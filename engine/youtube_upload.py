"""Post reviewed-and-ready episodes to YouTube, hands-off. Run by .github/workflows/youtube.yml (after every push + hourly).

usage: python3 engine/youtube_upload.py [--dry-run]

Each run, for every episode in episodes/*/episode.json:
  1. NEW (issue labelled `ready-to-review`, not `needs-fix`/`skipped`, never uploaded):
     auto-checks (9:16, length, title/description/hashtag limits, a sourced URL). Fails -> `needs-fix` + comment, nothing posted.
     Passes -> upload as PRIVATE scheduled to go public at the best slot >= grace_hours from now (`scheduled` label),
     or PUBLIC right away for eps listed in channel/youtube.json "publish_now_eps".
  2. SCHEDULED: if the owner labelled the issue `skipped`/`needs-fix` before it went live -> publish is cancelled (stays private).
     If YouTube has made it public -> `uploaded` label + comment with the link.
  3. LIVE for 48 h: records the view count, which is how the best posting slots are learned.
Then rebuilds TRACKER.md / TRACKER.csv and commits + pushes. Safe to re-run: the YouTube video id is stored in episode.json
("upload" block), so nothing is ever uploaded twice.

Needs env YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (GitHub secrets) and `gh` + `ffprobe`.
"""
import datetime as dt, glob, json, os, random, re, statistics, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get('IIN_REPO', 'ketu98/claude-indiainnumbers')
R = f'repos/{REPO}'
CFG = json.load(open(os.path.join(ROOT, 'channel', 'youtube.json'), encoding='utf-8'))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DRY = '--dry-run' in sys.argv
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube']
NOW = dt.datetime.now(dt.timezone.utc)
STOP = {'needs-fix', 'skipped'}


def log(*a): print(*a, flush=True)


# ---------------------------------------------------------------- GitHub helpers
def gh(*args, check=True):
    p = subprocess.run(['gh', 'api', *args], capture_output=True, text=True)
    if check and p.returncode != 0: raise RuntimeError(f"gh api {' '.join(args[:3])} failed: {p.stdout} {p.stderr}")
    return json.loads(p.stdout) if p.stdout.strip().startswith(('{', '[')) else p.stdout


def labels_of(issue): return {l['name'] for l in gh(f'{R}/issues/{issue}').get('labels', [])}


def relabel(issue, add=(), remove=()):
    if DRY: log(f'  [dry] issue #{issue}: +{list(add)} -{list(remove)}'); return
    for l in remove: gh('-X', 'DELETE', f'{R}/issues/{issue}/labels/{l}', check=False)
    if add:
        args = ['-X', 'POST', f'{R}/issues/{issue}/labels']
        for l in add: args += ['-f', f'labels[]={l}']
        gh(*args)


def comment(issue, body):
    if DRY: log(f'  [dry] comment #{issue}: {body[:120]}'); return
    gh('-X', 'POST', f'{R}/issues/{issue}/comments', '-f', f'body={body}')


def ensure_labels():
    have = {l['name'] for l in gh(f'{R}/labels?per_page=100')}
    for name, color, desc in [('long-form', 'fbca04', '16:9 long-form episode'), ('scheduled', '1d76db', 'Uploaded to YouTube, goes public at the scheduled time'),
                              ('upload-failed', 'b60205', 'The YouTube upload failed: see the comment')]:
        if name not in have and not DRY:
            gh('-X', 'POST', f'{R}/labels', '-f', f'name={name}', '-f', f'color={color}', '-f', f'description={desc}', check=False)


# ---------------------------------------------------------------- YouTube client
def youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], token_uri='https://oauth2.googleapis.com/token',
                        client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'], scopes=SCOPES)
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)


def video_status(yt, vid):
    items = yt.videos().list(part='status,statistics', id=vid).execute().get('items', [])
    return items[0] if items else None


# ---------------------------------------------------------------- metadata
def clean(s): return re.sub(r'[<>]', '', s or '').strip()


def norm_tag(h):
    h = re.sub(r'[^\w]', '', h.lstrip('#'), flags=re.UNICODE)
    return f'#{h}' if h else ''


def is_long(E): return E.get('kind') == 'long' or bool(E.get('chapters')) or (E.get('github') or {}).get('kind') == 'long'


def chapter_lines(E):
    """YouTube chapters: first at 0:00, at least 3, each at least 10 s long. Shorter ones are merged into the previous one."""
    ch = (E.get('github') or {}).get('chapters') or []
    out = []
    for t, name in ch:
        t = 0 if not out else int(t)
        if out and t - out[-1][0] < 10: continue
        out.append((t, name))
    return [f'{t // 60}:{t % 60:02d} {n}' for t, n in out] if len(out) >= 3 else []


def metadata(E):
    """Title / description / tags for YouTube. Uses the episode's "youtube" block when the research task wrote one,
    otherwise builds it from title / description / hashtags / sources."""
    y = E.get('youtube') or {}
    title = clean(y.get('title') or E.get('title') or E.get('topic', ''))[:100]
    tags_h = []
    for h in (y.get('hashtags') or E.get('hashtags') or []):
        h = norm_tag(h)
        if h and h.lower() not in [t.lower() for t in tags_h]: tags_h.append(h)
    topic = [h for h in tags_h if h.lower() not in ('#shorts', '#indiainnumbers')]
    topic += [b for b in CFG.get('broad_hashtags', []) if b.lower() not in [t.lower() for t in topic]]
    shown = topic[:3] + ([] if is_long(E) else ['#Shorts'])          # YouTube shows the first 3 hashtags above the title
    tags_h = [h for h in tags_h if not (is_long(E) and h.lower() == '#shorts')]
    rest = [h for h in tags_h if h not in shown] + ([] if '#IndiaInNumbers' in tags_h else ['#IndiaInNumbers'])
    hashtags = (shown + rest)[:8]
    body = clean(y.get('description') or E.get('description', ''))
    src = '\n'.join(f"• {clean(s['name'])}: {s['url']}" for s in E.get('sources', []) if s.get('url'))
    hook = clean(E.get('hook', {}).get('text', ''))
    chap = chapter_lines(E)
    parts = [(hook + '\n') if hook and hook not in body else '', body, '', *((['⏱ Chapters', *chap, '']) if chap else []),
             '📊 Sources', src, '', *([CFG['long_cta_line'], ''] if is_long(E) and CFG.get('long_cta_line') else ([CFG['short_cta_line'], ''] if CFG.get('short_cta_line') and not is_long(E) else [])), CFG['channel_line'], '', ' '.join(hashtags)]
    description = re.sub(r'\n{3,}', '\n\n', '\n'.join(parts)).strip()
    tags, total = [], 0
    for t in (y.get('tags') or []) + [h.lstrip('#') for h in hashtags] + CFG['default_tags']:
        t = clean(t).replace(',', ' ')
        if t and t.lower() not in [x.lower() for x in tags] and total + len(t) + 3 <= 450: tags.append(t); total += len(t) + 3
    return dict(title=title, description=description, tags=tags, hashtags=hashtags)


# ---------------------------------------------------------------- checks
def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                        '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(p.stdout or '{}'); s = (j.get('streams') or [{}])[0]
    return s.get('width'), s.get('height'), float(j.get('format', {}).get('duration') or 0)


def checks(E, path, M):
    bad = []
    if not path or not os.path.exists(path): return [f'video file not found: {path}']
    w, h, d = probe(path)
    if is_long(E):
        if not (w and h and w > h and abs(w / h - 16 / 9) < 0.02): bad.append(f'long-form is not 16:9 ({w}x{h})')
        lo, hi = CFG.get('long_duration_s', [120, 1200])
    else:
        if not (w and h and h > w and abs(w / h - 9 / 16) < 0.02): bad.append(f'not 9:16 vertical ({w}x{h})')
        lo, hi = CFG['duration_s']
    if not lo <= d <= hi: bad.append(f'length {d:.1f}s is outside {lo}-{hi}s')
    if not M['title']: bad.append('empty title')
    if len(M['description'].encode()) > 4900: bad.append('description too long')
    if not any(str(s.get('url', '')).startswith('http') for s in E.get('sources', [])): bad.append('no source with a URL')
    if len(M['hashtags']) > 15: bad.append('more than 15 hashtags')
    return bad


# ---------------------------------------------------------------- slot choice (learns the best posting times)
def slot_time(day, hhmm):
    h, m = map(int, hhmm.split(':'))
    return dt.datetime.combine(day, dt.time(h, m), IST)


def taken_times(eps):
    out = []
    for _, E in eps:
        u = E.get('upload') or {}
        if u.get('publish_at') and not u.get('cancelled'): out.append(dt.datetime.fromisoformat(u['publish_at']))
    return out


def slot_stats(eps):
    slots = CFG['fixed_slots'] or CFG['candidate_slots']
    views, used = {s: [] for s in slots}, {s: 0 for s in slots}
    for _, E in eps:
        u = E.get('upload') or {}
        if u.get('slot') in used and not u.get('cancelled'):
            used[u['slot']] += 1
            if u.get('views_48h') is not None: views[u['slot']].append(u['views_48h'])
    return slots, views, used


def pick_publish_time(eps):
    """Learning: spread episodes evenly over the candidate slots (soonest first) until each has explore_per_slot
    measured results. Then: post in the slot with the best median 48-hour views that is free within a day,
    still trying another slot explore_rate of the time so the ranking keeps up with the audience."""
    earliest = NOW.astimezone(IST) + dt.timedelta(hours=CFG['grace_hours'])
    taken, gap = taken_times(eps), dt.timedelta(hours=CFG['min_gap_hours'])
    slots, views, used = slot_stats(eps)
    def next_free(s):
        for k in range(10):
            t = slot_time(earliest.date() + dt.timedelta(days=k), s)
            if t >= earliest and all(abs(t - x) >= gap for x in taken): return t
    opts = [(s, next_free(s)) for s in slots]
    opts = [(s, t) for s, t in opts if t]
    if CFG['fixed_slots']:
        s, t = min(opts, key=lambda x: x[1]); return s, t, 'fixed'
    if min(len(v) for v in views.values()) < CFG['explore_per_slot']:
        s, t = min(opts, key=lambda x: (used[x[0]], x[1])); return s, t, 'learning'
    ranked = sorted(slots, key=lambda s: -statistics.median(views[s]))
    if random.random() < CFG['explore_rate']: ranked.insert(0, ranked.pop(random.randrange(1, len(ranked))))
    order = {s: i for i, s in enumerate(ranked)}
    soon = [(s, t) for s, t in opts if t - earliest <= dt.timedelta(hours=24)]
    s, t = min(soon or opts, key=lambda x: (order[x[0]], x[1]) if soon else x[1])
    return s, t, 'best'


# ---------------------------------------------------------------- actions
def upload(yt, E, path, M, publish_at=None):
    from googleapiclient.http import MediaFileUpload
    status = {'privacyStatus': 'private' if publish_at else 'public', 'selfDeclaredMadeForKids': CFG['made_for_kids'],
              'containsSyntheticMedia': CFG['contains_synthetic_media'], 'embeddable': True, 'license': 'youtube'}
    if publish_at: status['publishAt'] = publish_at.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    body = {'snippet': {'title': M['title'], 'description': M['description'], 'tags': M['tags'], 'categoryId': CFG['category_id'],
                        'defaultLanguage': CFG['language'], 'defaultAudioLanguage': CFG['language']}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, notifySubscribers=CFG['notify_subscribers'],
                             media_body=MediaFileUpload(path, mimetype='video/mp4', chunksize=-1, resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    return resp['id']


def keep_private(yt, vid):
    yt.videos().update(part='status', body={'id': vid, 'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': CFG['made_for_kids'],
                                                                    'containsSyntheticMedia': CFG['contains_synthetic_media']}}).execute()


_playlist = None
def add_to_playlist(yt, vid):
    global _playlist
    if not CFG.get('playlist_title'): return
    if _playlist is None:
        mine = yt.playlists().list(part='snippet', mine=True, maxResults=50).execute().get('items', [])
        hit = [p for p in mine if p['snippet']['title'] == CFG['playlist_title']]
        _playlist = hit[0]['id'] if hit else yt.playlists().insert(part='snippet,status', body={
            'snippet': {'title': CFG['playlist_title'], 'description': CFG['channel_line']},
            'status': {'privacyStatus': 'public'}}).execute()['id']
    yt.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': _playlist,
                              'resourceId': {'kind': 'youtube#video', 'videoId': vid}}}).execute()


def ist(t): return t.astimezone(IST).strftime('%d %b %Y, %I:%M %p IST')


MARK = re.compile(r'<!-- iin-upload (\{.*?\}) -->')


def restore_from_issue(E):
    """Never upload twice: if episode.json lost its upload block (e.g. a push race) but the issue already records an
    upload, restore the newest record from the issue instead of uploading again."""
    g, last = E['github'], None
    for c in gh(f"{R}/issues/{g['issue']}/comments?per_page=100") or []:
        for m in MARK.finditer(c.get('body') or ''):
            d = json.loads(m.group(1))
            if d.get('video_id') not in (E.get('upload') or {}).get('replaced', []): last = d
    if not last: return False
    u = E.setdefault('upload', {}); u.update(last, url=(f"https://www.youtube.com/watch?v={last['video_id']}" if is_long(E) else f"https://youtube.com/shorts/{last['video_id']}"), error=None)
    return True


def handle_new(yt, eps, epj, E, labels):
    n, issue, g = int(E['ep']), E['github']['issue'], E['github']
    u = E.setdefault('upload', {})
    path = os.path.join(ROOT, g.get('path', ''))
    M = metadata(E)
    bad = checks(E, path, M)
    if bad:
        log(f'Ep {n:02d}: checks failed: {bad}')
        relabel(issue, add=['needs-fix'], remove=['ready-to-review'])
        comment(issue, '🤖 **Not posted: automatic checks failed**\n' + '\n'.join(f'- {b}' for b in bad) +
                '\n\nFix it and re-run `publish_github.py` (that puts the `ready-to-review` label back), and it will be posted on the next run.')
        return True
    now_mode = n in CFG.get('publish_now_eps', [])
    slot, when, mode = (None, None, 'now') if now_mode else pick_publish_time(eps)
    log(f'Ep {n:02d}: uploading {os.path.basename(path)} -> ' + ('public now' if now_mode else f'{ist(when)} (slot {slot}, {mode})'))
    if DRY: log('  [dry] title:', M['title'], '\n  [dry] tags:', M['tags'], '\n' + M['description']); return False
    try:
        vid = upload(yt, E, path, M, when)
    except Exception as e:
        u['attempts'] = u.get('attempts', 0) + 1; u['error'] = str(e)[:300]
        relabel(issue, add=['upload-failed'])
        comment(issue, f"🤖 **YouTube upload failed** (attempt {u['attempts']}/{CFG['max_attempts']}): `{str(e)[:300]}`\n"
                       + ('I will retry on the next hourly run.' if u['attempts'] < CFG['max_attempts'] else 'Giving up: please check the setup.'))
        return True
    url = f'https://www.youtube.com/watch?v={vid}' if is_long(E) else f'https://youtube.com/shorts/{vid}'
    marker = '<!-- iin-upload ' + json.dumps({'video_id': vid, 'video_file': g.get('video_file'), 'slot': slot,
                                               'publish_at': (when or NOW.astimezone(IST)).isoformat(timespec='minutes')}) + ' -->'
    u.update(video_id=vid, url=url, video_file=g.get('video_file'), slot=slot, slot_mode=mode,
             uploaded=NOW.astimezone(IST).strftime('%Y-%m-%d %H:%M'), publish_at=(when or NOW.astimezone(IST)).isoformat(timespec='minutes'),
             title=M['title'], hashtags=M['hashtags'], error=None)
    try: add_to_playlist(yt, vid)
    except Exception as e: log('  playlist add failed (ignored):', e)
    th = os.path.join(ROOT, g.get('thumb') or '')
    if g.get('thumb') and os.path.exists(th):
        from googleapiclient.http import MediaFileUpload
        try: yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(th, mimetype='image/jpeg')).execute(); u['thumb'] = True
        except Exception as e: log('  thumbnail failed (ignored; custom thumbnails need a phone-verified channel):', str(e)[:200])
    st = (video_status(yt, vid) or {}).get('status', {})
    if (now_mode and st.get('privacyStatus') != 'public') or (when and not st.get('publishAt')):
        u['error'] = 'locked-private'
        relabel(issue, add=['upload-failed'], remove=['ready-to-review'])
        comment(issue, marker.replace('"slot"', '"error": "locked-private", "slot"') + f'\n🤖 Uploaded ({url}) but **YouTube kept it private**: the Google Cloud project probably needs the free '
                       'YouTube API audit (https://support.google.com/youtube/contact/yt_api_form). Until then, make it public in Studio by hand. '
                       'Uploads are paused for this episode.')
        return True
    if now_mode:
        u['published'] = NOW.astimezone(IST).strftime('%Y-%m-%d %H:%M')
        relabel(issue, add=['uploaded'], remove=['ready-to-review', 'upload-failed'])
        comment(issue, marker.replace('"slot"', '"published": "' + u['published'] + '", "slot"') + f'\n🤖 **Live on YouTube**: {url}\nYouTube link: {url}')
    else:
        relabel(issue, add=['scheduled'], remove=['ready-to-review', 'upload-failed'])
        comment(issue, marker + f'\n🤖 **Uploaded and scheduled**: goes public **{ist(when)}**.\n{url} (private until then)\n\n'
                       f'To stop it, label this issue `skipped` or `needs-fix` before then.\n\nTitle: {M["title"]}\nHashtags: {" ".join(M["hashtags"])}')
    return True


def handle_scheduled(yt, E, labels):
    n, issue, u = int(E['ep']), E['github']['issue'], E['upload']
    v = video_status(yt, u['video_id'])
    if not v:
        u['error'] = 'missing'; relabel(issue, remove=['scheduled'])
        comment(issue, f"🤖 The YouTube video {u['url']} no longer exists. I won't upload this episode again unless you clear its `upload` block.")
        return True
    if v['status'].get('privacyStatus') == 'public':
        u['published'] = u.get('publish_at', '').replace('T', ' ')[:16]; u['error'] = None
        relabel(issue, add=['uploaded'], remove=['scheduled', 'ready-to-review', 'upload-failed'])
        mk = {k: u.get(k) for k in ('video_id', 'video_file', 'slot', 'publish_at', 'published')}
        comment(issue, f"<!-- iin-upload {json.dumps(mk)} -->\n🤖 **Live on YouTube**: {u['url']}\nYouTube link: {u['url']}")
        log(f'Ep {n:02d}: now live'); return True
    if labels & STOP:
        log(f'Ep {n:02d}: cancelled by label {labels & STOP}')
        if not DRY: keep_private(yt, u['video_id'])
        u['cancelled'] = True; relabel(issue, remove=['scheduled'])
        mk = {k: u.get(k) for k in ('video_id', 'video_file', 'slot', 'publish_at', 'cancelled')}
        comment(issue, f"<!-- iin-upload {json.dumps(mk)} -->\n🤖 **Publish cancelled**: {u['url']} stays private. Fix it and re-run `publish_github.py` to try again.")
        return True
    return False


def handle_views(yt, E):
    u = E['upload']
    pub = dt.datetime.fromisoformat(u['publish_at'])
    if NOW - pub >= dt.timedelta(hours=48):
        v = video_status(yt, u['video_id'])
        u['views_48h'] = int(v['statistics'].get('viewCount', 0)) if v else 0
        log(f"Ep {E['ep']:02d}: {u['views_48h']} views after 48 h (slot {u.get('slot')})"); return True
    return False


def git(*a, check=True):
    p = subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True)
    if check and p.returncode != 0: raise SystemExit(f"git {' '.join(a)} failed: {p.stdout}{p.stderr}")
    return p


def main():
    if not CFG.get('enabled'): log('uploader disabled in channel/youtube.json'); return
    missing = [k for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN') if not os.environ.get(k)]
    if missing and not DRY: log(f'YouTube secrets not set yet ({", ".join(missing)}): nothing to do. See channel/YOUTUBE_SETUP.md'); return
    yt = None if missing else youtube()
    ensure_labels()
    eps = []
    for epj in sorted(glob.glob(os.path.join(ROOT, 'episodes', '*', 'episode.json'))):
        eps.append((epj, json.load(open(epj, encoding='utf-8'))))
    eps.sort(key=lambda x: int(x[1]['ep']))
    changed = False
    for epj, E in eps:
        g, u = E.get('github') or {}, E.get('upload') or {}
        if not g.get('issue'): continue
        try:
            labels = labels_of(g['issue'])
            did = False
            if not u.get('video_id') and restore_from_issue(E):
                log(f"Ep {E['ep']:02d}: restored its upload record from the issue"); u = E['upload']; did = True
            if u.get('video_file') and g.get('video_file') != u['video_file'] and not u.get('published'):
                # re-rendered (e.g. narrator voice) before going live: retire the old upload, post the new render
                log(f"Ep {E['ep']:02d}: new render found, replacing the earlier upload")
                if yt and u.get('video_id') and not u.get('cancelled') and not DRY: keep_private(yt, u['video_id'])
                if u.get('video_id'):
                    comment(g['issue'], f"🤖 A new render was published, so the earlier upload ({u['url']}) stays private "
                                        "(delete it in Studio if you like). The new one will be posted.")
                E['upload'] = u = {'replaced': (u.get('replaced') or []) + ([u['video_id']] if u.get('video_id') else [])}
                relabel(g['issue'], remove=['scheduled']); did = True
                labels = labels_of(g['issue']) if not DRY else labels
            if not u.get('video_id'):
                retry_ok = u.get('attempts', 0) < CFG['max_attempts']
                if 'ready-to-review' in labels and not labels & STOP and 'uploaded' not in labels and retry_ok:
                    did = handle_new(yt, eps, epj, E, labels) or did
            elif yt and not u.get('published') and not u.get('cancelled') and u.get('error') is None:
                did = handle_scheduled(yt, E, labels) or did
            elif yt and u.get('published') and u.get('views_48h') is None:
                did = handle_views(yt, E) or did
            if did and not DRY:
                json.dump(E, open(epj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); changed = True
        except Exception as e:
            log(f"Ep {E.get('ep')}: error {e}")
    if DRY or not changed: log('done (no changes)' if not DRY else 'dry run done'); return
    subprocess.run([sys.executable, os.path.join(ROOT, 'engine', 'build_tracker.py')], check=True)
    git('add', 'episodes', 'TRACKER.md', 'TRACKER.csv')
    if git('diff', '--cached', '--quiet', check=False).returncode != 0:
        git('commit', '-m', f"YouTube: uploads/status update ({NOW.astimezone(IST):%Y-%m-%d %H:%M} IST)")
        for _ in range(3):
            if git('push', 'origin', 'HEAD:main', check=False).returncode == 0: break
            git('rebase', '--abort', check=False); git('pull', '--rebase', '-X', 'theirs', 'origin', 'main', check=False)
        else: raise SystemExit('push failed')
    log('done')


if __name__ == '__main__':
    main()

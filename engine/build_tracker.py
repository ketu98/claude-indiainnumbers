"""Regenerate TRACKER.md and TRACKER.csv at the repo root from episodes/*/episode.json
and the live labels of each episode's GitHub issue (status = ready-to-review / uploaded / needs-fix / skipped).
The YouTube link is taken from the issue body line "YouTube link: <url>" or the issue comments, if the owner pasted one."""
import csv, glob, json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get('IIN_REPO', 'ketu98/claude-indiainnumbers')
STATUS = {'uploaded': '✅ Uploaded', 'needs-fix': '🛠 Needs fix', 'skipped': '⏭ Skipped', 'upload-failed': '❌ Upload failed',
          'scheduled': '🗓 Scheduled', 'ready-to-review': '🟡 Queued for YouTube'}
ORDER = ('uploaded', 'skipped', 'needs-fix', 'upload-failed', 'scheduled', 'ready-to-review')
YT = re.compile(r'https?://(?:www\.)?(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)[\w\-?=&]+')

def gh(path):
    p = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None

rows = []
for epj in glob.glob(os.path.join(ROOT, 'episodes', '*', 'episode.json')):
    E = json.load(open(epj)); g = E.get('github', {}); status, yt = '⚪ Not published', ''
    if g.get('issue'):
        iss = gh(f"repos/{REPO}/issues/{g['issue']}")
        if iss:
            names = [l['name'] for l in iss.get('labels', [])]
            status = next((STATUS[k] for k in ORDER if k in names), STATUS['ready-to-review'])
            texts = [iss.get('body') or ''] + [c.get('body') or '' for c in (gh(f"repos/{REPO}/issues/{g['issue']}/comments") or [])]
            m = [YT.search(t) for t in texts]; m = [x.group(0) for x in m if x]
            yt = m[-1] if m else ''
    u = E.get('upload') or {}
    yt = u.get('url') if u.get('published') else (yt or '')
    golive = (u.get('published') or (u.get('publish_at', '').replace('T', ' ')[:16] if u.get('video_id') and not u.get('cancelled') else ''))
    rows.append(dict(ep=int(E['ep']), made=g.get('made', ''), slot=g.get('slot', ''), topic=E.get('topic', ''), status=status,
                     title=E.get('title', ''), voice=g.get('voice', ''), video_file=g.get('video_file', ''),
                     video=g.get('video', ''), release=g.get('release', ''),
                     issue=f"https://github.com/{REPO}/issues/{g['issue']}" if g.get('issue') else '',
                     sources='; '.join(s['name'] for s in E.get('sources', [])), youtube=yt, live_ist=golive,
                     post_slot=u.get('slot') or ('now' if u.get('published') and not u.get('slot') else ''), views_48h=u.get('views_48h', ''),
                     folder=os.path.basename(os.path.dirname(epj)), kind=g.get('kind', 'short'), format=E.get('format', 'classic')))
rows.sort(key=lambda r: r['ep'], reverse=True)

with open(os.path.join(ROOT, 'TRACKER.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['ep']); w.writeheader(); w.writerows(rows)

def esc(s): return str(s).replace('|', '\\|')
lines = ['# 📊 Episode Tracker', '',
         'Auto-generated on every run (newest first). Status comes from each episode\'s Issue label, set by the YouTube uploader: '
         '`ready-to-review` (queued) → `scheduled` → `uploaded`. Label an issue `skipped` before it goes live to stop it. 🎞 = long-form.', '',
         '| Ep | Made (IST) | Status | Live (IST) | Title | Voice | Video | Issue | YouTube | Views 48h |',
         '|---:|---|---|---|---|---|---|---|---|---:|']
for r in rows:
    vid = f"[▶ mp4]({r['video']})" if r['video'] else ''
    rev = f"[issue]({r['issue']})" if r['issue'] else ''
    yt = f"[watch]({r['youtube']})" if r['youtube'] else ''
    lines.append(f"| {r['ep']:02d} | {r['made']} | {r['status']} | {r['live_ist']} | {'🎞 ' if r.get('kind') == 'long' else ''}{esc(r['title'])} | {r['voice']} | {vid} | {rev} | {yt} | {r['views_48h']} |")
open(os.path.join(ROOT, 'TRACKER.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('tracker:', len(rows), 'episodes')

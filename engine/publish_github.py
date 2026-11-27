"""Publish an episode to GitHub for review, then refresh the tracker and push.

usage: python3 engine/publish_github.py episodes/<folder> [--slot Morning|Afternoon|Manual]

- Copies the newest video + upload text from <folder>/out/ into  videos/YYYY-MM/  (date-time file names).
- Opens (or updates) one Issue per episode: "Ep NN · <date time> · <title>", labels `episode` + `ready-to-review`
  (+ `narrator-voice`), linking the video, with a review checklist.
- Writes the GitHub info into episode.json, regenerates TRACKER.md / TRACKER.csv, commits everything and pushes to main.
Uses `gh api` (REST only) and git. Safe to re-run for the same episode (one issue per episode, files replaced).
"""
import json, os, sys, glob, shutil, subprocess, datetime, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get('IIN_REPO', 'ketu98/claude-indiainnumbers')
R = f'repos/{REPO}'

def gh(*args, check=True):
    p = subprocess.run(['gh', 'api', *args], capture_output=True, text=True)
    if check and p.returncode != 0: raise SystemExit(f"gh api failed: {' '.join(args[:3])}\n{p.stdout}\n{p.stderr}")
    return json.loads(p.stdout) if p.stdout.strip().startswith(('{', '[')) else p.stdout

def git(*args, check=True):
    p = subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True)
    if check and p.returncode != 0: raise SystemExit(f"git {' '.join(args)} failed:\n{p.stdout}\n{p.stderr}")
    return p

def main():
    ep_dir = os.path.abspath(sys.argv[1].rstrip('/'))
    slot = sys.argv[sys.argv.index('--slot') + 1] if '--slot' in sys.argv else 'Manual'
    epj = os.path.join(ep_dir, 'episode.json'); EP = json.load(open(epj)); n = int(EP['ep'])
    vids = sorted(glob.glob(os.path.join(ep_dir, 'out', '*.mp4')), key=os.path.getmtime)
    txts = sorted(glob.glob(os.path.join(ep_dir, 'out', '*_upload.txt')), key=os.path.getmtime)
    if not vids: raise SystemExit('no mp4 in out/ — render first')
    vid, txt = vids[-1], (txts[-1] if txts else None)
    extra = [x for x in (sorted(glob.glob(os.path.join(ep_dir, 'out', '*_chapters.json')), key=os.path.getmtime)[-1:] +
                         sorted(glob.glob(os.path.join(ep_dir, 'out', '*_thumb.jpg')), key=os.path.getmtime)[-1:])]
    vname = os.path.basename(vid); stamp = vname[:16]
    when = datetime.datetime.strptime(stamp, '%Y-%m-%d_%H-%M'); nice = when.strftime('%d %b %Y, %I:%M %p IST')
    voice = 'SIGMA' if vname.endswith(('_sigma.mp4', '_narrator.mp4')) else 'VEDA'
    kind = 'long' if EP.get('kind') == 'long' or EP.get('chapters') else 'short'

    # ---- files into videos/YYYY-MM/
    month_dir = os.path.join(ROOT, 'videos', when.strftime('%Y-%m')); os.makedirs(month_dir, exist_ok=True)
    rel_paths = []
    for p in (vid, txt, *extra):
        if p:
            shutil.copy2(p, os.path.join(month_dir, os.path.basename(p)))
            rel_paths.append(os.path.relpath(os.path.join(month_dir, os.path.basename(p)), ROOT))
    vrel = rel_paths[0]
    vurl = f"https://github.com/{REPO}/blob/main/{urllib.parse.quote(vrel)}"
    vraw = f"https://github.com/{REPO}/raw/main/{urllib.parse.quote(vrel)}"
    turl = f"https://github.com/{REPO}/blob/main/{urllib.parse.quote(rel_paths[1])}" if txt else ''
    chap_rel = next((r for r in rel_paths if r.endswith('_chapters.json')), None)
    thumb_rel = next((r for r in rel_paths if r.endswith('_thumb.jpg')), None)

    # ---- issue (one per episode)
    title = f"Ep {n:02d} · {nice} · {EP.get('title', EP.get('topic', ''))}"
    grace = json.load(open(os.path.join(ROOT, 'channel', 'youtube.json'))).get('grace_hours', 3)
    src = '\n'.join(f"- [{s['name']}]({s['url']})" for s in EP.get('sources', []))
    ibody = f"""### 🎬 {vname}
[▶ Open video]({vurl}) · [⬇ Download]({vraw}){f' · [📝 Upload text]({turl})' if turl else ''}

**{EP.get('topic', '')}** · {'🎞 LONG-FORM (16:9)' if kind == 'long' else '📱 Short'} · format: {EP.get('format', 'classic')} · made {nice} · {slot} slot · hook voice: {voice}

**YouTube title:** {EP.get('title', '')}

**Description:**
{EP.get('description', '')}

{' '.join(EP.get('hashtags', []))}

**Sources**
{src}

Hook line to record: "{EP['hook']['text']}"

### Posting
🤖 The YouTube uploader posts this automatically: it checks the video, uploads it as private and schedules it for the
best posting slot (at least {grace} h from now). Its comments below say when it goes live.
**To stop it**, label this issue `skipped` or `needs-fix` any time before then.

---
Labels: `ready-to-review` → `scheduled` → `uploaded` (or `needs-fix` / `skipped` / `upload-failed`). TRACKER.md updates on every run.
"""
    issue_no = EP.get('github', {}).get('issue')
    if issue_no:
        gh('-X', 'PATCH', f'{R}/issues/{issue_no}', '-f', f'title={title}', '-f', f'body={ibody}')
        if voice == 'SIGMA': gh('-X', 'POST', f'{R}/issues/{issue_no}/labels', '-f', 'labels[]=narrator-voice')
        # a re-publish (fix or new voice) puts the episode back in the YouTube queue, unless it is already live
        if not EP.get('upload', {}).get('published'):
            for l in ('needs-fix', 'skipped', 'upload-failed'): gh('-X', 'DELETE', f'{R}/issues/{issue_no}/labels/{l}', check=False)
            gh('-X', 'POST', f'{R}/issues/{issue_no}/labels', '-f', 'labels[]=ready-to-review')
            up = EP.get('upload', {})
            if not up.get('video_id'): EP.pop('upload', None)
            elif up.get('cancelled') or up.get('error'):   # cancelled / failed upload: start fresh, never revive the old one
                EP['upload'] = {'replaced': (up.get('replaced') or []) + [up['video_id']]}
    else:
        args = ['-X', 'POST', f'{R}/issues', '-f', f'title={title}', '-f', f'body={ibody}']
        for l in ['episode', 'ready-to-review'] + (['narrator-voice'] if voice == 'SIGMA' else []) + (['long-form'] if kind == 'long' else []):
            args += ['-f', f'labels[]={l}']
        issue_no = gh(*args)['number']
    EP['github'] = {'issue': issue_no, 'video': vurl, 'video_file': vname, 'path': vrel,
                    'made': when.strftime('%Y-%m-%d %H:%M'), 'slot': slot, 'voice': voice, 'kind': kind}
    if chap_rel: EP['github']['chapters'] = json.load(open(os.path.join(ROOT, chap_rel)))
    if thumb_rel: EP['github']['thumb'] = thumb_rel
    json.dump(EP, open(epj, 'w'), ensure_ascii=False, indent=1)

    subprocess.run([sys.executable, os.path.join(ROOT, 'engine', 'build_tracker.py')], check=True)

    # ---- commit + push (retry once on a moved remote)
    git('add', '--sparse', '-f', *rel_paths, os.path.relpath(epj, ROOT), 'TRACKER.md', 'TRACKER.csv')
    if os.path.exists(os.path.join(ep_dir, 'upload.txt')): git('add', os.path.relpath(os.path.join(ep_dir, 'upload.txt'), ROOT))
    if git('diff', '--cached', '--quiet', check=False).returncode != 0:
        git('commit', '-m', f"Ep {n:02d}: {EP.get('topic', '')} ({stamp})")
    for attempt in range(2):
        if git('-c', 'push.negotiate=true', 'push', 'origin', 'HEAD:main', check=False).returncode == 0: break
        git('rebase', '--abort', check=False)   # TRACKER.md may clash with the uploader's commit: keep ours, it is rebuilt every run
        git('pull', '--rebase', '-X', 'theirs', '--depth=50', 'origin', 'main', check=False)
    else:
        raise SystemExit('push failed twice')
    print('ISSUE', f"https://github.com/{REPO}/issues/{issue_no}"); print('VIDEO', vurl)

if __name__ == '__main__':
    main()

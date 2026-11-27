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
    vname = os.path.basename(vid); stamp = vname[:16]
    when = datetime.datetime.strptime(stamp, '%Y-%m-%d_%H-%M'); nice = when.strftime('%d %b %Y, %I:%M %p IST')
    voice = 'Narrator' if vname.endswith('_narrator.mp4') else 'VEDA'

    # ---- files into videos/YYYY-MM/
    month_dir = os.path.join(ROOT, 'videos', when.strftime('%Y-%m')); os.makedirs(month_dir, exist_ok=True)
    rel_paths = []
    for p in (vid, txt):
        if p:
            shutil.copy2(p, os.path.join(month_dir, os.path.basename(p)))
            rel_paths.append(os.path.relpath(os.path.join(month_dir, os.path.basename(p)), ROOT))
    vrel = rel_paths[0]
    vurl = f"https://github.com/{REPO}/blob/main/{urllib.parse.quote(vrel)}"
    vraw = f"https://github.com/{REPO}/raw/main/{urllib.parse.quote(vrel)}"
    turl = f"https://github.com/{REPO}/blob/main/{urllib.parse.quote(rel_paths[1])}" if len(rel_paths) > 1 else ''

    # ---- issue (one per episode)
    title = f"Ep {n:02d} · {nice} · {EP.get('title', EP.get('topic', ''))}"
    src = '\n'.join(f"- [{s['name']}]({s['url']})" for s in EP.get('sources', []))
    ibody = f"""### 🎬 {vname}
[▶ Open video]({vurl}) · [⬇ Download]({vraw}){f' · [📝 Upload text]({turl})' if turl else ''}

**{EP.get('topic', '')}** · made {nice} · {slot} slot · hook voice: {voice}

**YouTube title:** {EP.get('title', '')}

**Description:**
{EP.get('description', '')}

{' '.join(EP.get('hashtags', []))}

**Sources**
{src}

Hook line to record: "{EP['hook']['text']}"

### Review checklist
- [ ] Watched it: numbers, captions and audio look right
- [ ] Uploaded to YouTube (paste the link below, then switch the label to `uploaded`)

YouTube link:

---
Labels: `ready-to-review` → `uploaded` (or `needs-fix` / `skipped`). TRACKER.md updates on the next run.
"""
    issue_no = EP.get('github', {}).get('issue')
    if issue_no:
        gh('-X', 'PATCH', f'{R}/issues/{issue_no}', '-f', f'title={title}', '-f', f'body={ibody}')
        if voice == 'Narrator': gh('-X', 'POST', f'{R}/issues/{issue_no}/labels', '-f', 'labels[]=narrator-voice')
    else:
        args = ['-X', 'POST', f'{R}/issues', '-f', f'title={title}', '-f', f'body={ibody}']
        for l in ['episode', 'ready-to-review'] + (['narrator-voice'] if voice == 'Narrator' else []): args += ['-f', f'labels[]={l}']
        issue_no = gh(*args)['number']
    EP['github'] = {'issue': issue_no, 'video': vurl, 'video_file': vname, 'path': vrel,
                    'made': when.strftime('%Y-%m-%d %H:%M'), 'slot': slot, 'voice': voice}
    json.dump(EP, open(epj, 'w'), ensure_ascii=False, indent=1)

    subprocess.run([sys.executable, os.path.join(ROOT, 'engine', 'build_tracker.py')], check=True)

    # ---- commit + push (retry once on a moved remote)
    git('add', '--sparse', '-f', *rel_paths, os.path.relpath(epj, ROOT), 'TRACKER.md', 'TRACKER.csv')
    if os.path.exists(os.path.join(ep_dir, 'upload.txt')): git('add', os.path.relpath(os.path.join(ep_dir, 'upload.txt'), ROOT))
    if git('diff', '--cached', '--quiet', check=False).returncode != 0:
        git('commit', '-m', f"Ep {n:02d}: {EP.get('topic', '')} ({stamp})")
    for attempt in range(2):
        if git('-c', 'push.negotiate=true', 'push', 'origin', 'HEAD:main', check=False).returncode == 0: break
        git('pull', '--rebase', '--depth=50', 'origin', 'main', check=False)
    else:
        raise SystemExit('push failed twice')
    print('ISSUE', f"https://github.com/{REPO}/issues/{issue_no}"); print('VIDEO', vurl)

if __name__ == '__main__':
    main()

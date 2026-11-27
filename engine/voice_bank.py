"""SIGMA's voice bank: turn one long phone recording per script section into ready-to-use clips.

The bank lives in a PRIVATE repo (default ~/iin-voice-bank, or $IIN_VOICE_BANK):
    bank.json            id -> {text, kind, tone, file}
    clips/<id>.m4a       cleaned clips (NOT disguised; the disguise is applied at render time, see channel/sigma.json)
    inbox/*              drop raw recordings here, named after their script: Script_01.m4a, Script_02.m4a ... (or inbox/Script_01/<any name>)
    raw/<Script_NN>/*    processed raw recordings are moved here

The scripts to read are in this public repo's sigma-scripts/ folder (Script_01_<name>.md ...). When a recording is processed,
its script is renamed Completed_Script_01_<name>.md, so the owner can see what's done.

usage:
  python3 engine/voice_bank.py inbox [--bank DIR]          # process everything waiting in inbox/
  python3 engine/voice_bank.py split <recording> --section Script_01 [--bank DIR]
  python3 engine/voice_bank.py status [--bank DIR]         # what's recorded, what's missing
  python3 engine/voice_bank.py scripts                     # (re)write sigma-scripts/ from channel/sigma_script.json
"""
import glob, json, os, re, shutil, subprocess, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SCRIPT = json.load(open(os.path.join(ROOT, 'channel', 'sigma_script.json'), encoding='utf-8'))['sections']
SR = 48000
AUDIO = ('mp3', 'm4a', 'wav', 'ogg', 'aac', 'opus', 'webm', 'mp4', 'flac', '3gp', 'amr')
CHAIN = ','.join([
    'arnndn=m=' + os.path.join(HERE, 'models', 'sh.rnnn') + ':mix=0.8', 'highpass=f=80',
    'equalizer=f=170:t=q:w=1:g=2', 'equalizer=f=400:t=q:w=1.2:g=-2', 'equalizer=f=3500:t=q:w=1:g=3',
    'equalizer=f=10000:t=q:w=1:g=2.5', 'deesser=i=0.4', 'acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=2',
    'loudnorm=I=-15:TP=-1.5:LRA=6', 'aresample=48000'])


SCRIPTS_DIR = os.path.join(ROOT, 'sigma-scripts')


def section_of(name):
    """'Script_01', 'script 1', '01', 'Script_01_whatever.m4a' -> 'Script_01' (or None)."""
    m = re.match(r'\s*(?:script)?[\s_-]*0*(\d{1,3})(?!\d)', os.path.basename(name), re.I)
    key = f'Script_{int(m.group(1)):02d}' if m else None
    return key if key in SCRIPT else None


def script_filename(key):
    return f"{key}_{re.sub(r'[^A-Za-z0-9]+', '-', SCRIPT[key]['title']).strip('-')}.md"


def write_scripts():
    """One readable file per recording in sigma-scripts/, numbered lines in order. Keeps the Completed_ prefix if already done."""
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    for key, sec in SCRIPT.items():
        name = script_filename(key); done = os.path.join(SCRIPTS_DIR, 'Completed_' + name)
        path = done if os.path.exists(done) else os.path.join(SCRIPTS_DIR, name)
        n = len(sec['lines'])
        out = [f"# {key.replace('_', ' ')} · {sec['title']}", '',
               f"Save your recording as **{key}** (e.g. `{key}.m4a`). {n} lines, about {max(1, round(n * 4.5 / 60))}–{max(2, round(n * 6 / 60))} minutes.",
               'Read in order. Pause about 2 seconds after each line. Do not read the numbers.', '']
        for i, (cid, text, tone) in enumerate(sec['lines'], 1):
            out += [f'{i:02d}. {text}', '']
        out += ['---', f"<sub>clip ids in order: {' '.join(l[0] for l in sec['lines'])}</sub>", '']
        open(path, 'w', encoding='utf-8').write('\n'.join(out))
    print('scripts written to', SCRIPTS_DIR)


def mark_completed(key):
    src = os.path.join(SCRIPTS_DIR, script_filename(key))
    if os.path.exists(src):
        os.replace(src, os.path.join(SCRIPTS_DIR, 'Completed_' + script_filename(key)))
        print(f'  marked {script_filename(key)} as Completed_')


def bank_dir():
    if '--bank' in sys.argv: return os.path.abspath(sys.argv[sys.argv.index('--bank') + 1])
    return os.path.expanduser(os.environ.get('IIN_VOICE_BANK', '~/iin-voice-bank'))


def read(path):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-af', 'highpass=f=70',
                                         '-f', 'f32le', '-'], capture_output=True, check=True).stdout, np.float32).copy()


def segments(x, n):
    """Find exactly n spoken lines separated by pauses. Returns [(start, end)] in samples, or raises with what it found."""
    hop = SR // 50; e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    found = {}
    for k in (4, 3, 5, 2.5, 6, 8):
        thr = max(np.percentile(e, 15) * k, e.max() * 0.04)
        on = np.where(e > thr)[0]
        if not len(on): continue
        for gap in np.arange(0.5, 2.05, 0.1):
            g = int(gap * 50); groups, cur = [], [on[0]]
            for i in on[1:]:
                if i - cur[-1] <= g: cur.append(i)
                else: groups.append(cur); cur = [i]
            groups.append(cur)
            groups = [c for c in groups if (c[-1] - c[0]) >= 12 and e[c].mean() > thr * 1.2]   # drop clicks / breaths (< 0.25 s)
            found.setdefault(len(groups), []).append((round(gap, 1), k, groups))
        if n in found: break
    if n not in found:
        near = sorted(found, key=lambda m: abs(m - n))[:3]
        raise SystemExit(f'expected {n} lines but found {near} (pauses between lines may be too short, or a line was skipped/repeated). '
                         'Re-record with a clear ~2 s pause between lines, or send the lines you missed as a new recording.')
    gap, k, groups = found[n][len(found[n]) // 2]
    return [(max(0, c[0] * hop - int(0.22 * SR)), min(len(x), (c[-1] + 1) * hop + int(0.3 * SR))) for c in groups]


def clean_all(x, segs, tmp):
    import noisereduce as nr
    mask = np.ones(len(x), bool)
    for a, b in segs: mask[a:b] = False
    quiet = x[mask]
    den = nr.reduce_noise(y=x, sr=SR, y_noise=quiet if len(quiet) > SR * 0.5 else None, stationary=len(quiet) > SR * 0.5,
                          prop_decrease=0.9, n_fft=2048) if len(quiet) > SR * 0.2 else x
    sf.write(tmp + '.den.wav', den, SR)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '.den.wav', '-af', CHAIN, '-ac', '1', tmp + '.clean.wav'], check=True)
    y = sf.read(tmp + '.clean.wav')[0]
    for f in (tmp + '.den.wav', tmp + '.clean.wav'): os.remove(f)
    return y


def split(rec, section, bank, start=None):
    section = section_of(section) or section
    sec = SCRIPT[section]; lines = sec['lines']
    if start: lines = lines[[l[0] for l in lines].index(start):]
    x = read(rec); segs = segments(x, len(lines))
    os.makedirs(os.path.join(bank, 'clips'), exist_ok=True)
    y = clean_all(x, segs, os.path.join(bank, '.tmp'))
    bj = os.path.join(bank, 'bank.json'); B = json.load(open(bj, encoding='utf-8')) if os.path.exists(bj) else {}
    for (cid, text, tone), (a, b) in zip(lines, segs):
        c = y[a:b].copy(); f = int(0.03 * SR); c[:f] *= np.linspace(0, 1, f); c[-f:] *= np.linspace(1, 0, f)
        wav = os.path.join(bank, 'clips', cid + '.wav'); sf.write(wav, c, SR)
        out = os.path.join(bank, 'clips', cid + '.m4a')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-c:a', 'aac', '-b:a', '96k', out], check=True); os.remove(wav)
        B[cid] = dict(text=text, kind=sec['kind'], tone=tone, file=f'clips/{cid}.m4a', secs=round((b - a) / SR, 2))
        print(f'  {cid}  {(b - a) / SR:4.1f}s  {text}')
    json.dump(dict(sorted(B.items())), open(bj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{section}: {len(lines)} clips saved to {bank}/clips')
    if not start: mark_completed(section)


def inbox(bank):
    done, problems = 0, []
    for rec in sorted(glob.glob(os.path.join(bank, 'inbox', '**', '*'), recursive=True)):
        if not os.path.isfile(rec) or rec.rsplit('.', 1)[-1].lower() not in AUDIO: continue
        parent = os.path.basename(os.path.dirname(rec))
        key = section_of(parent) if parent != 'inbox' else None
        key = key or section_of(rec)
        if not key:
            problems.append(f'{os.path.basename(rec)}: name it after its script (Script_01 ... Script_{len(SCRIPT):02d})'); continue
        print(f'{rec} -> {key}:')
        try: split(rec, key, bank)
        except SystemExit as e: problems.append(f'{os.path.basename(rec)} ({key}): {e}'); continue
        dst = os.path.join(bank, 'raw', key); os.makedirs(dst, exist_ok=True); shutil.move(rec, os.path.join(dst, os.path.basename(rec)))
        done += 1
    print(f'inbox: {done} recording(s) processed')
    for p in problems: print('PROBLEM:', p)
    if problems: sys.exit(2)


def status(bank):
    bj = os.path.join(bank, 'bank.json'); B = json.load(open(bj, encoding='utf-8')) if os.path.exists(bj) else {}
    for s, sec in SCRIPT.items():
        miss = [l[0] for l in sec['lines'] if l[0] not in B]
        print(f"{s} · {sec['title']}: {len(sec['lines']) - len(miss)}/{len(sec['lines'])} recorded" + (f"  missing: {' '.join(miss)}" if miss else ''))


if __name__ == '__main__':
    cmd, bank = (sys.argv[1] if len(sys.argv) > 1 else ''), bank_dir()
    if cmd == 'split': split(sys.argv[2], sys.argv[sys.argv.index('--section') + 1], bank,
                             sys.argv[sys.argv.index('--start') + 1] if '--start' in sys.argv else None)
    elif cmd == 'inbox': inbox(bank)
    elif cmd == 'status': status(bank)
    elif cmd == 'scripts': write_scripts()
    else: raise SystemExit(__doc__)

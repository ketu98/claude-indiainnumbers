"""India in Numbers — turn an episode.json into a finished video.

usage: python3 engine/make_episode.py episodes/<ep-folder> [--preview 2,9,15]
- Short (default): 9:16, 1080x1920.  Long-form ("kind": "long", with "chapters"): 16:9, 1920x1080, plus a thumbnail.
- SIGMA, the anonymous narrator, speaks clips from the private voice bank ($IIN_VOICE_BANK, default ~/iin-voice-bank):
  "hook": {"clip": "q01", "intro": "i01"} and "last_word": {"react": "r02", "close": "s03"}. Missing clips fall back to VEDA / are skipped.
  A hook.(mp3|m4a|wav|ogg|aac) file in the folder is also used as SIGMA's hook. The voice disguise is set in channel/sigma.json.
Writes <folder>/out/<YYYY-MM-DD_HH-MM>_<epNN_slug>_<veda|sigma>.mp4, ..._upload.txt (IST time), and for long-form ..._chapters.json + ..._thumb.jpg
"""
import json, math, os, subprocess, sys, glob, hashlib
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 24000
FD = os.environ.get('IIN_FONTS', '/usr/share/fonts/opentype/inter/')
MODEL_DIR = os.environ.get('IIN_MODELS', os.path.expanduser('~/.cache/iin'))
BANK = os.path.expanduser(os.environ.get('IIN_VOICE_BANK', '~/iin-voice-bank'))
SIG = json.load(open(os.path.join(os.path.dirname(HERE), 'channel', 'sigma.json'), encoding='utf-8'))
SNAME, SGLYPH, SCOL = SIG.get('name', 'SIGMA'), SIG.get('glyph', 'Σ'), tuple(SIG.get('color', (190, 160, 255)))
# layout (portrait canvas). Long-form renders a taller portrait canvas and rearranges it into 16:9 (compose_land)
LONG = False; OUT_W, OUT_H = W, H; BUB_Y, ROB_Y, NAME_Y = 1270, 1615, 1640
FORMATS = {  # episode "format" -> header label, accent colour
    'classic': ('THE PANEL', (255, 138, 61)), 'myth': ('MYTH OR FACT?', (255, 96, 96)), 'versus': ('INDIA VS THE WORLD', (80, 200, 255)),
    'then-now': ('THEN VS NOW', (255, 214, 120)), 'ranking': ('THE RANKING', (140, 240, 140)), 'viewer': ('YOU ASKED', (255, 105, 200)),
    'tracker': ('THE TRACKER', (190, 160, 255)), 'guess': ('GUESS THE NUMBER', (110, 240, 215)), 'long': ('THE LONG VERSION', (255, 186, 70))}
NUMW = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']

# ---------------------------------------------------------------- cast
CAST = {
    'VEDA':     dict(voice='af_bella',  speed=0.97, lang='en-us', col=(80, 220, 255),  x=540),
    'REGINALD': dict(voice='bm_george', speed=1.00, lang='en-gb', col=(255, 186, 70),  x=210),
    'TARA':     dict(voice='af_heart',  speed=1.05, lang='en-us', col=(255, 105, 200), x=870),
}
CAST['SIGMA'] = dict(voice=None, speed=1.0, lang='', col=SCOL, x=540)   # recorded voice only, never TTS
ORDER = ['REGINALD', 'VEDA', 'TARA']
WELCOME = [
    ('VEDA', "Hello, I'm Veda.", "Hello, I'm VEDA."),
    ('REGINALD', "Reginald, at your service.", "REGINALD, at your service."),
    ('TARA', "And I'm Tara! Welcome to India in Numbers, where we settle your questions with real data!",
     "And I'm TARA! Welcome to INDIA IN NUMBERS, where we settle your questions with real data!"),
]

# ---------------------------------------------------------------- helpers
_fc = {}
def F(n, s):
    if (n, s) not in _fc: _fc[(n, s)] = ImageFont.truetype(os.path.join(FD, n), s)
    return _fc[(n, s)]
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x):
    x = clamp(x); c = 1.70158; c3 = c + 1
    return 1 + c3 * (x - 1) ** 3 + c * (x - 1) ** 2
def shade(c, k): return tuple(int(clamp(v * k, 0, 255)) for v in c)

def put_text(base, xy, s, font, color, alpha=1.0, anchor='mm', scale=1.0):
    if alpha <= 0.003 or not s: return
    asc, desc = font.getmetrics(); w = int(font.getlength(s)) + 12; h = asc + desc + 12
    im = Image.new('RGBA', (w, h), tuple(color) + (0,))
    ImageDraw.Draw(im).text((6, 6), s, font=font, fill=tuple(color) + (255,), anchor='la')
    if alpha < 1: im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    if abs(scale - 1) > 1e-3: im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BICUBIC)
    x, y = xy; iw, ih = im.size
    if anchor[0] == 'm': x -= iw / 2
    elif anchor[0] == 'r': x -= iw
    if anchor[1] == 'm': y -= ih / 2
    base.paste(im, (round(x), round(y)), im)

def fit_font(name, size, s, maxw, minsize=20):
    while size > minsize and F(name, size).getlength(s) > maxw: size -= 2
    return F(name, size)

def indian_group(n):
    s = str(int(round(abs(n)))); neg = n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]; parts = []
        while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        s = ','.join(parts + [tail])
    return ('-' if neg else '') + s

def fmt(v, spec):
    d = spec.get('decimals', 0)
    if spec.get('indian') and d == 0: body = indian_group(v)
    elif d == 0: body = f"{int(round(v)):,}"
    else: body = f"{v:,.{d}f}"
    return f"{spec.get('prefix', '')}{body}{spec.get('suffix', spec.get('unit', ''))}"

# ---------------------------------------------------------------- episode load
EP_DIR = None; EP = None; LINES = []; HOOK = None; HOOK_ENV = None; HOOK_MODE = 'veda'; HOOK_AT = 0.15; T_END = 0
def load(ep_dir):
    global EP_DIR, EP
    global LONG, H, OUT_W, OUT_H, BUB_Y, ROB_Y, NAME_Y
    EP_DIR = ep_dir; EP = json.load(open(os.path.join(ep_dir, 'episode.json')))
    if EP.get('kind') == 'long' or EP.get('chapters'):
        LONG = True; H = 2400; OUT_W, OUT_H = 1920, 1080; BUB_Y, ROB_Y, NAME_Y = 1400, 2000, 2025
    os.makedirs(os.path.join(ep_dir, 'work'), exist_ok=True); os.makedirs(os.path.join(ep_dir, 'out'), exist_ok=True)

def wpath(n): return os.path.join(EP_DIR, 'work', n)

# ---------------------------------------------------------------- voices
_K = None
def kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        _K = Kokoro(os.path.join(MODEL_DIR, 'kokoro-v1.0.onnx'), os.path.join(MODEL_DIR, 'voices-v1.0.bin'))
    return _K

def tts(spk, text, out):
    key = hashlib.md5(f"{spk}|{text}".encode()).hexdigest()[:10]
    cache = os.path.join(MODEL_DIR, 'tts_cache'); os.makedirs(cache, exist_ok=True)
    cpath = os.path.join(cache, key + '.wav')
    if not os.path.exists(cpath):
        c = CAST[spk]; a, sr = kokoro().create(text, voice=c['voice'], speed=c['speed'], lang=c['lang'])
        raw = cpath + '.raw.wav'; sf.write(raw, a, sr)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af',
                        'highpass=f=90,aecho=0.8:0.5:6:0.18,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=24000', '-ac', '1', cpath], check=True)
        os.remove(raw)
    subprocess.run(['cp', cpath, out], check=True)
    return sf.read(out)[0]

def bank_has(cid): return bool(cid) and os.path.exists(os.path.join(BANK, 'clips', f'{cid}.m4a'))
def bank_text(cid):
    try: return json.load(open(os.path.join(BANK, 'bank.json'), encoding='utf-8')).get(cid, {}).get('text', '')
    except Exception: return ''

def sigma_fx():
    fx, st = SIG.get('voice_fx', 'sigma'), float(SIG.get('pitch_semitones', -2.0))
    if fx == 'none': return 'aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=7'
    r = 2 ** (st / 12)
    ch = f'aresample=48000,asetrate={int(48000 * r)},aresample=48000,atempo={1 / r:.5f}'
    if fx == 'sigma': ch += ',aecho=0.8:0.5:14:0.16,equalizer=f=250:t=q:w=1:g=2'
    return ch + ',loudnorm=I=-16:TP=-1.5:LRA=7'

def sigma_audio(src, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', sigma_fx() + f',aresample={SR}', '-ac', '1', out], check=True)
    return sf.read(out)[0]

def sigma_clips(ids, out):
    parts = []
    for k, cid in enumerate(ids):
        parts.append(sigma_audio(os.path.join(BANK, 'clips', f'{cid}.m4a'), wpath(f'sig_{cid}.wav')))
        if k < len(ids) - 1: parts.append(np.zeros(int(0.3 * SR)))
    a = np.concatenate(parts); sf.write(out, a, SR); return a

def env_of(x):
    n = int(len(x) / SR * FPS) + 1; hop = SR // FPS
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(x) else 0 for i in range(n)])
    return np.clip(e / (np.percentile(e[e > 0], 90) + 1e-9), 0, 1) if np.any(e > 0) else e

HOOK_Q0 = 0.0; CHAPTERS = []
def build_lines():
    global LINES, HOOK, HOOK_ENV, HOOK_MODE, T_END, HOOK_Q0, CHAPTERS
    hk = EP['hook']; force_veda = os.environ.get('IIN_HOOK', '') == 'veda'
    rec = [p for p in glob.glob(os.path.join(EP_DIR, 'hook.*')) if p.split('.')[-1].lower() in ('mp3', 'm4a', 'wav', 'ogg', 'aac', 'opus', 'webm')]
    if hk.get('clip') and bank_has(hk['clip']) and not force_veda:
        HOOK_MODE = 'sigma'; intro = [hk['intro']] if hk.get('intro') and bank_has(hk['intro']) else []
        HOOK = sigma_clips(intro + [hk['clip']], wpath('hook.wav'))
        HOOK_Q0 = (len(sigma_clips(intro, wpath('hook_intro.wav'))) / SR + 0.3) if intro else 0.0
    elif rec and not force_veda:
        HOOK_MODE = 'sigma'
        subprocess.run([sys.executable, os.path.join(HERE, 'clean_voice.py'), rec[0], wpath('hook48.wav')], check=True)
        HOOK = sigma_audio(wpath('hook48.wav'), wpath('hook.wav'))
    else:
        if hk.get('clip'): print(f"note: hook clip {hk['clip']} not in the voice bank ({BANK}); VEDA asks instead")
        HOOK_MODE = 'veda'; HOOK = tts('VEDA', hk.get('say', hk['text']), wpath('hook.wav'))
    HOOK_ENV = env_of(HOOK)
    seq = []
    if EP.get('welcome', True):
        for spk, say, cap in WELCOME: seq.append(dict(spk=spk, say=say, cap=cap, visual={'type': 'welcome'}))
    if EP.get('sigma_intro'):
        seq.append(dict(spk='SIGMA', clips=[EP['sigma_intro']], visual={'type': 'sigma', 'kicker': FORMATS.get(EP.get('format', 'long'), FORMATS['long'])[0]}))
    if EP.get('chapters'):
        for n, ch in enumerate(EP['chapters'], 1):
            card = {'type': 'chapter', 'n': n, 'title': ch['title']}
            if ch.get('bridge') and bank_has(ch['bridge']):
                seq.append(dict(spk='SIGMA', clips=[ch['bridge']], visual=card, chapter=ch['title']))
                card = dict(card, quiet=True)
            host = ch.get('host', ['VEDA', 'TARA', 'REGINALD'][n % 3])
            seq.append(dict(spk=host, say=f"Chapter {NUMW[n] if n < len(NUMW) else n}. {ch.get('say_title', ch['title'])}.",
                            cap=f"CHAPTER {n}: {ch['title']}", visual=card, chapter=None if card.get('quiet') else ch['title']))
            seq += ch['lines']
    seq += EP.get('lines', [])
    lw = EP.get('last_word')
    if lw:
        ids = [c for c in (lw.get('react'), lw.get('close')) if c]
        if ids and all(bank_has(c) for c in ids):
            seq.append(dict(spk='SIGMA', clips=ids, cap=lw.get('cap'), visual={'type': 'sigma', 'kicker': lw.get('kicker', 'THE LAST WORD')}))
        else: print(f'note: last_word clips {ids} not all in the voice bank; skipped')
    t = HOOK_AT + len(HOOK) / SR + 0.35
    LINES = []; CHAPTERS = [(0.0, 'Intro')]
    for n, L in enumerate(seq):
        L = dict(L); assert L['spk'] in CAST, L['spk']
        if L['spk'] == 'SIGMA':
            if not L.get('clips') or not all(bank_has(c) for c in L['clips']):
                print(f"note: SIGMA clips {L.get('clips')} missing from the voice bank; line skipped"); continue
            L['audio'] = sigma_clips(L['clips'], wpath(f'l{n}.wav'))
            L['cap'] = L.get('cap') or ' '.join(bank_text(c) for c in L['clips'])
        else:
            L['audio'] = tts(L['spk'], L['say'], wpath(f'l{n}.wav'))
        L['dur'] = len(L['audio']) / SR; L['env'] = env_of(L['audio']); L['start'] = t
        L['vis'] = L.get('visual', {}).get('type', 'none')
        if L.get('chapter'): CHAPTERS.append((t - 0.3, L['chapter']))
        LINES.append(L); t += L['dur'] + (0.5 if L['vis'] == 'chapter' else 0.25)
    T_END = t + 1.2

def wt(L, key, default=0.0):
    """time (s, from line start) at which caption word containing `key` is spoken"""
    if key is None: return default
    if isinstance(key, (int, float)): return float(key)
    words = L['cap'].split(); total = sum(len(w) + 1 for w in words); acc = 0
    for w in words:
        ws = w.strip('.,!?:;"\'()').lower()
        if key.lower() == ws or (len(key) > 2 and key.lower() in w.lower()):
            return acc / total * L['dur'] * 0.93
        acc += len(w) + 1
    return default

# ---------------------------------------------------------------- audio
def synth_sfx(kind, idx=0):
    def X(d): return np.arange(int(d * SR)) / SR
    rng = np.random.default_rng(7)
    if kind in ('pop', 'pop_small', 'bubble'):
        x = X(0.09); f0, f1 = {'pop': (1100, 320), 'pop_small': (1600, 700), 'bubble': (600, 1150)}[kind]
        return np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, len(x))) / SR) * np.exp(-x * 45)
    if kind == 'tick': x = X(0.02); return np.sin(2 * np.pi * 2600 * x) * np.exp(-x * 280)
    if kind == 'rise':
        x = X(0.28); return np.sin(2 * np.pi * np.cumsum(np.linspace(320, 900, len(x))) / SR) * np.sin(np.pi * x / 0.28) * 0.7
    if kind == 'whoosh':
        x = X(0.38); nz = np.convolve(rng.standard_normal(len(x)), np.ones(14) / 14, 'same')
        return nz * np.sin(np.pi * x / 0.38) ** 2 * 2.2
    if kind in ('ding', 'ding2'):
        x = X(0.8); f = 1320 if kind == 'ding' else 1568
        y = sum(a * np.sin(2 * np.pi * f * m * x) for m, a in ((1, 1), (2.01, 0.45), (3.02, 0.2))) * np.exp(-x * 6)
        if kind == 'ding2':
            s2 = int(0.09 * SR); y[s2:] += 0.8 * np.sin(2 * np.pi * 1976 * x[:len(x) - s2]) * np.exp(-x[:len(x) - s2] * 6)
        return y / 1.6
    if kind == 'boing':
        x = X(0.45); f = 180 + 140 * np.sin(2 * np.pi * 11 * x) * np.exp(-x * 4)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 6)
    if kind == 'note':
        x = X(0.45); f = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.5][idx % 8]
        return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 7)
    return np.zeros(1)

def sfx_events():
    ev = [(0.2 + 0.15 * i, 'pop_small', 0.10) for i in range(3)]
    ev += [(at, 'pop', 0.20) for at in hook_times()]
    for L in LINES:
        s0, v, V = L['start'], L['vis'], L.get('visual', {})
        ev += [(s0 - 0.12, 'whoosh', 0.09), (s0 - 0.05, 'bubble', 0.15)]
        if L['spk'] == 'REGINALD' and V.get('boing'): ev.append((s0, 'boing', 0.09))
        if v == 'welcome':
            ev.append((s0 + 0.02, 'pop', 0.16))
            if 'INDIA' in L['cap']: ev += [(s0 + wt(L, 'INDIA') - 0.1, 'ding', 0.2), (s0 + wt(L, 'real'), 'pop_small', 0.12)]
        elif v == 'bars':
            ev += [(s0 + 0.3 + 0.18 * i, 'rise', 0.08) for i in range(len(V['items']))]
            for k, b in enumerate(V.get('badges', [])): ev.append((s0 + wt(L, b.get('at'), 2.5 + 2 * k), 'ding' if k == 0 else 'ding2', 0.22))
        elif v == 'bigstat':
            c0, c1 = count_window(L)
            ev += [(s0 + c0 + k * 0.09, 'tick', 0.07) for k in range(int((c1 - c0) / 0.09))]
            th = V.get('then')
            if th: ev.append((s0 + wt(L, th.get('at'), c1 + 0.6), 'pop', 0.22))
            tl = V.get('tiles')
            if tl:
                t0 = wt(L, tl.get('at'), c1 + 1.0) + 0.45
                ev += [(s0 + t0 + 0.13 * i, 'note', 0.11, i) for i in range(min(8, tl['n']))]
        elif v == 'vs':
            ev += [(s0 + 0.2, 'rise', 0.12)]
            if V.get('pill'): ev.append((s0 + wt(L, V['pill'].get('at'), 1.8), 'pop', 0.22))
        elif v == 'gauge':
            c0, c1 = 0.6, 2.4
            ev += [(s0 + c0 + k * 0.09, 'tick', 0.08) for k in range(20)]
            if V.get('sub'): ev.append((s0 + wt(L, V['sub'].get('at'), 3.0), 'pop', 0.14))
        elif v == 'fact':
            ev.append((s0 + 0.1, 'pop', 0.2))
            for i, ln in enumerate(V.get('lines', [])): ev.append((s0 + wt(L, ln.get('at'), 1.2 + 0.8 * i), 'pop_small', 0.14))
        elif v in ('chapter', 'sigma'):
            ev += [(s0 + 0.05, 'rise', 0.12), (s0 + 0.4, 'ding2' if v == 'sigma' else 'ding', 0.16)]
        elif v == 'cta':
            n = len(V.get('chips', []))
            ev += [(s0 + 0.1, 'pop', 0.22)] + [(s0 + 0.5 + 0.1 * k, 'pop_small', 0.09) for k in range(n)] + [(s0 + 0.5 + 0.1 * n + 0.3, 'ding', 0.2)]
    return ev

def build_audio():
    n = int(T_END * SR); voice = np.zeros(n)
    def place(x, at):
        s = int(at * SR); e = min(n, s + len(x)); voice[s:e] += x[:e - s]
    place(HOOK * 0.95, HOOK_AT)
    for L in LINES: place(L['audio'], L['start'])
    seed = int(EP.get('ep', 1)); rng = np.random.default_rng(seed)
    progs = [[[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]],
             [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]],
             [[293.66, 349.23, 440.0], [233.08, 293.66, 349.23], [261.63, 329.63, 392.0], [220.0, 277.18, 329.63]],
             [[196.0, 246.94, 293.66], [164.81, 196.0, 246.94], [261.63, 329.63, 392.0], [146.83, 185.0, 220.0]]]
    chords = progs[seed % len(progs)]; bpm = [92, 96, 88, 100][seed % 4]
    tt = np.arange(n) / SR; mus = np.zeros(n); beat = 60 / bpm; bar = beat * 4
    for b in range(int(T_END / bar) + 1):
        s = int(b * bar * SR); e = min(n, int((b + 1) * bar * SR)); seg = tt[s:e] - b * bar
        for f in chords[b % 4]:
            mus[s:e] += 0.05 * (np.sin(2 * np.pi * f * tt[s:e]) + 0.2 * np.sin(4 * np.pi * f * tt[s:e])) * np.minimum(1, seg / 0.08)
    for k in range(int(T_END / beat) + 1):
        s = int(k * beat * SR); m = min(n - s, int(0.4 * SR))
        if m <= 0: continue
        x = np.arange(m) / SR
        mus[s:s + m] += 0.35 * np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-x * 35)) / SR) * np.exp(-x * 9)
        h = int((k + 0.5) * beat * SR); mh = min(n - h, int(0.05 * SR))
        if mh > 0: mus[h:h + mh] += 0.05 * np.diff(rng.standard_normal(mh + 1)) * np.exp(-np.arange(mh) / SR * 70)
    venv = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck = 1 - 0.55 * np.clip(venv / 0.08, 0, 1)
    fade = np.minimum(1, tt / 0.6) * np.minimum(1, (T_END - tt) / 1.0)
    sfx = np.zeros(n)
    for at, kind, amp, *ex in sfx_events():
        y = synth_sfx(kind, *ex); st = int(max(0, at) * SR); e = min(n, st + len(y))
        if e > st: sfx[st:e] += amp * y[:e - st]
    mix = voice + mus * 0.55 * duck * fade + sfx
    mix /= max(1e-9, np.abs(mix).max() / 0.95)
    sf.write(wpath('mix.wav'), mix, SR)

# ---------------------------------------------------------------- characters (holograms)
SCAN = Image.new('L', (420, 520), 255); _sd = ImageDraw.Draw(SCAN)
for _y in range(0, 520, 6): _sd.line((0, _y, 420, _y), fill=150)

def robot_layer(spk, mouth, blink, t, active, look):
    L = Image.new('RGBA', (420, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(L, 'RGBA'); cx = 210
    col = CAST[spk]['col']
    def A(al): return col + (int(al),)
    W8 = (240, 255, 255, 255)
    d.polygon([(cx - 70, 488), (cx + 70, 488), (cx + 135, 330), (cx - 135, 330)], fill=A(22))
    d.ellipse((cx - 92, 472, cx + 92, 504), fill=A(70), outline=A(230), width=3)
    d.rounded_rectangle((cx - 132, 322, cx + 132, 452), 70, fill=A(40), outline=A(235), width=4)
    d.rectangle((cx - 26, 280, cx + 26, 326), fill=A(45), outline=A(210), width=3)
    lx = look * 9
    if spk == 'VEDA':
        pts = [(cx - 80, 60), (cx + 80, 60), (cx + 120, 172), (cx + 80, 286), (cx - 80, 286), (cx - 120, 172)]
        d.polygon(pts, fill=A(55)); d.line(pts + [pts[0]], fill=A(245), width=5, joint='curve')
        d.ellipse((cx - 9, 86, cx + 9, 104), fill=W8)
        for ex in (cx - 44, cx + 44):
            h = 4 if blink else 16
            d.rounded_rectangle((ex - 27 + lx, 152 - h / 2, ex + 27 + lx, 152 + h / 2), 7, fill=W8)
        for i in range(7):
            h = 6 + mouth * 46 * (0.45 + 0.55 * abs(math.sin(t * 19 + i * 1.3)))
            x = cx - 48 + i * 16
            d.rounded_rectangle((x - 5, 228 - h / 2, x + 5, 228 + h / 2), 4, fill=W8)
    elif spk == 'REGINALD':
        d.rectangle((cx - 58, 8, cx + 58, 70), fill=A(70), outline=A(245), width=4)
        d.line((cx - 95, 72, cx + 95, 72), fill=A(245), width=7)
        d.rounded_rectangle((cx - 106, 76, cx + 106, 288), 52, fill=A(55), outline=A(245), width=5)
        if blink:
            for ex in (cx - 42, cx + 44): d.line((ex - 15 + lx, 152, ex + 15 + lx, 152), fill=W8, width=5)
        else:
            d.ellipse((cx - 42 - 14 + lx, 138, cx - 42 + 14 + lx, 166), fill=W8)
            d.ellipse((cx + 44 - 13 + lx, 140, cx + 44 + 13 + lx, 164), fill=W8)
        d.ellipse((cx + 44 - 30 + lx, 122, cx + 44 + 30 + lx, 182), outline=W8, width=4)
        d.line((cx + 72 + lx, 170, cx + 84, 268), fill=A(220), width=3)
        d.line((cx - 66, 120, cx - 20, 110), fill=W8, width=5)
        d.chord((cx - 48, 194, cx - 2, 222), 180, 360, fill=W8); d.chord((cx + 2, 194, cx + 48, 222), 180, 360, fill=W8)
        if mouth < 0.08: d.line((cx - 26, 246, cx + 24, 240), fill=W8, width=5)
        else:
            h = 6 + 28 * mouth; d.rounded_rectangle((cx - 26, 244 - h / 2, cx + 24, 244 + h / 2), int(min(h / 2, 10)), fill=W8)
        d.polygon([(cx, 304), (cx - 40, 288), (cx - 40, 320)], fill=W8); d.polygon([(cx, 304), (cx + 40, 288), (cx + 40, 320)], fill=W8)
    else:  # TARA
        d.arc((cx - 132, 44, cx + 132, 270), 195, 345, fill=A(245), width=10)
        d.ellipse((cx - 108, 64, cx + 108, 290), fill=A(55), outline=A(245), width=5)
        for sx in (-1, 1): d.rounded_rectangle((cx + sx * 118 - 18, 140, cx + sx * 118 + 18, 214), 14, fill=A(200))
        for ex in (cx - 40, cx + 40):
            if blink: d.arc((ex - 20 + lx, 140, ex + 20 + lx, 172), 200, 340, fill=W8, width=5)
            else:
                d.ellipse((ex - 22 + lx, 134, ex + 22 + lx, 180), fill=W8)
                d.ellipse((ex - 10 + lx * 1.6, 146, ex + 10 + lx * 1.6, 168), fill=shade(col, 0.6) + (255,))
                d.ellipse((ex - 4 + lx * 1.6 + 5, 147, ex + 4 + lx * 1.6 + 5, 155), fill=W8)
        for ex in (cx - 66, cx + 66): d.ellipse((ex - 12, 196, ex + 12, 208), fill=A(200))
        if mouth < 0.08: d.arc((cx - 24, 192, cx + 24, 230), 20, 160, fill=W8, width=5)
        else:
            h = 14 + 30 * mouth; d.chord((cx - 26, 210 - h / 2, cx + 26, 210 + h / 2), 0, 360, fill=W8)
    fl = 0.86 + 0.14 * math.sin(t * 23 + len(spk))
    L.putalpha(ImageChops.multiply(L.getchannel('A'), SCAN).point(lambda v: int(v * fl)))
    g = L.filter(ImageFilter.GaussianBlur(9))
    out = Image.new('RGBA', L.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(L)
    return out

def draw_robots(img, t, speaker, mouth):
    for i, spk in enumerate(ORDER):
        appear = back(prog(t, 0.05 + 0.15 * i, 0.55 + 0.15 * i))
        if appear <= 0: continue
        active = spk == speaker; m = mouth if active else 0
        ph = {'REGINALD': 0.0, 'VEDA': 1.7, 'TARA': 3.1}[spk]
        blink = ((t + ph) % 3.3) < 0.13
        look = 0.0 if (active or speaker is None) else clamp((CAST[speaker]['x'] - CAST[spk]['x']) / 330, -1, 1)
        L = robot_layer(spk, m, blink, t, active, look)
        sc = (0.63 if active else 0.55) * appear
        if not active: L = ImageEnhance.Brightness(L).enhance(0.62 if speaker else 0.9)
        L = L.resize((max(1, int(420 * sc)), max(1, int(520 * sc))), Image.BICUBIC)
        bob = math.sin(t * (3.2 if active else 1.6) + ph) * (9 if active else 4) - m * 8
        X = CAST[spk]['x']; x = X - L.width / 2; y = ROB_Y - L.height + bob
        if active:
            dd = ImageDraw.Draw(img, 'RGBA')
            for k in range(3):
                a0 = (t * 120 + k * 120) % 360
                dd.arc((X - 150, ROB_Y - 41, X + 150, ROB_Y + 11), a0, a0 + 70, fill=CAST[spk]['col'] + (200,), width=4)
        img.paste(L, (int(x), int(y)), L)
        if appear > 0.6:
            put_text(img, (X, NAME_Y), spk, F('Inter-Bold.otf', 26 if active else 22), CAST[spk]['col'] if active else (150, 150, 175))

# ---------------------------------------------------------------- background / header / hook
def make_bg():
    if LONG: return Image.new('RGB', (W, H), FLAT)
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array((10, 14, 38)) * (1 - y) + np.array((30, 14, 50)) * y) * np.ones((1, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.exp(-(((xx - 540) / 600) ** 2 + ((yy - 700) / 700) ** 2)) * 28
    arr = arr + g[..., None] * np.array([0.6, 0.5, 1.0])
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA')
    for x in range(0, W, 60): d.line((x, 0, x, H), fill=(255, 255, 255, 7))
    for yv in range(0, H, 60): d.line((0, yv, W, yv), fill=(255, 255, 255, 7))
    return im
FLAT = (14, 15, 40)
RNG = np.random.default_rng(9)
DOTS = [(RNG.uniform(0, 1), RNG.uniform(0.02, 0.06), RNG.integers(0, 3), RNG.random() < 0.5) for _ in range(46)]
def ambient(d, t):
    if LONG: return
    lanes = [(250, 1120), (380, 1240), (1010, 1290)]
    for u0, sp, lane, red in DOTS:
        y0, y1 = lanes[lane]; u = (u0 + (sp if red else -sp) * t) % 1
        x = -40 + (W + 80) * u; y = y0 + (y1 - y0) * u * 0.08
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 70, 60, 55) if red else (255, 240, 200, 45))

def header(img, d, t):
    f = F('InterDisplay-Black.otf', 44); s = 'INDIA IN NUMBERS'; sp = 6
    tot = sum(f.getlength(c) for c in s) + sp * (len(s) - 1); x = 540 - tot / 2; a = eo(prog(t, 0, 0.4))
    for c in s: put_text(img, (x, 120), c, f, (255, 255, 255), a, 'lm'); x += f.getlength(c) + sp
    lab, acc = FORMATS.get(EP.get('format') or ('long' if LONG else 'classic'), FORMATS['classic'])
    s = f"{lab} · EP {int(EP.get('ep', 1)):02d}"; w = F('Inter-Bold.otf', 22).getlength(s) + 56
    d.rounded_rectangle((540 - w / 2, 158, 540 + w / 2, 198), 20, fill=acc + (int(255 * a),))
    put_text(img, (540, 178), s, F('Inter-Bold.otf', 22), (20, 14, 30), a)
    hc = (80, 220, 255, 90)
    for (x, y, sx, sy) in ((40, 250, 1, 1), (1040, 250, -1, 1), (40, 945, 1, -1), (1040, 945, -1, -1)):
        d.line((x, y, x + 60 * sx, y), fill=hc, width=4); d.line((x, y, x, y + 60 * sy), fill=hc, width=4)

def hook_lines():
    hk = EP['hook']
    if hk.get('lines'): return hk['lines']
    words = hk['text'].split(); lines, cur = [], []
    for w in words:
        if cur and F('InterDisplay-Black.otf', 110).getlength(' '.join(cur + [w])) > 900: lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines[:5]

_HT = None
def hook_times():
    global _HT
    if _HT is None:
        on = np.where(HOOK_ENV > 0.15)[0]; on = on[on >= int(HOOK_Q0 * FPS)]
        s0, s1 = (on[0] / FPS, on[-1] / FPS) if len(on) else (0.1, len(HOOK) / SR)
        hl = hook_lines(); tot = sum(len(t) + 1 for t in hl); acc = 0; _HT = []
        for t in hl: _HT.append(HOOK_AT + s0 + (s1 - s0) * acc / tot - 0.08); acc += len(t) + 1
    return _HT

def hook_panel(img, d, t):
    end = HOOK_AT + len(HOOK) / SR
    out = eo(prog(t, end + 0.05, end + 0.33)); a0 = eo(prog(t, 0, 0.3)) * (1 - out)
    tag = 'VEDA ASKS' if HOOK_MODE == 'veda' else f'{SGLYPH}  {SNAME} ASKS'
    tc = CAST['VEDA']['col'] if HOOK_MODE == 'veda' else SCOL
    tw = F('Inter-Bold.otf', 22).getlength(tag) + 70
    d.rounded_rectangle((540 - tw / 2, 318, 540 + tw / 2, 362), 22, outline=tc + (int(200 * a0),), width=2)
    put_text(img, (540, 340), tag, F('Inter-Bold.otf', 22), (230, 230, 245), a0)
    hl = hook_lines(); n = len(hl); lh = 130 if n <= 4 else 110
    for k, (s, at) in enumerate(zip(hl, hook_times())):
        p = prog(t, at, at + 0.25)
        if p <= 0: continue
        c = (255, 160, 90) if k == 0 else ((255, 214, 120) if k == n - 1 else (255, 255, 255))
        f = fit_font('InterDisplay-Black.otf', 120, s, 940)
        put_text(img, (540, 480 + k * lh - 40 * out), s, f, c, eo(p) * (1 - out), 'mm', 1 + 0.25 * (1 - back(p)) if p < 1 else 1)
    i = int((t - HOOK_AT) * FPS)
    for b in range(25):
        e = HOOK_ENV[i] if 0 <= i < len(HOOK_ENV) else 0
        h = 8 + 120 * e * (0.55 + 0.45 * math.sin(b * 1.7 + t * 9) ** 2)
        x = 540 + (b - 12) * 28
        d.rounded_rectangle((x - 9, 1040 - h / 2, x + 9, 1040 + h / 2), 9, fill=tc + (int(220 * a0),))

# ---------------------------------------------------------------- visual panels
def panel_welcome(img, d, u, a, L):
    t = L['start'] + u; WL = [x for x in LINES if x['vis'] == 'welcome']; last = WL[-1]
    a = eo(prog(t, WL[0]['start'] - 0.05, WL[0]['start'] + 0.3))
    for Lw in WL:
        q = prog(t, Lw['start'], Lw['start'] + 0.35)
        if q <= 0: continue
        k = Lw['spk']; sc = back(q); f = F('InterDisplay-Black.otf', 48)
        w = (f.getlength(k) + 60) * sc; h = 88 * sc; x = CAST[k]['x']; y = 420
        d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), int(h / 2), fill=CAST[k]['col'] + (int(255 * a),))
        put_text(img, (x, y), k, f, (14, 14, 28), a, 'mm', sc)
    ti = last['start'] + wt(last, 'INDIA')
    p = prog(t, ti - 0.35, ti - 0.05)
    if p > 0: put_text(img, (540, 590), 'Welcome to', F('Inter-SemiBold.otf', 46), (190, 198, 235), a * eo(p))
    p = prog(t, ti - 0.1, ti + 0.25)
    if p > 0: put_text(img, (540, 690), 'INDIA IN NUMBERS', fit_font('InterDisplay-Black.otf', 110, 'INDIA IN NUMBERS', 960), (255, 255, 255), a * eo(p), 'mm', back(p) if p < 1 else 1)
    tr = last['start'] + wt(last, 'real'); q = prog(t, tr, tr + 0.35)
    if q > 0: put_text(img, (540, 830 + 20 * (1 - eo(q))), 'Real data. Real arguments.', F('Inter-Bold.otf', 44), (255, 186, 70), a * eo(q))

def titles(img, V, a, y0=315):
    if V.get('title'): put_text(img, (540, y0), V['title'], fit_font('Inter-SemiBold.otf', 42, V['title'], 940), (200, 206, 240), a)
    if V.get('subtitle'): put_text(img, (540, y0 + 48), V['subtitle'], fit_font('Inter-Regular.otf', 26, V['subtitle'], 940), (130, 136, 175), a)

def badge(img, d, s, x, y, col, p, a, size=44):
    if p <= 0: return
    sc = back(p); f = F('InterDisplay-Black.otf', size); w = (f.getlength(s) + 60) * sc; h = size * 1.9 * sc
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), int(h / 2), fill=tuple(col) + (int(255 * a),))
    put_text(img, (x, y), s, f, (20, 14, 30), a, 'mm', sc)

HI = (255, 138, 61); LO = (90, 110, 210); GOLD = (255, 214, 120)

def panel_bars(img, d, u, a, L):
    V = L['visual']; titles(img, V, a); items = V['items']; n = len(items)
    vmax = V.get('max') or max(v for _, v in items) * 1.08
    hl = V.get('highlight', 0); hl = hl if isinstance(hl, list) else [hl]
    sp = min(92, 400 / max(1, n - 1)); lw = max(F('Inter-Bold.otf', 36).getlength(str(c)) for c, _ in items)
    lf = F('Inter-Bold.otf', 36) if lw < 250 else F('Inter-Bold.otf', int(36 * 250 / lw))
    for i, (c, v) in enumerate(items):
        y = 440 + i * sp; p = eo(prog(u, 0.3 + 0.18 * i, 1.4 + 0.18 * i)); hi = i in hl
        put_text(img, (70, y), str(c), lf, (255, 255, 255) if hi else (205, 210, 235), a * min(1, p * 3), 'lm')
        bw = max(0, v) / vmax * 470 * p
        if bw > 4:
            d.rounded_rectangle((330, y - 26, 330 + bw, y + 26), 14, fill=(HI if hi else LO) + (int(255 * a),))
        put_text(img, (330 + bw + 16, y), fmt(v * p, V), F('Inter-Bold.otf', 32), (255, 255, 255), a * min(1, p * 3), 'lm')
    bs = V.get('badges', [])
    xs = [540] if len(bs) == 1 else [300, 780]
    for k, b in enumerate(bs[:2]):
        at = wt(L, b.get('at'), 2.5 + 2 * k)
        badge(img, d, b['text'], xs[k], 885, HI if k == 0 else GOLD, prog(u, at, at + 0.35), a)

def count_window(L):
    V = L['visual']; c0 = wt(L, V.get('count_at'), 0.5); return max(0.3, c0 - 0.1), max(c0 + 1.2, c0 + 1.8)

def note_icon(d, x, y, s, a, col):
    d.ellipse((x - 11 * s, y - 8 * s, x + 11 * s, y + 8 * s), fill=col + (int(255 * a),))
    d.line((x + 9 * s, y, x + 9 * s, y - 38 * s), fill=col + (int(255 * a),), width=max(2, int(5 * s)))
    d.line((x + 9 * s, y - 38 * s, x + 24 * s, y - 28 * s), fill=col + (int(255 * a),), width=max(2, int(5 * s)))

def panel_bigstat(img, d, u, a, L):
    V = L['visual']; titles(img, V, a, 300) if V.get('title') else None
    c0, c1 = count_window(L); val = V['value'] * eo(prog(u, c0, c1))
    col = tuple(V.get('color', CAST[L['spk']]['col']))
    s = fmt(val, V); f = fit_font('InterDisplay-Black.otf', 190, fmt(V['value'], V), 960)
    put_text(img, (540, 450), s, f, col, a)
    if V.get('label'): put_text(img, (540, 575), V['label'], fit_font('Inter-SemiBold.otf', 38, V['label'], 940), (200, 205, 235), a)
    th = V.get('then')
    if th:
        at = wt(L, th.get('at'), c1 + 0.6); pe = prog(u, at, at + 0.35)
        if pe > 0: put_text(img, (540, 675), th['text'], fit_font('InterDisplay-Black.otf', 68, th['text'], 960), GOLD, a * eo(pe), 'mm', back(pe))
    tl = V.get('tiles')
    if tl:
        n = min(8, tl['n']); t0 = wt(L, tl.get('at'), c1 + 1.0) + 0.45; tw = min(112, (900 - 12 * (n - 1)) / n)
        x0 = 540 - (n * tw + (n - 1) * 12) / 2
        for i in range(n):
            p = prog(u, t0 + 0.13 * i, t0 + 0.35 + 0.13 * i)
            if p <= 0: continue
            sc = back(p); x = x0 + i * (tw + 12) + tw / 2; y = 830; w = tw * sc; h = 140 * sc
            d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), int(18 * sc), fill=(255, 255, 255, int(235 * a)))
            d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y - h / 2 + 34 * sc), int(18 * sc), fill=col + (int(255 * a),))
            put_text(img, (x, y - h / 2 + 17 * sc), f"{tl.get('label', '')} {i + 1}".strip(), F('Inter-Bold.otf', 20), (255, 255, 255), a, 'mm', sc)
            if tl.get('icon', 'note') == 'note':
                note_icon(d, x - 6, y + 34 * sc + (math.sin(u * 10 + i) * 6 if u > t0 + 1.5 else 0), sc, a, (90, 60, 160))
            else:
                put_text(img, (x, y + 18 * sc), str(tl['icon']), F('InterDisplay-Black.otf', 44), (40, 30, 70), a, 'mm', sc)

def panel_vs(img, d, u, a, L):
    V = L['visual']
    put_text(img, (540, 320), V.get('title', ''), fit_font('InterDisplay-Black.otf', 70, V.get('title', ''), 960), (255, 255, 255), a)
    if V.get('subtitle'): put_text(img, (540, 380), V['subtitle'], F('Inter-Regular.otf', 30), (170, 176, 210), a)
    base = 930; vmax = V.get('max') or max(V['a'][1], V['b'][1]) * 1.08
    hb = V.get('highlight', 'a') == 'b'
    for x, (c, v), col in ((360, V['a'], LO if hb else HI), (720, V['b'], HI if hb else LO)):
        p = eo(prog(u, 0.2, 1.0)); h = max(0, v) / vmax * 380 * p
        if h > 4:
            d.rounded_rectangle((x - 95, base - h, x + 95, base), 20, fill=col + (int(255 * a),))
            put_text(img, (x, base - h - 36), fmt(v * p, V), fit_font('InterDisplay-Black.otf', 52, fmt(v, V), 300), (255, 255, 255), a)
        put_text(img, (x, base + 34), str(c), fit_font('Inter-Bold.otf', 36, str(c), 330), (220, 224, 245), a)
    if V.get('pill'):
        at = wt(L, V['pill'].get('at'), 1.8); p = prog(u, at, at + 0.4)
        if p > 0:
            sc = back(p); s = V['pill']['text']; f = fit_font('Inter-Bold.otf', 36, s, 820); w = (f.getlength(s) + 56) * sc; h = 70 * sc
            d.rounded_rectangle((540 - w / 2, 440 - h / 2, 540 + w / 2, 440 + h / 2), int(h / 2), fill=GOLD + (int(255 * a),))
            put_text(img, (540, 440), s, f, (20, 14, 30), a, 'mm', sc)

def panel_gauge(img, d, u, a, L):
    V = L['visual']
    if V.get('title'): put_text(img, (540, 340), V['title'], fit_font('InterDisplay-Black.otf', 84, V['title'], 960), (255, 255, 255), a)
    m = V['value'] * eo(prog(u, 0.6, 2.4)); cy, R = 680, 170; mx = V.get('max', V['value'] * 1.5)
    d.ellipse((540 - R, cy - R, 540 + R, cy + R), outline=(255, 255, 255, int(40 * a)), width=18)
    if m > 1e-6: d.arc((540 - R, cy - R, 540 + R, cy + R), -90, -90 + 360 * min(1, m / mx), fill=HI + (int(255 * a),), width=18)
    s = f"{int(m):02d}:{int((m % 1) * 60):02d}" if V.get('format') == 'mm:ss' else fmt(m, V)
    put_text(img, (540, cy - 12), s, fit_font('InterDisplay-Black.otf', 96, s, 2 * R - 50), (255, 255, 255), a)
    if V.get('unit_label'): put_text(img, (540, cy + 66), V['unit_label'], F('Inter-SemiBold.otf', 30), (180, 186, 220), a)
    sb = V.get('sub')
    if sb:
        at = wt(L, sb.get('at'), 3.0); pe = eo(prog(u, at, at + 0.4))
        put_text(img, (540, 925 + 20 * (1 - pe)), sb['text'], fit_font('Inter-Bold.otf', 36, sb['text'], 940), (255, 190, 120), a * pe)

def panel_fact(img, d, u, a, L):
    V = L['visual']
    if V.get('kicker'): put_text(img, (540, 330), V['kicker'], fit_font('Inter-SemiBold.otf', 40, V['kicker'], 940), (190, 198, 235), a)
    p = prog(u, 0.1, 0.45)
    put_text(img, (540, 460), V['big'], fit_font('InterDisplay-Black.otf', 150, V['big'], 960), tuple(V.get('color', GOLD)), a * eo(p), 'mm', back(p) if p < 1 else 1)
    for i, ln in enumerate(V.get('lines', [])[:3]):
        at = wt(L, ln.get('at'), 1.2 + 0.8 * i); q = prog(u, at, at + 0.35)
        if q > 0: put_text(img, (540, 610 + i * 95 + 20 * (1 - eo(q))), ln['text'], fit_font('Inter-Bold.otf', 46, ln['text'], 940), (255, 255, 255), a * eo(q))

def panel_cta(img, d, u, a, L):
    V = L['visual']; p = prog(u, 0.1, 0.45); title = V.get('title', 'Your city?')
    if not LONG and V.get('support', True) and 'SUBSCRIBE' not in [str(c).upper() for c in V.get('chips', [])]: support_pills(img, d, u, a)
    put_text(img, (540, 400), title, fit_font('InterDisplay-Black.otf', 120, title, 960), (255, 255, 255), a * eo(p), 'mm', back(p) if p < 1 else 1)
    chips = V.get('chips', []); f = F('Inter-Bold.otf', 36); rows, cur, k = [], [], 0
    for c in chips:
        if cur and sum(f.getlength(x) + 68 for x in cur + [c]) > 960: rows.append(cur); cur = [c]
        else: cur.append(c)
    if cur: rows.append(cur)
    for r, row in enumerate(rows[:3]):
        ws = [f.getlength(c) + 50 for c in row]; tot = sum(ws) + 18 * (len(row) - 1); x = 540 - tot / 2
        for c, w in zip(row, ws):
            q = prog(u, 0.5 + 0.1 * k, 0.8 + 0.1 * k); k += 1
            if q > 0:
                sc = back(q); y = 580 + r * 100
                d.rounded_rectangle((x + w / 2 - w * sc / 2, y - 34 * sc, x + w / 2 + w * sc / 2, y + 34 * sc), int(34 * sc), outline=(255, 255, 255, int(200 * a)), width=3)
                put_text(img, (x + w / 2, y), c, f, (255, 255, 255), a, 'mm', sc)
            x += w + 18
    q = prog(u, 0.5 + 0.1 * len(chips) + 0.3, 0.9 + 0.1 * len(chips) + 0.3)
    if q > 0:
        sc = back(q) * (1 + 0.05 * math.sin(u * 7)); cx, cy = 540, 880; b = V.get('button', 'COMMENT')
        d.rounded_rectangle((cx - 150 * sc, cy - 70 * sc, cx + 150 * sc, cy + 70 * sc), int(40 * sc), fill=HI + (int(255 * a),))
        d.polygon([(cx - 60 * sc, cy + 66 * sc), (cx - 100 * sc, cy + 110 * sc), (cx - 20 * sc, cy + 66 * sc)], fill=HI + (int(255 * a),))
        put_text(img, (cx, cy), b, fit_font('InterDisplay-Black.otf', 50, b, 270), (20, 14, 30), a, 'mm', sc)

def glow_text(img, xy, s, font, col, a, scale=1.0, blur=18):
    asc, desc = font.getmetrics(); w = int(font.getlength(s)) + 2 * blur + 20; h = asc + desc + 2 * blur + 20
    lay = Image.new('RGBA', (w, h), col + (0,)); ImageDraw.Draw(lay).text((w / 2, h / 2), s, font=font, fill=col + (255,), anchor='mm')
    g = lay.filter(ImageFilter.GaussianBlur(blur)); out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(lay)
    if a < 1: out.putalpha(out.getchannel('A').point(lambda v: int(v * a)))
    if abs(scale - 1) > 1e-3: out = out.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BICUBIC)
    img.paste(out, (int(xy[0] - out.width / 2), int(xy[1] - out.height / 2)), out)

def panel_sigma(img, d, u, a, L):
    V = L['visual']; p = prog(u, 0.05, 0.45)
    put_text(img, (540, 345), V.get('kicker', 'THE LAST WORD'), F('Inter-Bold.otf', 40), SCOL, a * eo(p))
    j = int(u * FPS); e = float(L['env'][j]) if 0 <= j < len(L['env']) else 0.0
    glow_text(img, (540, 600), SGLYPH, F('InterDisplay-Black.otf', 300), SCOL, a * eo(p), (back(p) if p < 1 else 1) * (1 + 0.06 * e))
    put_text(img, (540, 820), SNAME, F('InterDisplay-Black.otf', 60), (240, 236, 255), a * eo(prog(u, 0.3, 0.6)))
    if not LONG and V.get('kicker', 'THE LAST WORD') == 'THE LAST WORD':
        support_pills(img, d, u + 0.6, a)
        put_text(img, (540, 905), EP.get('follow_line', 'A new question every day. Follow along!'), F('Inter-SemiBold.otf', 34), (200, 196, 235), a * eo(prog(u, 0.8, 1.2)))
    for k in range(3):
        r = 150 + 40 * k + 30 * ((u * 0.8 + k / 3) % 1)
        d.ellipse((540 - r, 600 - r, 540 + r, 600 + r), outline=SCOL + (int(90 * a * (1 - ((u * 0.8 + k / 3) % 1))),), width=3)

def panel_chapter(img, d, u, a, L):
    V = L['visual']; p = prog(u, 0.05, 0.4); acc = FORMATS.get(EP.get('format', 'long'), FORMATS['long'])[1]
    put_text(img, (540, 420), f"CHAPTER {V.get('n', 1)}", F('Inter-Bold.otf', 48), acc, a * eo(p))
    words = V.get('title', '').split(); f = F('InterDisplay-Black.otf', 110)
    for size in (110, 96, 84, 72):
        f = F('InterDisplay-Black.otf', size); ls = wrap(words, f, 940)
        if len(ls) <= 3: break
    for k, ln in enumerate(ls[:3]):
        q = prog(u, 0.15 + 0.12 * k, 0.5 + 0.12 * k)
        put_text(img, (540, 560 + k * size * 1.1), ' '.join(ln), f, (255, 255, 255), a * eo(q), 'mm', back(q) if q < 1 else 1)
    w = 600 * eo(prog(u, 0.3, 0.9)); y = 560 + len(ls[:3]) * size * 1.1 + 10
    d.rounded_rectangle((540 - w / 2, y, 540 + w / 2, y + 8), 4, fill=acc + (int(255 * a),))

def support_pills(img, d, u, a, y=262):
    """Small LIKE · SHARE · SUBSCRIBE pills that pop in one by one (Shorts closing card + Last Word)."""
    items = [('LIKE', HI), ('SHARE', (80, 200, 255)), ('SUBSCRIBE', (255, 70, 70))]; f = F('Inter-Bold.otf', 30)
    ws = [f.getlength(t) + 48 for t, _ in items]; x = 540 - (sum(ws) + 16 * (len(ws) - 1)) / 2
    for k, ((t, col), w) in enumerate(zip(items, ws)):
        q = prog(u, 0.6 + 0.18 * k, 0.9 + 0.18 * k)
        if q > 0:
            sc = back(q) * (1 + (0.06 * math.sin(u * 6) if t == 'SUBSCRIBE' and q >= 1 else 0)); cx = x + w / 2
            d.rounded_rectangle((cx - w * sc / 2, y - 26 * sc, cx + w * sc / 2, y + 26 * sc), int(26 * sc), fill=col + (int(255 * a),))
            put_text(img, (cx, y), t, f, (255, 255, 255) if t != 'LIKE' else (20, 14, 30), a, 'mm', sc)
        x += w + 16

PANELS = {'welcome': panel_welcome, 'sigma': panel_sigma, 'chapter': panel_chapter, 'bars': panel_bars, 'bigstat': panel_bigstat, 'vs': panel_vs,
          'gauge': panel_gauge, 'fact': panel_fact, 'cta': panel_cta, 'none': lambda *a: None}

def wrap(words, f, maxw):
    lines, cur = [], []
    for w in words:
        if cur and f.getlength(' '.join(cur + [w])) > maxw: lines.append(cur); cur = [w]
        else: cur.append(w)
    if cur: lines.append(cur)
    return lines

def bubble(img, d, L, u):
    p = prog(u, -0.05, 0.25); sc = 0.9 + 0.1 * back(p); a = eo(prog(u, -0.05, 0.12))
    words = L['cap'].split()
    for size in (46, 42, 38, 34):
        f = F('Inter-Bold.otf', size); lines = wrap(words, f, 860)
        if len(lines) <= 3: break
    lh = size * 1.28; bh = 60 + lh * len(lines) + 18; top = BUB_Y - bh - 22
    cxm, cym = 540, top + bh / 2
    def S(x, y): return (cxm + (x - cxm) * sc, cym + (y - cym) * sc)
    tx = CAST[L['spk']]['x']; col = CAST[L['spk']]['col']
    d.polygon([S(tx - 26, top + bh - 2), S(tx + 26, top + bh - 2), S(tx, top + bh + 30)], fill=(250, 248, 255, int(255 * a)))
    bx0, by0 = S(60, top); bx1, by1 = S(1020, top + bh)
    d.rounded_rectangle((bx0, by0, bx1, by1), int(32 * sc), fill=(250, 248, 255, int(255 * a)))
    nm = f'{SGLYPH} {SNAME}' if L['spk'] == 'SIGMA' else L['spk']
    nf = F('Inter-Bold.otf', 24); nw = nf.getlength(nm) + 36
    d.rounded_rectangle((bx0 + 28, by0 - 20, bx0 + 28 + nw, by0 + 22), 21, fill=col + (int(255 * a),))
    put_text(img, (bx0 + 28 + nw / 2, by0 + 1), nm, nf, (255, 255, 255) if L['spk'] != 'SIGMA' else (24, 18, 50), a)
    total = sum(len(w) + 1 for w in words); done = clamp(u / (L['dur'] * 0.93)) * total; acc = 0
    for li, ln in enumerate(lines):
        y = top + 50 + li * lh + lh / 2 - 12; x = 540 - f.getlength(' '.join(ln)) / 2
        for w in ln:
            acc += len(w) + 1
            put_text(img, S(x, y), w, f, (24, 20, 40) if acc <= done + 2 else (175, 172, 195), a, 'lm', sc)
            x += f.getlength(w + ' ')

BG = None
def frame(i):
    t = i / FPS; img = BG.copy(); d = ImageDraw.Draw(img, 'RGBA'); ambient(d, t); header(img, d, t)
    cur = None
    for L in LINES:
        if t >= L['start'] - 0.05: cur = L
    speaker, mouth = None, 0.0
    if cur is None:
        hook_panel(img, d, t)
        if HOOK_MODE == 'veda':
            j = int((t - HOOK_AT) * FPS)
            if 0 <= j < len(HOOK_ENV): speaker, mouth = 'VEDA', float(HOOK_ENV[j]) ** 0.7
    else:
        u = t - cur['start']; a = eo(prog(u, -0.05, 0.3))
        PANELS[cur['vis']](img, d, u, a, cur)
        bubble(img, d, cur, u)
        j = int(u * FPS)
        if 0 <= j < len(cur['env']): speaker, mouth = cur['spk'], float(cur['env'][j]) ** 0.7
        elif u < cur['dur'] + 0.25: speaker = cur['spk']
    draw_robots(img, t, speaker, mouth)
    return compose_land(img, t, cur) if LONG else img

LBG = None; DECOR = None
def land_assets():
    global LBG, DECOR
    LBG = Image.new('RGBA', (OUT_W, OUT_H), FLAT + (255,))
    yy, xx = np.mgrid[0:OUT_H, 0:OUT_W]
    g = np.exp(-(((xx - 600) / 900) ** 2 + ((yy - 520) / 600) ** 2))
    vig = np.clip(((xx - OUT_W / 2) / (OUT_W * 0.62)) ** 2 + ((yy - OUT_H / 2) / (OUT_H * 0.7)) ** 2, 0, 1)
    arr = np.zeros((OUT_H, OUT_W, 4)); arr[..., 0] = 120; arr[..., 1] = 90; arr[..., 2] = 255
    arr[..., 3] = g * 34
    dk = vig * 110; arr[..., :3] = arr[..., :3] * (arr[..., 3:4] / (arr[..., 3:4] + dk[..., None] + 1e-6))
    arr[..., 3] = arr[..., 3] + dk
    DECOR = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA'); dd = ImageDraw.Draw(DECOR)
    for x in range(0, OUT_W, 60): dd.line((x, 0, x, OUT_H), fill=(255, 255, 255, 7))
    for y in range(0, OUT_H, 60): dd.line((0, y, OUT_W, y), fill=(255, 255, 255, 7))
    dd.line((1130, 150, 1130, 1010), fill=(255, 255, 255, 22), width=2)

def compose_land(p, t, cur):
    out = LBG.copy()
    out.paste(p.crop((0, 70, 1080, 215)).resize((756, 101), Image.LANCZOS), (582, 6))
    out.paste(p.crop((0, 240, 1080, 1110)), (30, 165))
    out.paste(p.crop((0, 1095, 1080, 1445)).resize((734, 238), Image.LANCZOS), (1160, 330))
    out.paste(p.crop((0, 1640, 1080, 2050)).resize((734, 279), Image.LANCZOS), (1160, 640))
    out.alpha_composite(DECOR); d = ImageDraw.Draw(out, 'RGBA')
    chap = [c for c in CHAPTERS if c[0] <= t][-1][1] if CHAPTERS else ''
    acc = FORMATS.get(EP.get('format', 'long'), FORMATS['long'])[1]
    put_text(out, (1527, 190), chap.upper(), fit_font('Inter-Bold.otf', 30, chap.upper(), 700), acc, eo(prog(t, 0.3, 0.8)))
    w = 700 * clamp(t / T_END); d.rounded_rectangle((1177, 240, 1877, 246), 3, fill=(255, 255, 255, 40))
    d.rounded_rectangle((1177, 240, 1177 + w, 246), 3, fill=acc + (220,))
    for c0, _ in CHAPTERS[1:]:
        x = 1177 + 700 * clamp(c0 / T_END); d.ellipse((x - 5, 238, x + 5, 248), fill=(255, 255, 255, 180))
    return out.convert('RGB')

def make_thumb():
    """1280x720 thumbnail: big short text left (episode "thumb_text", else the title), the three hosts right, Σ badge."""
    import re
    Wt, Ht = 1280, 720; acc = FORMATS.get(EP.get('format', 'long'), FORMATS['long'])[1]
    yy, xx = np.mgrid[0:Ht, 0:Wt]
    arr = np.array(FLAT, float) * np.ones((Ht, Wt, 1)) + np.exp(-(((xx - 980) / 420) ** 2 + ((yy - 420) / 320) ** 2))[..., None] * np.array([60, 40, 110])
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'); d = ImageDraw.Draw(img, 'RGBA')
    for i, spk in enumerate(['REGINALD', 'VEDA', 'TARA']):
        L = robot_layer(spk, 0.5 if spk == 'TARA' else 0.0, False, 1.0 + i, True, 0.0)
        sc = 0.78 if spk == 'VEDA' else 0.66; L = L.resize((int(420 * sc), int(520 * sc)), Image.BICUBIC)
        x = [830, 990, 1150][i]; img.alpha_composite(L, (int(x - L.width / 2), int(690 - L.height)))
    text = EP.get('thumb_text') or re.sub(r'[^\w\s,.?!%₹-]', '', EP.get('title', EP['hook']['text'])).strip()
    words = text.split()
    for size in (120, 108, 96, 84, 72):
        f = F('InterDisplay-Black.otf', size); ls = wrap(words, f, 680)
        if len(ls) <= 4: break
    y = 360 - len(ls) * size * 1.05 / 2 + size * 0.5
    for k, ln in enumerate(ls[:4]):
        s = ' '.join(ln); col = acc if any(ch.isdigit() for ch in s) or (k == 0 and not any(any(c.isdigit() for c in ' '.join(x)) for x in ls)) else (255, 255, 255)
        for dx, dy in ((4, 5), (0, 0)):
            put_text(img, (60 + dx, y + k * size * 1.05 + dy), s, f, (0, 0, 0) if dx else col, 0.55 if dx else 1, 'lm')
    d.rounded_rectangle((60, 34, 60 + F('Inter-Bold.otf', 30).getlength('INDIA IN NUMBERS') + 40, 84), 25, fill=acc + (255,))
    put_text(img, (80, 59), 'INDIA IN NUMBERS', F('Inter-Bold.otf', 30), (20, 14, 30), 1, 'lm')
    glow_text(img, (1190, 95), SGLYPH, F('InterDisplay-Black.otf', 110), SCOL, 1.0, 1.0, 14)
    return img.convert('RGB')

def slug():
    return f"ep{int(EP.get('ep', 1)):02d}_{EP.get('slug', 'episode')}"

def stamp_now():
    import datetime
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist).strftime('%Y-%m-%d_%H-%M')

def write_upload_txt(stamp):
    tags = ' '.join(EP.get('hashtags', []))
    src = '\n'.join(f"Source: {s['name']} — {s['url']}" for s in EP.get('sources', []))
    txt = f"""TITLE
{EP.get('title', '')}

DESCRIPTION
{EP.get('description', '')}

{src}
{tags}

HOOK LINE
"{EP['hook']['text']}"
""" + (('\nCHAPTERS\n' + '\n'.join(f"{int(c // 60)}:{int(c % 60):02d} {n}" for c, n in CHAPTERS) + '\n') if LONG else '')
    for f in glob.glob(os.path.join(EP_DIR, 'out', '*_upload.txt')): os.remove(f)
    open(os.path.join(EP_DIR, 'out', f"{stamp}_{slug()}_upload.txt"), 'w').write(txt)

def main():
    global BG
    ep_dir = sys.argv[1]; load(ep_dir); build_lines(); BG = make_bg()
    if LONG: land_assets()
    if '--preview' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--preview') + 1].split(',')]
        tw, th = (640, 360) if LONG else (360, 640); cols = 3 if LONG else len(ts); rows = (len(ts) + cols - 1) // cols
        tiles = [frame(int(tt * FPS)).resize((tw, th), Image.LANCZOS) for tt in ts]
        sheet = Image.new('RGB', (tw * cols, th * rows))
        for k, tl in enumerate(tiles): sheet.paste(tl, (tw * (k % cols), th * (k // cols)))
        sheet.save(os.path.join(EP_DIR, 'work', 'preview.jpg'), quality=88)
        print('T_END', round(T_END, 2), 'starts', [round(L['start'], 2) for L in LINES]); return
    if '--dry' in sys.argv: print('T_END', round(T_END, 1), 'chapters', CHAPTERS); return
    if '--thumb' in sys.argv: make_thumb().save(wpath('thumb.jpg'), quality=92); print('thumb', wpath('thumb.jpg')); return
    build_audio()
    vid = wpath('video.mp4')
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OUT_W}x{OUT_H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', vid], stdin=subprocess.PIPE)
    NF = int(T_END * FPS)
    for i in range(NF):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close(); p.wait(); assert p.returncode == 0
    stamp = stamp_now(); name = f"{stamp}_{slug()}_{HOOK_MODE}.mp4"; out = os.path.join(EP_DIR, 'out', name); tmp = out[:-4] + '.tmp.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wpath('mix.wav'), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-shortest', tmp], check=True)
    os.replace(tmp, out); write_upload_txt(stamp)
    for f in glob.glob(os.path.join(EP_DIR, 'out', '*_chapters.json')) + glob.glob(os.path.join(EP_DIR, 'out', '*_thumb.jpg')): os.remove(f)
    if LONG:
        json.dump([[round(c, 1), n] for c, n in CHAPTERS], open(os.path.join(EP_DIR, 'out', f"{stamp}_{slug()}_chapters.json"), 'w'))
        make_thumb().save(os.path.join(EP_DIR, 'out', f"{stamp}_{slug()}_thumb.jpg"), quality=92)
    print('DONE', out, round(T_END, 1), 's')

if __name__ == '__main__':
    main()

"""Clean + enhance a phone voice recording.
usage: python3 clean_voice.py input.m4a output.wav [--before before.wav]
"""
import subprocess, sys, numpy as np, soundfile as sf, noisereduce as nr

src, dst = sys.argv[1], sys.argv[2]
SR = 48000
raw = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(SR), '-af', 'highpass=f=70',
                                    '-f', 'f32le', '-'], capture_output=True, check=True).stdout, np.float32).copy()

# find speech region from short-term energy
hop = SR // 50
e = np.array([np.sqrt(np.mean(raw[i:i + hop] ** 2)) for i in range(0, len(raw) - hop, hop)])
thr = max(np.percentile(e, 20) * 4, e.max() * 0.08)
on = np.where(e > thr)[0]
# group into phrases (gaps < 0.7 s), keep the phrase group carrying the most energy (drops stray clicks/bumps)
groups, cur = [], [on[0]]
for i in on[1:]:
    if i - cur[-1] <= 35: cur.append(i)
    else: groups.append(cur); cur = [i]
groups.append(cur)
best = max(groups, key=lambda g: e[g].sum())
s0 = max(0, best[0] * hop - int(0.25 * SR)); s1 = min(len(raw), (best[-1] + 1) * hop + int(0.35 * SR))
# noise profile = quiet frames outside speech
quiet = np.concatenate([raw[:max(s0, 1)], raw[s1:]]) if (s0 + len(raw) - s1) > SR * 0.3 else None

if '--before' in sys.argv:
    sf.write(sys.argv[sys.argv.index('--before') + 1], raw[s0:s1] / (np.abs(raw[s0:s1]).max() + 1e-9) * 0.9, SR)

den = nr.reduce_noise(y=raw, sr=SR, y_noise=quiet, stationary=quiet is not None, prop_decrease=0.9, n_fft=2048)
den = den[s0:s1]
fade = int(0.04 * SR); den[:fade] *= np.linspace(0, 1, fade); den[-fade:] *= np.linspace(1, 0, fade)
DEN = dst + '.den.wav'; sf.write(DEN, den, SR)

chain = ','.join([
    'arnndn=m=' + __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'models', 'sh.rnnn') + ':mix=0.8',          # neural speech denoise (removes what's left)
    'highpass=f=80',
    'equalizer=f=170:t=q:w=1:g=2',              # warmth
    'equalizer=f=400:t=q:w=1.2:g=-2',           # less boxy phone sound
    'equalizer=f=3500:t=q:w=1:g=3',             # presence / clarity
    'equalizer=f=10000:t=q:w=1:g=2.5',          # air
    'deesser=i=0.4',
    'acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=2',
    'loudnorm=I=-15:TP=-1.5:LRA=6',
    'aresample=48000',
])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', DEN, '-af', chain, '-ac', '1', dst], check=True)
print('speech', round(s0 / SR, 2), '-', round(s1 / SR, 2), 's ->', dst)

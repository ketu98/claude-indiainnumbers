#!/usr/bin/env bash
# One-time (per session) setup for the India in Numbers video engine. Safe to re-run.
set -e
CACHE="${IIN_MODELS:-$HOME/.cache/iin}"
mkdir -p "$CACHE"

command -v ffmpeg >/dev/null || { echo "ffmpeg missing — install it (apt-get install -y ffmpeg)"; exit 1; }
python3 -c "import kokoro_onnx, soundfile, noisereduce" 2>/dev/null || \
  pip install -q --break-system-packages kokoro-onnx soundfile noisereduce numpy pillow

# Voice model (free, open source: Kokoro 82M via kokoro-onnx GitHub releases)
REL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s "$CACHE/kokoro-v1.0.onnx" ] || curl -sL --retry 3 -o "$CACHE/kokoro-v1.0.onnx" "$REL/kokoro-v1.0.onnx"
[ -s "$CACHE/voices-v1.0.bin" ]  || curl -sL --retry 3 -o "$CACHE/voices-v1.0.bin"  "$REL/voices-v1.0.bin"

# Fonts (Inter). Use system copy if present, else download.
if [ ! -f /usr/share/fonts/opentype/inter/InterDisplay-Black.otf ] && [ ! -f "$CACHE/fonts/InterDisplay-Black.otf" ]; then
  mkdir -p "$CACHE/fonts"
  curl -sL --retry 3 -o /tmp/inter.zip https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
  python3 - "$CACHE/fonts" <<'EOF'
import zipfile, sys, os
z = zipfile.ZipFile('/tmp/inter.zip')
for n in z.namelist():
    if n.startswith('extras/otf/') and n.endswith('.otf'):
        open(os.path.join(sys.argv[1], os.path.basename(n)), 'wb').write(z.read(n))
EOF
fi
if [ -f /usr/share/fonts/opentype/inter/InterDisplay-Black.otf ]; then
  echo "export IIN_FONTS=/usr/share/fonts/opentype/inter/"
else
  echo "export IIN_FONTS=$CACHE/fonts/"
fi
echo "setup ok"

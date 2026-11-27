#!/bin/bash
# India in Numbers: keep a synced copy of the channel repo on your Desktop (macOS).
# Run once in Terminal:  bash mac-setup.sh
# After that it syncs at log-in and every 30 minutes whenever you are online.
#
# The Desktop folder is a MIRROR of GitHub: anything you change inside it is overwritten on the next sync.
set -e
REPO=https://github.com/ketu98/claude-indiainnumbers.git
DEST="$HOME/Desktop/India in Numbers"
HOME2="$HOME/Library/Application Support/IndiaInNumbers"
SYNC="$HOME2/sync.sh"; LOG="$HOME2/sync.log"
PLIST="$HOME/Library/LaunchAgents/com.indiainnumbers.sync.plist"

if ! xcode-select -p >/dev/null 2>&1; then
  echo "Git needs Apple's command line tools. A window will open: click Install, wait, then run this script again."
  xcode-select --install; exit 1
fi
[ -d "$DEST/.git" ] || git clone "$REPO" "$DEST"

mkdir -p "$HOME2"
cat > "$SYNC" <<EOF
#!/bin/bash
cd "$DEST" || exit 0
T=\$(date '+%Y-%m-%d %H:%M')
if git fetch --quiet origin main 2>/dev/null; then
  git reset --hard --quiet origin/main
  echo "\$T synced \$(git log -1 --format='%h %s')" >> "$LOG"
else
  echo "\$T offline or GitHub unreachable, will retry" >> "$LOG"
fi
EOF
chmod +x "$SYNC"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.indiainnumbers.sync</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$SYNC</string></array>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>1800</integer>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
bash "$SYNC"
echo
echo "Done. Your copy is in: $DEST"
echo "Videos: videos/YYYY-MM/  ·  Tracker: TRACKER.md / TRACKER.csv"
echo "Syncs every 30 minutes while online. Log: $LOG"
echo "To stop: launchctl unload \"$PLIST\" && rm \"$PLIST\""

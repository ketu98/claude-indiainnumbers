# episode.json — format

One folder per episode: `episodes/epNN_<slug>/episode.json`. See ep01–ep03 for complete working examples.

```jsonc
{
  "ep": 4,                         // episode number (next after the highest in episodes/)
  "slug": "chai-vs-coffee",        // lowercase, hyphens
  "topic": "One-line question the episode answers",
  "hook": {
    "text": "Is Bangalore traffic really the worst in India?",   // the opening question (shown on screen, spoken by VEDA or the narrator)
    "lines": ["Is Bangalore", "traffic really", "the worst", "in India?"],  // optional manual line breaks (≤ 5 lines)
    "clip": "q25",                 // optional: SIGMA asks it with this voice-bank clip (text must match the clip exactly)
    "intro": "i01"                 // optional: SIGMA's opener before the question ("Sigma here. Question for the panel.")
  },
  "format": "myth",                // classic | myth | versus | then-now | ranking | guess | viewer | tracker (RUNBOOK step 3); "long" for long-form
  "welcome": true,                 // VEDA / REGINALD / TARA intros (keep true)
  "lines": [ LINE, LINE, ... ],    // 4–5 lines after the welcome
  "last_word": {"react": "r08", "close": "s03"},   // SIGMA's closing card "THE LAST WORD" (voice-bank clips; skipped if missing)
  "title": "YouTube title, ≤ 70 chars, 1 emoji max",
  "description": "2–3 sentences + a question for comments",
  "hashtags": ["#IndianRailways", "#VandeBharat", "#India"],   // 3–5, most important first; #Shorts + #IndiaInNumbers are added automatically
  "youtube": {                     // optional extras for YouTube (see RUNBOOK step 4)
    "tags": ["indian railways daily passengers", "india train facts"]   // 8–12 search phrases
    // "title": "...", "description": "..."  (optional: override title/description on YouTube only)
  },
  "sources": [{"name": "Publisher / dataset (date)", "url": "https://..."}]
}
```

`github` (written by publish_github.py) and `upload` (written by the YouTube uploader: video id, slot, go-live time, 48-hour views)
are filled in automatically. Never edit them by hand.

## Long-form (16:9) — see LONGFORM.md and episodes/_examples/longform.json
```jsonc
{
  "kind": "long", "format": "long",
  "hook": {"text": "How does Indian Railways keep the whole country moving?", "clip": "L04"},
  "sigma_intro": "x01",                       // SIGMA: "Grab a chai. This one's the long version."
  "chapters": [
    {"title": "Two crore people a day", "lines": [ LINE, ... ]},
    {"title": "The fastest trains", "bridge": "x03", "host": "TARA", "lines": [ ... ]}   // bridge = SIGMA clip before the chapter card; host = who announces it
  ],
  "lines": [ CTA LINE ],                       // after the chapters
  "last_word": {"react": "r04", "close": "x05"},
  "thumb_text": "2 CRORE people a day",        // big text on the thumbnail
  "title": "...", "description": "...", "hashtags": [...], "youtube": {"tags": [...]}, "sources": [...]
}
```
A SIGMA line can also go anywhere in `lines`: `{"spk": "SIGMA", "clips": ["r02"], "visual": {"type": "sigma", "kicker": "WAIT FOR IT"}}`
(no `say`; the caption is the clip text). Visual types `sigma` and `chapter` are used by SIGMA lines and chapter cards.

## LINE
```jsonc
{
  "spk": "VEDA" | "REGINALD" | "TARA" | "SIGMA",   // SIGMA uses "clips" instead of "say"
  "say": "What the voice speaks. Spell out years and tricky numbers: 'twenty twenty-five', 'seven hundred and forty one crore'.",
  "cap": "On-screen caption, same meaning, with digits: '741 CRORE passengers'. CAPS for 1–2 punch words.",
  "visual": VISUAL
}
```
Keyword timing: fields called `at` are a word from `cap` (e.g. "WORLD", "3.5x", "FULL"). The pop/ding happens when that word is spoken. If missing, a sensible default time is used.

## VISUAL types

**bars** — ranking / trend, 2–6 rows
```json
{"type": "bars", "title": "Traffic congestion · 2025", "subtitle": "Source: TomTom Traffic Index",
 "items": [["Bengaluru", 74.4], ["Pune", 71.1]], "unit": "%", "decimals": 1, "highlight": 0,
 "badges": [{"text": "#1 in India", "at": "India,"}, {"text": "#2 in the World", "at": "WORLD"}]}
```
`highlight` = row index (or list). `badges` ≤ 2. Optional `prefix` ("₹"), `indian`: true for Indian digit grouping, `max`.

**bigstat** — one huge counting number
```json
{"type": "bigstat", "value": 168, "label": "hours a year, stuck in rush hour", "count_at": "168",
 "then": {"text": "= 7 full days", "at": "FULL"},
 "tiles": {"n": 7, "label": "DAY", "icon": "note", "at": "FULL"}}
```
Optional `prefix`, `suffix` (" crore"), `decimals`, `indian`, `title`. `tiles` (≤ 8, icon "note" or a short text like "₹") is optional.

**vs** — two values side by side (A vs B, then vs now)
```json
{"type": "vs", "title": "UPI payments in October", "subtitle": "billions per month",
 "a": ["Oct 2022", 7.3], "b": ["Oct 2026", 25.47], "unit": " bn", "decimals": 1, "highlight": "b",
 "pill": {"text": "3.5x in 4 years", "at": "3.5x"}}
```

**gauge** — ring that fills while a number counts up
```json
{"type": "gauge", "title": "10 km drive", "value": 36.15, "max": 60, "format": "mm:ss", "unit_label": "minutes",
 "sub": {"text": "Evening rush: 45 min 27 sec", "at": "episode"}}
```
`format`: "mm:ss" or omit for a normal number (then `unit`/`decimals`/`prefix` apply).

**fact** — big headline figure + up to 3 supporting lines
```json
{"type": "fact", "kicker": "Average UPI value, every day (Oct 2026)", "big": "₹1,01,707 cr",
 "lines": [{"text": "First time above ₹1 lakh crore a day", "at": "DAY."}]}
```

**cta** — closing question (always the last line)
```json
{"type": "cta", "title": "Your city?", "chips": ["Pune", "Mumbai", "Delhi"], "button": "COMMENT"}
```

Any visual can add `"boing": true` on a REGINALD line for a comedy sound.

## Render
```
python3 engine/make_episode.py episodes/epNN_slug --preview 2,12,18,25,31,37   # contact sheet → work/preview.jpg
python3 engine/make_episode.py episodes/epNN_slug                               # full render → out/
```
Put a narrator recording in the folder as `hook.mp3|m4a|wav|ogg` to use it instead of VEDA's voice (it is denoised and enhanced automatically). `IIN_HOOK=veda` forces VEDA.

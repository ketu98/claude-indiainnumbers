# RUNBOOK — make one India in Numbers Short

You are making ONE new episode of **India in Numbers** (YouTube @IndiaInNumbersPanel), a channel of 40–50 second
vertical Shorts where three animated characters answer a question about India with real, sourced data.
Once you publish an episode to GitHub (step 8), the YouTube uploader workflow posts it automatically: it checks it, uploads it as private
and schedules it for the best posting slot. **You (Claude) never upload or post anything yourself.** Your title, description and hashtags are what goes on YouTube, so make them good (step 4).

## The cast (keep them in character)
- **VEDA** (cyan, calm American female): precise, warm, the "here's what the data says" voice. Often asks the hook question.
- **REGINALD** (gold, posh British butler): dry wit, verdicts and roasts. "I'm afraid", "old chap", "splendid". Never mean about people or places.
- **TARA** (pink, bright American female): excited reactions, relatable comparisons (web series, chai, traffic), usually the closing question.
Rotate who leads. No one gets more than 2 lines after the welcome. Vary who gives the big verdict from episode to episode.
Never call them AIs on screen or in the script, and never claim they are real people.

## Steps

1. **Setup**: clone without the big `videos/` folder (it is only for Aniket's computer):
   `git clone --depth 1 --filter=blob:none --sparse https://github.com/ketu98/claude-indiainnumbers ~/claude-indiainnumbers && cd ~/claude-indiainnumbers && git sparse-checkout set --no-cone '/*' '!/videos/'`
   Then set a git identity (`git config user.name "India in Numbers bot"`, `git config user.email "aniket+claude@users.noreply.github.com"`),
   run `bash setup.sh`, and run the `export IIN_FONTS=...` line it prints.

2. **Pick the topic**
   - Read `topics/requests.md` first: if Aniket left a request there, do the top one and delete it from the list.
   - Otherwise pick from `topics/backlog.md`, or a fresh timely angle (new official data released this week, e.g. NPCI monthly UPI numbers in the first days of a month).
   - Read `episodes/LOG.md`: never repeat a topic, and don't use the same category as either of the last 2 episodes.
   - **Off-limits**: religion, caste, communities, politics, elections, parties or politicians, crime by group, health or medical advice,
     personal finance or investment advice, disasters or death tolls, anything that ranks people or states as "worse" in a demeaning way.
     Factual brand and company mentions are fine.

3. **Research** (WebSearch / WebFetch)
   - Need **at least 3 solid numbers**, each from a named, linkable source: official first (PIB, ministries, NPCI, RBI, IMD, MoSPI, data.gov.in,
     World Bank, UN), else reputable media quoting them. Use the latest available figures and say the year on screen.
   - Cross-check key numbers with a second source where possible. If sources disagree, use the official one or drop the number.
   - Compute derived numbers (per day, per second, % change, ratios) **in Python** and present them as "about …".
   - Never invent or round misleadingly. If you can't find 3 solid numbers, pick another topic.
   - Avoid crowdsourced sites (Numbeo etc.) unless labelled as estimates.

4. **Write `episodes/epNN_<slug>/episode.json`** following `SCHEMA.md` (copy ep02 or ep03 as a template).
   - NN = highest existing episode number + 1.
   - Hook: a curiosity question of 10 words or fewer.
   - Then 4–5 lines, the last one a `cta`. Each `say` about 25 words max, each `cap` about 20 words max. Target 40–50 s total.
   - Use a different visual type on consecutive lines. Give every number a visual.
   - Spell out years and big numbers in `say` ("twenty twenty-six", "seven hundred and forty one crore"); use digits in `cap`.
   - Title: ≤ 70 chars, punchy, at most 1 emoji, with the main search words (e.g. "UPI", "Indian Railways", "Bangalore traffic") in the first 40 chars.
     Description: 2–3 sentences with the key numbers, ending with a question for comments. Fill `sources` with every source used.
   - **YouTube discoverability** (this goes straight to YouTube, so it must be accurate and on-topic):
     - `hashtags`: 3–5, most important first. The first 3 show above the title on YouTube: 2 specific topic tags people actually search
       (`#IndianRailways`, `#UPI`, `#Bengaluru`), then a broad one (`#India`, `#IndiaFacts`). `#Shorts` and `#IndiaInNumbers` are added
       automatically. Use a WebSearch to see which hashtags are in use for the topic this week, and pick only ones directly about the
       episode: unrelated "viral" tags break YouTube's misleading-metadata rules and can get a video removed.
     - `youtube.tags`: 8–12 search phrases a viewer would type ("indian railways daily passengers", "how many people travel by train in india").
     - Optional `youtube.title` / `youtube.description` override the plain ones for YouTube only. Usually leave them out.

5. **Preview and check**: `python3 engine/make_episode.py episodes/<folder> --preview <times>`, using times about 2 s into each line
   (the command prints line start times). Open `work/preview.jpg` and check that text fits, nothing overlaps, and the numbers are right.
   Fix the JSON and re-preview until it's clean.

6. **Render**: `python3 engine/make_episode.py episodes/<folder>` (VEDA asks the hook, since no recording exists yet).

7. **Deliver to Aniket** (he may be away, so use status "proactive"):
   Output files are named with the IST date and time they were made, e.g. `2026-11-28_08-52_ep04_chai-vs-coffee_veda.mp4`
   and `2026-11-28_08-52_ep04_chai-vs-coffee_upload.txt`. Keep those names.
   - SendUserFile: the mp4 from `out/`, caption "Ep NN · <date, time IST> · <title>".
   - SendUserFile: the `*_upload.txt` from `out/` (title, description, sources, hashtags, hook line).
   - SendUserMessage, short: the topic, the 3 key numbers with their sources, "It will be posted to YouTube automatically
     (the Issue will say when; label it `skipped` to stop it)", and
     "Want your voice on the opening question? Record: '<hook text>' and send it here, and I'll redo the video."

8. **Publish to GitHub for review** (this also commits and pushes everything):
   - Copy the `*_upload.txt` from `out/` next to `episode.json` as `upload.txt`, and append a line to `episodes/LOG.md`:
     `| NN | YYYY-MM-DD | <category> | <topic> | <title> |`.
   - `git add episodes topics && git commit -m "Ep NN: <topic> (script)"` (skip if nothing changed).
   - `python3 engine/publish_github.py episodes/<folder> --slot <Morning|Afternoon>`
     It copies the video and upload text into `videos/YYYY-MM/` (date-time names), opens the episode's review Issue labelled
     `episode` + `ready-to-review` with a checklist, regenerates `TRACKER.md` / `TRACKER.csv` (status comes from Issue labels),
     then commits and pushes to main. Put the Issue link it prints in your message to Aniket.
   - If it fails, fix the cause and re-run it: it is safe to repeat (one Issue per episode).

9. **YouTube**: nothing to do. After your push, the uploader workflow picks the episode up within minutes, comments on its Issue with
   the YouTube link and go-live time, and keeps `TRACKER.md` up to date (status, live time, 48-hour views).

10. **If Aniket replies with a recording**: save it as `episodes/<folder>/hook.<ext>` (never commit it), re-render (step 6 picks it up
   automatically and cleans the audio), send the new mp4, then re-run step 8's `publish_github.py`: it updates the same Issue
   and adds the `narrator-voice` label. If the old version is scheduled but not live yet, the uploader keeps it private and posts
   the new one instead. If it's already live, it is left as it is.

# RUNBOOK — make one India in Numbers Short

You are making ONE new episode of **India in Numbers** (YouTube @IndiaInNumbersPanel), a channel of 40–50 second
vertical Shorts where three animated characters answer a question about India with real, sourced data.
The owner, Aniket, reviews and uploads every video himself. **Never upload anywhere. Never post anything.**

## The cast (keep them in character)
- **VEDA** (cyan, calm American female): precise, warm, the "here's what the data says" voice. Often asks the hook question.
- **REGINALD** (gold, posh British butler): dry wit, verdicts and roasts. "I'm afraid", "old chap", "splendid". Never mean about people or places.
- **TARA** (pink, bright American female): excited reactions, relatable comparisons (web series, chai, traffic), usually the closing question.
Rotate who leads. No one gets more than 2 lines after the welcome. Vary who gives the big verdict from episode to episode.
Never call them AIs on screen or in the script, and never claim they are real people.

## Steps

1. **Setup**: `bash setup.sh`, then run the `export IIN_FONTS=...` line it prints.

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
   - Title: ≤ 70 chars, punchy, at most 1 emoji. Description: 2–3 sentences ending with a question. Fill `sources` with every source used.

5. **Preview and check**: `python3 engine/make_episode.py episodes/<folder> --preview <times>`, using times about 2 s into each line
   (the command prints line start times). Open `work/preview.jpg` and check that text fits, nothing overlaps, and the numbers are right.
   Fix the JSON and re-preview until it's clean.

6. **Render**: `python3 engine/make_episode.py episodes/<folder>` (VEDA asks the hook, since no recording exists yet).

7. **Deliver to Aniket** (he may be away, so use status "proactive"):
   Output files are named with the IST date and time they were made, e.g. `2026-11-28_08-52_ep04_chai-vs-coffee_veda.mp4`
   and `2026-11-28_08-52_ep04_chai-vs-coffee_upload.txt`. Keep those names.
   - SendUserFile: the mp4 from `out/`, caption "Ep NN · <date, time IST> · <title>".
   - SendUserFile: the `*_upload.txt` from `out/` (title, description, sources, hashtags, hook line).
   - SendUserMessage, short: the topic, the 3 key numbers with their sources, and
     "Want your voice on the opening question? Record: '<hook text>' and send it here, and I'll redo the video."

8. **Log it in the Episode Tracker sheet** (Claude Docs connector; Sheet id `e594af4b-4f59-41d0-aa7c-3755099280bd`,
   link https://claude.ai/artifact/VMH7G519GZtzyErD87GPqn).
   - First call the connector's `guide` with `items: ["topic.sheets"]` and follow it. Find the workbook node with
     `read(ref={"object":"project","id":"e594af4b-4f59-41d0-aa7c-3755099280bd"})`, then `readSheets` and `readCells` on sheet `Episodes`
     to find the first empty row of the table (columns A:K, header in row 1).
   - Write ONE new row there (never overwrite a filled row) with these columns:
     `Ep` (number) · `Made on (IST)` ("YYYY-MM-DD HH:MM") · `Slot` ("Morning" or "Afternoon") · `Topic` · `Status` = "Ready to review" ·
     `Title` · `Voice` ("VEDA" or "Narrator") · `Video file` (the mp4 file name) · `Sources` (publisher names, "; "-separated) ·
     `YouTube link` (leave empty) · `Notes` (anything Aniket should check, or empty).
   - If a re-render with Aniket's voice happens later (step 10), update that row's `Voice` and `Video file` only.
   - If the connector is unavailable, skip this step and mention it in your message to Aniket.

9. **Save to GitHub**
   - Copy the `*_upload.txt` from `out/` next to `episode.json` as `upload.txt`. Append a line to `episodes/LOG.md`: `| NN | YYYY-MM-DD | <category> | <topic> | <title> |`.
   - `git add episodes topics && git commit -m "Ep NN: <topic>"`, then `git -c push.negotiate=true push origin HEAD:main`.
   - If the push is rejected because the remote moved on, run `git pull --rebase origin main` and push again.
   - Never commit audio or video (`.gitignore` handles it).

10. **If Aniket replies with a recording**: save it as `episodes/<folder>/hook.<ext>`, re-render (step 6 picks it up
   automatically and cleans the audio), and send the new mp4.

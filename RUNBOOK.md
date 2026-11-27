# RUNBOOK — make one India in Numbers Short

You are making ONE new episode of **India in Numbers** (YouTube @IndiaInNumbersPanel): a 40–55 second vertical Short where three
animated hosts answer one question about India with real, sourced data, opened and closed by **SIGMA (Σ)**, the channel's anonymous narrator.
One Short is made per day. For the weekly long-form video, follow **LONGFORM.md** instead.
After you publish to GitHub (step 9), the YouTube uploader workflow posts the episode automatically: it checks it, uploads it as private and
schedules it for the best slot. **You (Claude) never upload or post anything yourself.** Your title, description and hashtags go straight to YouTube.

## The cast (keep them in character)
- **SIGMA (Σ)**: the narrator. A recorded human voice (pre-recorded clips from the private voice bank), never TTS. SIGMA asks the hook and has
  **The Last Word**. SIGMA is a mystery handle: never name, describe, hint at or speculate about the person behind it, anywhere (scripts,
  captions, titles, descriptions, Issues, messages). Never write the owner's name in this repo.
- **VEDA** (cyan, calm American female): precise, warm, the "here's what the data says" voice.
- **REGINALD** (gold, posh British butler): dry wit, verdicts and roasts. "I'm afraid", "old chap", "splendid". Never mean about people or places.
- **TARA** (pink, bright American female): excited reactions, relatable comparisons (web series, chai, traffic), usually the closing question.
Rotate who leads. No host gets more than 2 lines after the welcome. Vary who gives the big verdict. Never call the hosts AIs, never claim they are real people.

## Why variety matters (read once)
YouTube refuses to pay channels whose videos look template-made with little variation. Every episode must feel different: a new subject, a rotating
**format** (step 3), a different lead host, varied visuals, and a real insight (a comparison, a surprise, a "so what") rather than a list of numbers.

## Steps

1. **Setup**
   - Clone without the big `videos/` folder:
     `git clone --depth 1 --filter=blob:none --sparse https://github.com/ketu98/claude-indiainnumbers ~/claude-indiainnumbers && cd ~/claude-indiainnumbers && git sparse-checkout set --no-cone '/*' '!/videos/'`
   - `git config user.name "India in Numbers bot"` and `git config user.email "iin-bot@users.noreply.github.com"`.
   - `bash setup.sh`, then run the `export IIN_FONTS=...` line it prints.
   - **Voice bank** (private): attach `ketu98/iin-voice-bank` with the add_repo tool (access "push") and clone it to `~/iin-voice-bank`
     (`git clone --depth 1 https://github.com/ketu98/iin-voice-bank ~/iin-voice-bank`), then `export IIN_VOICE_BANK=~/iin-voice-bank`.
     - If `~/iin-voice-bank/inbox/` has new recordings: `python3 engine/voice_bank.py inbox`. It matches each file to its script by name
       (`Script_01.m4a` …), cuts it into clips and renames the finished script in `sigma-scripts/` to `Completed_…`. For every `PROBLEM:`
       line, tell the owner exactly which recording and what to redo. Then commit and push both repos:
       `cd ~/iin-voice-bank && git add -A && git commit -m "Process recordings" && git push`, and in this repo
       `git add -A sigma-scripts && git commit -m "SIGMA: recordings processed" && git push`.
     - `python3 engine/voice_bank.py status` shows which clips exist. New recording batches: add a section `Script_NN` (new ids) to
       `channel/sigma_script.json` and run `python3 engine/voice_bank.py scripts` to write its file into `sigma-scripts/`.
     - If the bank repo can't be attached or is empty, carry on without SIGMA (VEDA asks the hook, no Last Word) and mention it in your message.
     - Clips are private: never copy them into this repo, never send them anywhere.

2. **Pick the topic** (go wide: space, nature, sports, food, energy, money facts, culture, cities, transport, digital, tourism, education, geography, records…)
   - **Owner's ideas first**: open Issues labelled `idea` (`gh api "repos/ketu98/claude-indiainnumbers/issues?labels=idea&state=open"`).
     Skip ones marked "Long-form" (those are for LONGFORM.md) and ones whose "Make it on" date is in the future; if one is dated today, do that one,
     else the oldest. Follow its question, format and angle: the owner's angle and lines are the heart of the episode (keep the facts sourced;
     if a number they gave can't be verified, use the verified figure and say so in your message). Then comment on the idea Issue with the
     episode Issue link and close it.
   - Then `topics/requests.md`: if the owner left a request, do the top one and delete it from the list.
   - Otherwise **prefer a recorded SIGMA question** (`channel/sigma_script.json` Script_01 / Script_02, kind `question`) that has a clip in the bank and
     isn't in the `Q` column of `episodes/LOG.md`. The question is the hook, word for word.
   - Else pick from `topics/backlog.md`, or a timely angle (fresh official data this week).
   - Never repeat a topic in `episodes/LOG.md`, and don't use the same category as either of the last 2 episodes.
   - **Off-limits**: religion, caste, communities, politics, elections, parties or politicians, crime by group, health or medical advice,
     personal finance or investment advice, disasters or death tolls, anything that ranks people or states as "worse" in a demeaning way.
     Factual brand and company mentions are fine.

3. **Pick the format**: not the same as either of the last 2 episodes (`Format` column in `episodes/LOG.md`). Set `"format"` in episode.json.
   | format | header label | shape |
   |---|---|---|
   | `classic` | THE PANEL | question → 3 numbers → verdict |
   | `myth` | MYTH OR FACT? | a popular belief as the question; the data reveals MYTH or FACT (big `fact` card) |
   | `versus` | INDIA VS THE WORLD | India against other countries (`bars` or `vs`) |
   | `then-now` | THEN VS NOW | 10–25 years ago vs today (`vs`), and what changed |
   | `ranking` | THE RANKING | a top-5 of cities/states/things, never a "worst" ranking of people |
   | `guess` | GUESS THE NUMBER | a host invites a guess ("Comment your guess before the reveal"), then the reveal |
   | `viewer` | YOU ASKED | answers a viewer question from `topics/requests.md` (say "a viewer asked", never their name) |
   | `tracker` | THE TRACKER | this month's official figure vs last month/last year (UPI, car sales, flights…) |

4. **Research** (WebSearch / WebFetch)
   - Need **at least 3 solid numbers**, each from a named, linkable source: official first (PIB, ministries, NPCI, RBI, IMD, MoSPI, ISRO,
     data.gov.in, World Bank, UN), else reputable media quoting them. Use the latest figures and say the year on screen.
   - Cross-check key numbers with a second source where possible. If sources disagree, use the official one or drop the number.
   - Compute derived numbers (per day, per second, % change, ratios) **in Python** and present them as "about …".
   - Never invent or round misleadingly. If you can't find 3 solid numbers, pick another topic.
   - Find one genuine insight: a surprising comparison or a "so what does that mean for daily life".

5. **Write `episodes/epNN_<slug>/episode.json`** following `SCHEMA.md` (copy the newest episode as a template).
   - NN = highest existing episode number + 1 (pull main first).
   - **Hook**: with a SIGMA question: `"hook": {"text": "<the clip's exact text>", "clip": "qNN", "intro": "i01"}` (alternate `i01`/`i02`,
     or leave `intro` out sometimes). Without one: a curiosity question of 10 words or fewer.
   - Then 4–5 host lines, the last one a `cta`. Each `say` about 25 words max, each `cap` about 20 words max.
   - **The Last Word**: `"last_word": {"react": "rNN", "close": "sNN"}`. Pick the reaction whose tone fits the result
     (`wow` surprising · `ouch` a bad number · `proud` India does well · `fun` teases a host who was right/wrong in this script · `calm` neutral);
     the fun ones must match what happened (e.g. `r12` "Tara called it" only if Tara predicted it). Don't reuse a react or close used in
     the last 3 episodes (see LOG). Total length target: 40–55 s.
   - Use a different visual type on consecutive lines. Give every number a visual.
   - Spell out years and big numbers in `say` ("twenty twenty-six", "seven hundred and forty one crore"); use digits in `cap`.
   - Title: ≤ 70 chars, punchy, at most 1 emoji, with the main search words (e.g. "UPI", "Indian Railways", "tigers") in the first 40 chars.
     Description: 2–3 sentences with the key numbers, ending with a question for comments. Fill `sources` with every source used.
   - **YouTube discoverability** (goes straight to YouTube, so it must be accurate and on-topic):
     - `hashtags`: 3–5, most important first. The first 3 show above the title: 2 specific topic tags people actually search
       (`#IndianRailways`, `#ISRO`, `#Bengaluru`), then a broad one (`#India`, `#IndiaFacts`). `#Shorts` and `#IndiaInNumbers` are added
       automatically. WebSearch which hashtags are in use for the topic this week; pick only ones directly about the episode.
     - `youtube.tags`: 8–12 search phrases a viewer would type.

6. **Preview and check**: `python3 engine/make_episode.py episodes/<folder> --preview <times>`, using times about 2 s into each line
   (it prints line start times) plus one in the hook and one in the Last Word. Open `work/preview.jpg`: text fits, nothing overlaps,
   numbers are right, the header shows the format. If it printed "note: ... not in the voice bank", fix the clip id or drop it.

7. **Render**: `python3 engine/make_episode.py episodes/<folder>`. The file ends in `_sigma.mp4` when SIGMA's voice was used.

8. **Deliver to the owner** (status "proactive"; the owner may be away):
   - SendUserFile: the mp4 from `out/`, caption "Ep NN · <date, time IST> · <format> · <title>".
   - SendUserMessage, short: the topic, the 3 key numbers with sources, which SIGMA clips were used (or why none),
     and "It will be posted to YouTube automatically (the Issue will say when; label it `skipped` to stop it)."

9. **Publish to GitHub** (commits and pushes everything):
   - Copy the `*_upload.txt` from `out/` next to `episode.json` as `upload.txt`, and append to `episodes/LOG.md`:
     `| NN | YYYY-MM-DD | <category> | <format> | short | <hook clip or -> | <react>+<close or -> | <topic> | <title> |`.
   - `git add episodes topics && git commit -m "Ep NN: <topic> (script)"` (skip if nothing changed).
   - `python3 engine/publish_github.py episodes/<folder> --slot Daily`
     It copies the video into `videos/YYYY-MM/`, opens the episode's Issue, rebuilds `TRACKER.md` / `TRACKER.csv`, commits and pushes.
     Put the Issue link it prints in your message. Safe to re-run if it fails.

10. **YouTube**: nothing to do. The uploader workflow picks it up after your push and comments on the Issue with the link and go-live time.

11. **If the owner sends a one-off recording** for an episode: save it as `episodes/<folder>/hook.<ext>` (never commit it), re-render
   (it is cleaned and disguised automatically), send the new mp4, then re-run `publish_github.py`. If the old version isn't live yet,
   the uploader keeps it private and posts the new one.

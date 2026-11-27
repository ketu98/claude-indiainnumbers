# WEEKLY_SCRIPT — write SIGMA's script for next week (runs Friday evening)

The owner records one short script a week (about a minute). Plan next week (Sunday to Saturday) and write it.

1. **Setup**: as RUNBOOK step 1 (main repo; the voice bank is needed only for `status`).
2. **Plan 8 questions** for next Sunday to Saturday: 7 daily Short questions (one per day) and 1 long-form question for Saturday.
   - Spread subjects widely (nature, space, sports, food, energy, money facts, culture, cities, transport, digital, tourism, education,
     geography, weather, business…): no category twice in a row, nothing already in `episodes/LOG.md` or already planned in
     `channel/sigma_script.json`, and respect the RUNBOOK off-limits list. Use `topics/backlog.md`, timely angles for that week
     (an official data release, an anniversary, a big event), and open `idea` Issues that have no date (the owner's pitches: include them).
   - **Check each one is answerable**: a quick WebSearch must show at least 3 solid, official or reputable numbers exist. Replace any that don't.
   - Each Short question ≤ 10 words, spoken naturally, curiosity-first ("How many…", "Is it true that…", "Which…"). The long-form
     question can be broader (≤ 14 words).
3. **Fresh lines (optional, max 4)**: if the bank has fewer than 8 reactions or 4 sign-offs, or the same ones keep repeating in the LOG,
   add 2–4 new short reactions / sign-offs in SIGMA's voice (dry, calm, a little mysterious; ≤ 10 words; never reveal who SIGMA is).
4. **Write it** into `channel/sigma_script.json` as a new section `Script_NN` (next number) titled `Week N (<Sun date> - <Sat date>)`.
   Lines in order: Short questions by date, then the long-form question, then any fresh lines. New ids continue from the highest used
   (`q`, `L`, `r`, `s`, `x`), never reuse one. Each question line carries its date (YYYY-MM-DD).
   Then `python3 engine/voice_bank.py scripts`, and commit + push: `git add channel/sigma_script.json sigma-scripts && git commit -m "SIGMA script for week N" && git push`.
5. **Send it to the owner** (SendUserMessage, status proactive): "Next week's SIGMA script (about a minute):", the numbered lines
   exactly as in the file (just the sentences, each on its own line), then: "Record in one go, pausing ~2 s between lines, save as
   Script_NN and send it in a Claude chat or upload it to iin-voice-bank/inbox." Mention any older script that isn't Completed yet.

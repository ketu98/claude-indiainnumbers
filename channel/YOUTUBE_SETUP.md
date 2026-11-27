# YouTube uploader: one-time setup (about 15 minutes)

Once this is done, every episode is posted to YouTube automatically by the GitHub workflow
`.github/workflows/youtube.yml` (script: `engine/youtube_upload.py`, settings: `channel/youtube.json`).
Until it's done, the workflow just says "secrets not set yet" and does nothing.

You need: the Google account that owns the India in Numbers channel, and the GitHub account `ketu98`.

## 1. Google Cloud project (free)
1. Open https://console.cloud.google.com → project picker (top left) → **New project** → name it `India in Numbers uploader` → Create, then select it.
2. Search bar → **YouTube Data API v3** → **Enable**.

## 2. Consent screen: set it to "In production"
1. Search bar → **Google Auth Platform** (or "OAuth consent screen") → **Get started**.
   App name `India in Numbers uploader`, your email as support email, audience **External**, your email as contact → Create.
2. **Audience** → **Publish app** → confirm. The status must say **In production**.
   ⚠️ If it stays in "Testing", Google expires the sign-in after 7 days and uploads stop.
   You do **not** need Google's app verification: it's only you signing in. You'll see a "Google hasn't verified this app" screen once.
3. **Data access** → **Add or remove scopes** → paste both lines below into "Manually add scopes" → Add → Update → Save:
   ```
   https://www.googleapis.com/auth/youtube.upload
   https://www.googleapis.com/auth/youtube
   ```

## 3. OAuth client
1. **Clients** → **Create client** → type **Web application**, name `uploader`.
2. Under **Authorized redirect URIs** add: `https://developers.google.com/oauthplayground` → Create.
3. Copy the **Client ID** and **Client secret** (keep the tab open).

## 4. Get the refresh token (Google's OAuth Playground, nothing to install)
1. Open https://developers.google.com/oauthplayground
2. Gear icon (top right) → tick **Use your own OAuth credentials** → paste the Client ID and Client secret → Close.
3. In the left box "Input your own scopes" paste:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube` → **Authorize APIs**.
4. Sign in with the channel's Google account. On "Google hasn't verified this app": **Advanced** → **Go to India in Numbers uploader**.
   **If it asks you to pick a channel, pick India in Numbers** (not your personal channel). Allow.
5. Click **Exchange authorization code for tokens** → copy the **Refresh token**.

## 5. Put the 3 values in GitHub
https://github.com/ketu98/claude-indiainnumbers/settings/secrets/actions → **New repository secret**, three times:

| Name | Value |
|---|---|
| `YT_CLIENT_ID` | the Client ID |
| `YT_CLIENT_SECRET` | the Client secret |
| `YT_REFRESH_TOKEN` | the refresh token |

## 6. Test, then go live
1. https://github.com/ketu98/claude-indiainnumbers/actions → **YouTube uploader** → **Run workflow** → tick **Dry run** → Run.
   Open the run's log: it shows the title, tags and description it would post for each episode, and changes nothing.
2. Run it again **without** Dry run. Eps 01–03 go public straight away (they're listed in `publish_now_eps`). Their Issues get a
   comment with the YouTube link and the `uploaded` label, and TRACKER.md updates.
3. Check one of them in YouTube Studio: it should be **Public**, made for kids = **No**, and "Altered content" = **Yes**.

From then on it's hands-off: each new episode is uploaded as private and goes public in a posting slot at least 3 hours later.
To stop one, label its Issue `skipped` before then.

## When something goes wrong
- **Issue labelled `upload-failed` saying "YouTube kept it private"**: Google is restricting uploads from this unaudited API project.
  Make the video public in Studio by hand, and apply (free) at https://support.google.com/youtube/contact/yt_api_form.
- **`invalid_grant` in the workflow log**: the sign-in expired or was revoked (usually because the consent screen was still in
  "Testing"). Check step 2.2, redo step 4, and update `YT_REFRESH_TOKEN`.
- **Pause everything**: set `"enabled": false` in `channel/youtube.json`.

## Posting times
`channel/youtube.json` → `candidate_slots` (IST). The uploader spreads new videos across these slots, records each video's
views after 48 hours, and once every slot has 3 results it mostly posts in the best-performing slots, still trying the others
about 20% of the time. You can check this against YouTube Studio → Analytics → Audience → "When your viewers are on YouTube".
To force fixed times, put them in `fixed_slots`, e.g. `["12:30", "19:30"]`.

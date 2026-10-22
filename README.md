# Daily Anime YouTube Agent

Creates one anime video per day: story script → anime images → voices → music/SFX → FFmpeg edit → title/description/hashtags → YouTube upload → Gmail notification.

Pipeline stages (`agent/`): script, scenes, images, voice, music, edit, metadata, upload, notify. Each stage checkpoints to `work/<date>/state.json`, so a failed run resumes where it stopped.

## Setup
1. `sudo apt install ffmpeg` (with libass for subtitles) and `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` (or set the variables as CI secrets). Never commit secrets.
3. Edit `config.yaml` (style, scenes, privacy, budget) and `data/story_bible.md` (your world and characters).
4. Optionally add royalty-free tracks to `assets/music/` (e.g. `epic_01.mp3`, matched by mood: calm, epic, sad, tense, happy, mysterious) and SFX to `assets/sfx/` (e.g. `wind.mp3`). Make sure licences allow monetisation.

## Google OAuth (YouTube + Gmail)
1. In Google Cloud, create a project and enable **YouTube Data API v3** and **Gmail API**.
2. Configure the OAuth consent screen, then create an OAuth client of type **Desktop** and download it as `client_secret.json`.
3. Run `python -m agent.auth` locally, log in, and store the printed `GOOGLE_REFRESH_TOKEN` plus `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` as secrets.
4. Note: unaudited API projects have uploads locked to private. An upload costs about 1,600 of the 10,000 daily quota units.
5. Gmail uses the `gmail.send` scope, or set `notify.method: smtp` with an app password.

## Usage
```
python -m agent.run_daily --dry-run     # build the video, no upload/email
python -m agent.run_daily               # full run
python -m agent.run_daily --approve --day 2026-01-01   # publish an approved draft
python -m agent.run_daily --stage edit --force         # re-run one stage
```
Set `provider: mock` in `config.yaml` to test the whole pipeline offline without API calls.
With `upload.require_approval: true` the agent emails you the draft and waits for `--approve`.

Safety and cost: scripts go through schema validation and a keyword safety check, descriptions include an AI-content disclosure, uploads are flagged as synthetic media, and `budget.max_usd_per_video` aborts a run when the estimated cost is exceeded.

## Scheduling
`.github/workflows/daily.yml` runs daily via cron (manual runs default to dry-run). Add the secrets from `.env.example` to the repository. Note GitHub-hosted runners don't keep `work/`; the video is attached as an artifact.

## Tests
`python -m pytest tests`

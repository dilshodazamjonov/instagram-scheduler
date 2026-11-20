# Instagram autopost

Posts one Reel a day from `queue/` to Instagram, using GitHub Actions and
Instagram's official API. Free, and runs with your laptop off.

- `queue/NNN-name/video.mp4` + `caption.txt`: posted in number order, one per day
  at 19:00 Tashkent time (change the `cron` line in `.github/workflows/post-daily.yml`).
- `posted.json`: what was posted, with links. After posting, the video file is
  removed from the queue to keep the repo small.
- `add_to_queue.sh`: adds a video and pushes it.
- The Meta token for this app type (Unified login) does not expire.
  If Meta ever revokes it, generate a new one and replace the `IG_ACCESS_TOKEN` secret.

## One-time setup (done by hand, in this order)

Replace `USERNAME` with your GitHub username in the links below.

1. **Create the repository**: https://github.com/new
   Name `insta-queue`, **Public**, no README / .gitignore / license.
   (Public is what makes GitHub Pages and unlimited Actions minutes free.
   Your videos are going public on Instagram anyway.)

2. **Create a GitHub token** (only for pushing from the laptop):
   https://github.com/settings/personal-access-tokens/new
   - Repository access: *Only select repositories* → `insta-queue`
   - Permissions → Repository: **Contents: Read and write**

3. **Push this folder**: run the two commands Claude gives you. When git asks,
   the username is your GitHub username and the password is the token from step 2.

4. **Turn on GitHub Pages**: https://github.com/USERNAME/insta-queue/settings/pages
   Source: *Deploy from a branch* → Branch `main`, folder `/ (root)` → Save.

5. **Get the Meta token**: https://developers.facebook.com/apps/ → your app →
   Use cases → Instagram API → **API setup with Unified login** → section
   *2. Generate access tokens* → **Generate token** next to your Instagram account.
   (The account must be an Instagram Tester under App roles, and must be in your
   business portfolio under Instagram profiles.)

6. **Add the secret**: https://github.com/USERNAME/insta-queue/settings/secrets/actions
   - `IG_ACCESS_TOKEN` = the Meta token from step 5
   The Instagram account ID is set in `.github/workflows/post-daily.yml` (`IG_USER_ID`).

7. **Test it**: https://github.com/USERNAME/insta-queue/actions →
   *Post next Reel* → **Run workflow**. In a few minutes the first Reel is live,
   and its link appears in the log and in `posted.json`.

From then on it posts daily by itself. If something fails, GitHub emails you.

# HuddleHub Deployment Checklist

## Publishing an Update

This site is **not** linked to git. Pushing to GitHub does **not** deploy.
Every content change must be deployed manually.

1. Put the edited HTML at `public/index.html`, next to the existing `public/assets/`.
   Never edit or upload a lone `index.html` — every image is a relative
   `assets/images/...` path, so an HTML file on its own shows all images broken.
2. Preview locally with images intact: `npm run preview` → http://localhost:5173
3. Deploy the **whole `public` folder** (HTML + assets together):

   ```sh
   cd public
   zip -r -X /tmp/hh_deploy.zip index.html assets robots.txt sitemap.xml
   TOKEN=$(python3 -c "import json;d=json.load(open('$HOME/Library/Preferences/netlify/config.json'));print(next(iter(d['users'].values()))['auth']['token'])")
   curl -X POST "https://api.netlify.com/api/v1/sites/09b74ab5-0c7f-450d-bd96-25f3cb0b6d19/deploys" \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/zip" \
     --data-binary @/tmp/hh_deploy.zip
   ```

   Poll `GET /api/v1/deploys/<deploy_id>` until `state` is `ready`.
4. Verify on the live domain — not just locally:
   - every referenced image returns 200
   - the Kaspersky script is absent
   - both forms still appear under `GET /api/v1/sites/<site_id>/forms`

## Reviewing an Edited Page From Juliette

She edits by saving the page through her browser ("Save As"). That reliably
introduces the following, all of which must be fixed before deploying:

- **Kaspersky script** injected into `<head>`
  (`<script src="https://gc.kis.v2.scr.kaspersky-labs.com/...">`) — strip it.
- **The entire `<style>` block duplicated.** Diff the two copies before deleting
  one; they are not always identical, and the *first* copy has held rules the
  second was missing.
- **Whole sections silently dropped**, leaving dead links (e.g. the Cub Hub
  Toddlers/Pre-Schoolers detail pages). Check every `href="#..."` resolves to an
  existing `id="..."`.
- **Copy that contradicts itself** where only half an edit landed (e.g. hero said
  "5 sports codes", body still said 6). Grep for figures that appear twice.

Not a real problem: garbled characters (`â€"`, `Â·`) when the file is pasted into
a chat or viewer are a **paste artifact**. Check the file on disk with
`file -I` first — it is normally valid UTF-8. Do not "fix" the encoding.

## Weekly "This Week" Video

The homepage `#video` slot plays `public/assets/videos/this-week.mp4`
(`<video preload="metadata">`, so the page shows a poster and only streams the
clip when a visitor hits play). To swap the weekly reel: replace that file with
the new mp4 (same name) and redeploy the `public` folder.

The video is **git-ignored** — it exceeds GitHub's 100 MB limit, so it lives only
locally and on Netlify, never in the repo. Keep a copy; a fresh clone won't have
it. Reels also run heavy (the first was ~114 MB); compress to ~10-20 MB with
ffmpeg (`-vcodec libx264 -crf 28 -vf scale=-2:1280`) before dropping in when you can.

## Account Safety

- Change the GoDaddy and Netlify passwords that were sent over email.
- Enable two-factor authentication on both accounts.
- Store shared credentials in a password manager instead of email or chat.

## Website Cleanup

- Done: move embedded base64 images out of `public/index.html` into `public/assets/images/`.
- Done: remove public-facing image upload controls from the page.
- Done: replace fake form submit handlers with real Netlify Forms.
- Done: add meta description, social share image, favicon, and canonical URL.
- Done: remove duplicate `Venue & Times` links.
- Restrict the Google Maps API key to the final production domain.
- Add privacy, POPIA, safeguarding, cancellation, and refund copy.

## Netlify Setup

- Create a new Netlify site from this project.
- Set publish directory to `public`.
- Leave build command blank.
- Add `huddlehub.co.za` and `www.huddlehub.co.za` under domain management.
- Enable HTTPS after DNS has propagated.

## GoDaddy DNS

- Back up existing DNS records before changing anything.
- Preserve all email records: MX, SPF, DKIM, and DMARC.
- Point `www` to the Netlify site URL with a CNAME record.
- Point the root domain to Netlify using the record Netlify shows in domain setup.
- Wait for propagation, which can take up to 48 hours.

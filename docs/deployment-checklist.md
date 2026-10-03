# HuddleHub Deployment Checklist

## Current Term 4 release

This is a static HTML site on the existing Netlify site
`09b74ab5-0c7f-450d-bd96-25f3cb0b6d19`, serving
`https://www.huddlehub.co.za`. Netlify publishes `public` with no build command.
The repository is **not linked to automatic deployment**: pushing to GitHub does
not update the live site.

Because the upload contains only `public`, Netlify never reads the root
`netlify.toml`. Response headers are served from `public/_headers`; keep it in
sync with the `[[headers]]` block in `netlify.toml`.

The current page uses one Netlify form, `term4-registration`. Its static fields
are `form-name`, `parent-name`, `phone`, `email`, `children-and-groups`, `message`
and the `bot-field` honeypot. Cub Hub interest and coaching enquiries use email
links in this version; the previous supplementary forms are not part of this
page.

## Local review and deployment preparation

1. Run `npm run preview` and review `http://127.0.0.1:5173` on desktop and phone
   widths. Check the timetable, prices, dates, navigation, coach images, both
   videos and booking flow with dummy details. The hero uses
   `assets/videos/term4-hero.mp4`; the existing highlights clip remains
   `assets/videos/this-week.mp4`. Confirm each clip plays and can be sought.
2. Run `npm test`. This runs the booking logic tests, local receiver tests and
   deployment validation tests without external dependencies.
3. Remember that local submissions are **simulated**: they are recorded only in
   `/tmp/huddlehub-local-submissions.jsonl`. Nothing goes to Netlify and no email
   is delivered. The local preview cannot prove genuine delivery or notification
   settings.
4. After the page review and final edits, run `npm run prepare:deploy`.
   Preparation checks referenced local HTML, CSS, scripts, fonts, images and
   video files; hash anchors; and the static Netlify form definition. It creates:
   - `/tmp/huddlehub-term4-deploy.zip`: the complete `public` folder, with
     `index.html` at the archive root.
   - `/tmp/huddlehub-term4-manifest.json`: the exact uploaded filenames, byte
     counts and SHA256 hashes, plus the archive hash and validation summary.
5. Re-run preparation after any change to `public`. Upload the freshly prepared
   archive only when deployment is authorized. Preparation itself does not
   contact Netlify or deploy anything.

The archive includes files ignored by Git, including both
`assets/videos/term4-hero.mp4` and `assets/videos/this-week.mp4`. It excludes operating-system junk and local
scratch files such as `.DS_Store`, `._*`, `__pycache__`, `.env*` and temporary
editor files. Never upload `index.html` alone: its assets must travel with it.

## Authorized upload and live verification

Use the existing Netlify site's authenticated deployment flow to upload
`/tmp/huddlehub-term4-deploy.zip`. Keep authentication in the existing account
configuration; do not copy credentials into source files, logs or this document.
Wait for the resulting deployment state to become `ready`.

Verify on its Netlify preview URL or the live domain:

- The HTML, CSS, scripts, fonts, images and both MP4s return successfully. Play
  and seek the new hero clip and the retained highlights clip separately.
- The new timetable, dates and prices appear, and phone navigation works.
- Netlify recognizes **`term4-registration`** and all its expected fields. Prior
  historical form names may remain in the dashboard; they do not prove that the
  new form was detected.
- A clearly labelled test booking reaches the Netlify submission dashboard with
  the parent, every child and every selected group intact.
- Configure or confirm notifications for this new form and verify that the
  expected notification reaches its intended destination. This remote check is
  required to claim genuine form and email delivery are working.
- Metadata, canonical URL and social sharing image still point to the production
  site, and the local-preview notice is absent.

## Rollback

Before uploading, retain the previous Netlify deploy ID and a complete local
backup of the prior `public` folder, including its ignored video. If the release
has a material issue, restore the previous published Netlify deploy or redeploy
that complete backup. A Git checkout alone is not a sufficient media backup.

## Video files

The newly supplied Term 4 video uses `public/assets/videos/term4-hero.mp4` in the
hero position previously occupied by a team image. The existing highlights
video stays at `public/assets/videos/this-week.mp4` and must retain its current
contents. These are two distinct clips, not replacements for one another.

The video directory is Git-ignored and the existing highlights clip is
approximately 114 MB. Keep separate copies of both MP4s. A fresh clone will not
contain them, and preparation will fail if a referenced video is missing. For
future video updates, re-run local playback and seeking checks, `npm test` and
`npm run prepare:deploy` after changing the intended clip.

## Historical browser-saved page issues

Earlier browser-saved page updates introduced injected Kaspersky scripts,
duplicated style blocks, missing programme sections and contradictory copy.
Those observations describe earlier inputs, not the current Term 4 export.
For future incoming files, inspect them before integrating edits and do not
publish a browser export or JavaScript bundle directly. The current preparation
checks cover missing assets and dead section anchors; visual and copy review
still matter.

Apparent garbled characters in pasted previews are not proof of a file encoding
problem. Inspect the actual UTF-8 file before changing its encoding.

## Account and DNS continuity

- Use the existing Netlify site and domain configuration; this update does not
  require creating a new site or changing DNS.
- Keep account credentials in a password manager and use two-factor
  authentication. Change any credentials that were previously shared by email.
- Before any separately authorized DNS change, back up the current records and
  preserve all email records: MX, SPF, DKIM and DMARC.
- Keep `www` pointed at the site's configured Netlify target, and follow
  Netlify's current instructions for the root domain. Allow for DNS propagation
  before judging a change and confirm HTTPS afterward.

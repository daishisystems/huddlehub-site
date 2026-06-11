# HuddleHub Deployment Checklist

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

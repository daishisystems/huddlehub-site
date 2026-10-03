# HuddleHub Website

Static website project for HuddleHub.

## Project Structure

- `public/index.html` - the live website entry point.
- `public/assets/images/` - extracted website images referenced by the HTML.
- `netlify.toml` - Netlify publish configuration.
- `.vscode/` - VS Code settings, task, and extension recommendations.
- `docs/deployment-checklist.md` - deployment and domain checklist.

## Local Preview

From this folder:

```sh
npm run preview
```

Then open:

```text
http://127.0.0.1:5173
```

The preview binds only to `127.0.0.1`. Its forms simulate a successful submission
and save test records to `/tmp/huddlehub-local-submissions.jsonl`, outside the
repository. **They do not submit externally or deliver email.** Use dummy details
when testing. Genuine form delivery and notifications can only be verified on a
Netlify preview or deployment.

The local server accepts `POST /` for `term4-registration`, with a URL-encoded
body up to 64 KB. Inspect test records
at `http://127.0.0.1:5173/__preview/submissions`.

To simulate a failed booking, run the following once, then submit a form:

```sh
curl -X POST http://127.0.0.1:5173/__preview/fail-next
```

The next valid form submission returns HTTP 503 without saving a record; following
submissions work normally. To test the sending state, or use a different port:

```sh
npm run preview -- --delay-post 3 --port 5174
```

Run the preview server checks with `python3 -m unittest discover -s tests`.

## Netlify

The site is live at https://www.huddlehub.co.za (site id `09b74ab5-0c7f-450d-bd96-25f3cb0b6d19`).
Netlify publishes the `public` folder and needs no build command.

> **This repo is not linked to Netlify.** Pushing to GitHub does **not** deploy.
> Updates are deployed manually by uploading the whole `public` folder — the HTML
> and `assets/` must travel together, or every image breaks. See
> [docs/deployment-checklist.md](docs/deployment-checklist.md) for the deploy
> command and the pre-deploy review steps.

The public forms use Netlify Forms. Before going live, confirm form notifications in Netlify and restrict the Google Maps API key to the final production domain.

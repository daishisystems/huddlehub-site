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
http://localhost:5173
```

You can also run the VS Code task named `Preview HuddleHub site`.

## Netlify

The site is live at https://www.huddlehub.co.za (site id `09b74ab5-0c7f-450d-bd96-25f3cb0b6d19`).
Netlify publishes the `public` folder and needs no build command.

> **This repo is not linked to Netlify.** Pushing to GitHub does **not** deploy.
> Updates are deployed manually by uploading the whole `public` folder — the HTML
> and `assets/` must travel together, or every image breaks. See
> [docs/deployment-checklist.md](docs/deployment-checklist.md) for the deploy
> command and the pre-deploy review steps.

The public forms use Netlify Forms. Before going live, confirm form notifications in Netlify and restrict the Google Maps API key to the final production domain.

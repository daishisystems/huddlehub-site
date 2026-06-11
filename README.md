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

This project is ready for Netlify static hosting. Netlify should publish the `public` folder and does not need a build command.

The public forms use Netlify Forms. Before going live, confirm form notifications in Netlify and restrict the Google Maps API key to the final production domain.

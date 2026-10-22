# How this profile works

`README.md` and everything in `assets/generated/` are generated. Do not edit them by hand.

1. Edit `profile.json`: your headline, intro, what you are working on, featured projects, stack, and links.
2. Commit and push. The `profile` workflow runs `scripts/build.py`. The script reads `profile.json` and live GitHub data, then rewrites `README.md` and the images in `assets/generated/`.
3. The `profile` workflow also runs every day, so stars, dates, descriptions, and "Recently active" stay current.

Set `"show_projects": false` in `profile.json` to hide both "Selected projects" and "Recently active". Set it to `true` to show them again using the saved project settings.

To build on your own computer:

```bash
pip install fonttools brotli
python scripts/build.py
```

The script reads your GitHub token from `gh auth token` when `GITHUB_TOKEN` is not set.

Brand logos in `assets/icons/icons.json` come from Simple Icons (CC0). Fonts are listed in `fonts/README.md`.

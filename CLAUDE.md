# Working on this repository

This is the **pristine template** for a live git-teaching activity.
Instances are created from it with `scripts/new-instance.sh`, one per class, and students fork the instance.
`TEACHERS.md` is the runbook and explains what the activity is; read it before changing how anything behaves.

## Hard constraints

**`site/*.py` uses the standard library only.**
No third-party packages, ever.
It has to run on a bare GitHub Actions runner and in a Codespace with no install step, which is the whole reason the site builder is hand-written rather than using a Markdown library.

**Python must parse on 3.9.**
`/usr/bin/python3` on macOS is 3.9, and that is what a plain `python3` can resolve to.
In particular, **no backslashes inside f-string expressions** — that is a 3.12+ feature and it silently worked for a while here because GitHub's runners are new enough.
Check with `/usr/bin/python3 -m py_compile site/*.py`, not just `python3`.

**Shell scripts must work on macOS bash 3.2.**
No `mapfile`, no `${var,,}`, no associative arrays.
Use `while IFS= read -r x; do arr+=("$x"); done < <(...)` instead of `mapfile`.

**Graphviz is optional at runtime.**
`site/build.py` must always fall back to the ASCII commit graph when `dot` is absent, so the site still builds on a machine without it.
Never make the build hard-fail on a missing `dot`.

## The template/instance split

`instance.txt` is the discriminator: it contains `Template` here, and the class name in an instance.
Three things depend on that, and they must stay coherent with each other:

- `.github/workflows/pages.yml` skips the **deploy** job unless it is an instance. GitHub Pages is enabled per instance, so deploying from the template always 404s. The build job still runs, so a broken site is caught here.
- `scripts/new-instance.sh` replaces `TEACHERS.md` in the instance with a stub pointing back here, and strips the `<!-- template-only -->` banner from `README.md`.
- Everything `new-instance.sh` does must stay **idempotent**. Re-running it is the documented recovery path when a step fails.

**Workflows only reach an instance at creation time.**
Editing a workflow here does not fix instances that already exist; those have to be recreated.
Say so rather than implying a fix propagates.

## History

The repository is published and has been forked.
Do not rewrite history, squash published commits, or force-push.

## Testing

`./scripts/dry-run.sh 20` builds a realistic multi-author history — twenty students, parallel forks, sequential merges, genuine conflicts — in a throwaway clone.
Use it instead of hand-crafting test data; it is also how to check a change to the site actually looks right with real content.

To look at the built site, serve it over http (`python3 -m http.server`) — the browser tools cannot open `file://` URLs.
The pages are light/dark aware, so check both.

Before committing: `bash -n` every script, `/usr/bin/python3 -m py_compile site/*.py`, and parse each workflow as YAML.

## Two facts that constrain the design

Both are established with data in `TEACHERS.md` and are easy to break by accident:

- Merge conflicts require **everyone to fork before any merging starts**. A student who forks after their classmates' work has landed cannot collide with it. This is why `dry-run.sh` branches every simulated student from a fixed base commit.
- Students choose lines with strong **primacy bias** — they edit the top of the file. This is why full-length stories still produce conflicts and why `dry-run.sh` models a biased picker by default.

Read the "Why 'pick any line, anywhere' is enough" section of `TEACHERS.md` before changing story lengths, the `dry-run.sh` picking model, or `HOT_LINES`.

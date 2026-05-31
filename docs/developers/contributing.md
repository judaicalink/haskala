# Contributing

## Branch model

- `main` — released code only. Merge to main triggers a deploy.
- `development` — integration branch. Feature branches merge here.
- `feature/<slug>` — new functionality. Branch off `development`.
- `bugfix/<slug>` — non-trivial fixes. Branch off `development`.
- `hotfix/<slug>` — urgent fix that has to go straight to `main`.

The Github Issues board is the canonical task tracker. Reference the
issue in the branch name when convenient (`feature/14-book-detail`)
and in the commit body via "Close #14".

## Commit messages

- All commits are written in English.
- Subject line in the imperative mood ("fix nginx CSRF",
  "add ris_escape filter") and short enough for `git log --oneline`
  to remain readable.
- Body explains the *why*, not the *what* — readers will see the diff.
- Wrap at ~72 columns for the body.
- No Claude attribution and no `Co-Authored-By` tags.

A representative example:

```
fix(citation): newline-safety + multi-author/-language test coverage

Close #16.

- Add a ris_escape template filter that flattens \r and \n in
  RIS field values and collapses adjacent whitespace.
- Apply it to every interpolated field in cite/ris.txt.
- Add four new test classes that cover the previously-untested
  multi-valued loop branches and the newline-safety guarantee.
```

## Pre-commit checks

Run these locally before pushing. CI runs the same set.

```bash
docker compose exec web python manage.py test
flake8 --max-line-length=120 home/ haskala/
```

A few legacy flake8 warnings in `home/models.py` are tolerated for
now (E302, E303, F811, E402, W293 — all on lines that pre-date the
checker tightening). Don't add new ones; fix existing ones in
passing where the diff is small.

## Pull requests

- Open against `development` by default.
- Use the issue number in the title or body so Github closes it
  when the PR merges.
- A PR should pass tests and flake8 locally before review.
- Squash the PR when it lands. Per-feature commit history is
  preserved in the branch ref, not on the merged-to-development
  trunk.

## When to open an issue first

- Anything more invasive than a one-file refactor.
- Anything that touches the data model.
- Anything that adds or removes a service from the Docker stack.

Smaller in-passing fixes can land directly via a focused PR.

## Code style

- Python: PEP 8 with the project's 120-column line cap.
- Templates: 4-space indent, named blocks, BEM-ish class roots
  (`book-section__heading`, `person-toc__link`, …).
- SCSS: 2-space indent, partials named `_book_detail.scss` and
  imported from `haskala.scss`.

## Memory and conventions

Some workflow conventions live outside the repo (e.g. how PRs are
reviewed, which tracker columns mean what). When you stumble over an
unwritten rule, ask the maintainer once and consider whether it
belongs in this document.

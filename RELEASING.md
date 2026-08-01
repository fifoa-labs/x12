# Releasing a New Version of `ansi-x12`

This project publishes releases through GitHub Actions using PyPI Trusted Publishing.

The release flow is:

```text
Update code
→ Update version
→ Validate locally
→ Commit and push
→ Create and push Git tag
→ Publish GitHub Release
→ GitHub Actions publishes to PyPI
→ Verify installation
```

No PyPI password, API token, or manual Twine upload is required.

---

## 1. Finish the Changes

Make all code, test, and documentation updates.

Run the normal development checks:

```bash
make check
```

Before releasing, ensure:

* Tests cover the new behavior.
* Ruff passes.
* Mypy passes.
* Public APIs are documented.
* `README.md` is updated when necessary.
* No private, customer, carrier, or production data is included.
* The working tree contains only intentional changes.

Review:

```bash
git status
git diff
```

---

## 2. Choose the New Version

The project follows semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Examples:

### Patch release

Use for bug fixes or small compatible improvements:

```text
0.1.0 → 0.1.1
```

### Minor release

Use for new backward-compatible features:

```text
0.1.1 → 0.2.0
```

### Major release

Use for stable breaking changes:

```text
0.9.0 → 1.0.0
```

While the project remains below `1.0.0`, a minor-version increase may also indicate meaningful API changes.

---

## 3. Update `pyproject.toml`

Change:

```toml
[project]
version = "0.1.0"
```

to the new version, for example:

```toml
[project]
version = "0.1.1"
```

The following three values must agree:

```text
pyproject.toml version: 0.1.1
Git tag:                v0.1.1
GitHub Release:         ansi-x12 0.1.1
```

Do not reuse a version that has already been published to PyPI. Published PyPI versions cannot be replaced.

---

## 4. Update the Lockfile

After changing the version or dependencies:

```bash
uv lock
```

If dependencies were added or updated:

```bash
make sync
```

Review the resulting changes:

```bash
git diff -- pyproject.toml uv.lock
```

---

## 5. Run the Full Release Check

Run:

```bash
make release-check
```

This performs:

* cleanup
* Ruff formatting check
* Ruff linting
* strict mypy checking
* complete test suite
* statement and branch coverage
* wheel and source distribution build
* Twine distribution validation
* `py.typed` inclusion check

A successful release check should end with results similar to:

```text
All checks passed
Success: no issues found
456 passed
Required test coverage of 100% reached
Successfully built ...
Twine check: PASSED
Wheel contains x12/py.typed
```

Do not continue if any release check fails.

---

## 6. Review the Built Package

The release check creates:

```text
dist/ansi_x12-<version>-py3-none-any.whl
dist/ansi_x12-<version>.tar.gz
```

Optionally inspect the wheel:

```bash
make wheel-contents
```

Confirm that it contains the public package:

```text
x12/__init__.py
x12/envelopes.py
x12/exceptions.py
x12/inspection.py
x12/inspector.py
x12/parser.py
x12/py.typed
x12/segments.py
x12/separators.py
x12/tokenizer.py
```

It should not contain:

* `.coverage`
* `.env`
* caches
* private fixtures
* application-specific code
* local development files

---

## 7. Commit the Release Changes

Review everything:

```bash
git status
git diff
```

Stage the intended files:

```bash
git add .
```

Commit using the release version:

```bash
git commit -m "Prepare ansi-x12 0.1.1 release"
```

Push the commit:

```bash
git push origin main
```

Ensure the push succeeds before creating the tag.

---

## 8. Create the Git Tag

Create an annotated tag matching the package version:

```bash
git tag -a v0.1.1 -m "ansi-x12 0.1.1"
```

Push the tag:

```bash
git push origin v0.1.1
```

Verify it:

```bash
git tag --list
git show v0.1.1 --stat
```

The tag should point to the exact commit containing the matching version in `pyproject.toml`.

---

## 9. Create the GitHub Release

Open:

```text
https://github.com/fifoa-labs/x12/releases/new
```

Complete the release form:

```text
Choose a tag:   v0.1.1
Release title:  ansi-x12 0.1.1
Release label:  None
Set as latest:  Yes
Pre-release:    No, unless intentionally releasing alpha/beta/RC
```

Write release notes describing what changed.

Example:

````markdown
# ansi-x12 0.1.1

Patch release with parser and documentation improvements.

## Changed

- Improved validation error messages
- Expanded structural inspection coverage
- Clarified byte-oriented parsing documentation

## Fixed

- Corrected handling of a malformed envelope edge case

## Quality

- Python 3.11–3.14 supported
- Fully typed with `py.typed`
- 100% statement and branch coverage

## Installation

```bash
pip install --upgrade ansi-x12
````

````

Click **Publish release**.

Publishing the GitHub Release triggers:

```text
.github/workflows/publish.yml
````

---

## 10. Watch GitHub Actions

Open:

```text
GitHub repository
→ Actions
→ Publish to PyPI
```

The workflow should:

1. Check out the tagged source.
2. Install uv.
3. Build the wheel and source distribution.
4. Upload the build artifact.
5. Enter the `pypi` GitHub environment.
6. Authenticate to PyPI through OIDC.
7. Publish the distributions.

The workflow should finish with a green check.

Do not manually upload the same version if the workflow is still running.

---

## 11. Verify the PyPI Release

Open:

```text
https://pypi.org/project/ansi-x12/
```

Confirm:

* The new version is listed.
* The README renders correctly.
* The project links are correct.
* Python requirements are correct.
* The wheel and source archive are available.

---

## 12. Test Installation Outside the Repository

Test from a temporary environment so the local source directory cannot hide packaging errors:

```bash
rm -rf /tmp/ansi-x12-release-test

uv venv \
    --python 3.11 \
    /tmp/ansi-x12-release-test

uv pip install \
    --python /tmp/ansi-x12-release-test/bin/python \
    ansi-x12==0.1.1
```

Verify the installed distribution and import:

```bash
/tmp/ansi-x12-release-test/bin/python - <<'PY'
from importlib.metadata import version

import x12

print("Distribution version:", version("ansi-x12"))
print("Imported from:", x12.__file__)
print("Public API names:", len(x12.__all__))
PY
```

Expected:

```text
Distribution version: 0.1.1
Imported from: .../site-packages/x12/__init__.py
```

Clean up:

```bash
rm -rf /tmp/ansi-x12-release-test
```

---

## 13. Confirm the Local Repository State

After release verification:

```bash
git status
```

Generated files such as `dist/`, `.coverage`, and `htmlcov/` may exist locally but should be ignored by Git.

Optionally clean them:

```bash
make clean
```

---

# Fast Release Summary

For a normal patch release:

```bash
# 1. Update version in pyproject.toml
#    0.1.0 → 0.1.1

uv lock

make release-check

git status
git diff

git add .
git commit -m "Prepare ansi-x12 0.1.1 release"
git push origin main

git tag -a v0.1.1 -m "ansi-x12 0.1.1"
git push origin v0.1.1
```

Then:

```text
GitHub
→ Releases
→ Draft a new release
→ Select v0.1.1
→ Title: ansi-x12 0.1.1
→ Add release notes
→ Publish release
```

Finally:

```text
GitHub Actions
→ Confirm successful PyPI publication
→ Test pip installation from a clean environment
```

---

# Important Rules

## Never rebuild or upload manually during the workflow

GitHub Actions is the official publisher. Do not run:

```bash
twine upload dist/*
```

unless deliberately recovering from an automation failure and you fully understand the consequences.

## Never reuse a published version

After PyPI accepts `0.1.1`, another upload using `0.1.1` will be rejected.

Use a new version:

```text
0.1.2
```

## The tag must match the project version

Correct:

```text
pyproject.toml: 0.1.1
tag:            v0.1.1
release title:  ansi-x12 0.1.1
```

Incorrect:

```text
pyproject.toml: 0.1.1
tag:            v0.1.2
```

## Do not publish from an unvalidated working tree

Always run:

```bash
make release-check
```

before committing and tagging a release.

## Do not store PyPI secrets

Publishing uses GitHub OIDC Trusted Publishing.

The `pypi` GitHub environment should contain:

```text
Secrets:   none
Variables: none
```

---

# Release Checklist

```text
[ ] Code and tests are complete
[ ] README and documentation are current
[ ] Version updated in pyproject.toml
[ ] uv.lock refreshed
[ ] make release-check passes
[ ] git diff reviewed
[ ] Release commit pushed to main
[ ] Annotated version tag created
[ ] Tag pushed to GitHub
[ ] GitHub Release published
[ ] Publish workflow succeeds
[ ] New version appears on PyPI
[ ] Clean external installation succeeds
```

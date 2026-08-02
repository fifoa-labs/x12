# Releasing a New Version of `ansi-x12`

`ansi-x12` is published to PyPI from GitHub Actions through PyPI Trusted
Publishing. The distribution name is `ansi-x12`; the Python import package is
`x12`.

The release flow is:

```text
Finish changes
→ Choose and set the version
→ Refresh the lockfile
→ Validate source and distributions locally
→ Commit and push to main
→ Confirm CI succeeds
→ Create and push an annotated tag
→ Publish a GitHub Release
→ GitHub Actions publishes to PyPI
→ Verify the published package from a clean environment
```

No PyPI password, API token, or manual upload is required. Twine is used only
to validate built distributions locally.

---

## 1. Finish the Changes

Complete all intended code, tests, and documentation before preparing the
release.

Run the normal development checks:

```bash
make check
```

Before continuing, confirm:

- Tests cover all new or changed behavior.
- Ruff formatting and linting pass.
- Strict mypy checking passes.
- Public APIs and behavior changes are documented.
- `README.md` and `RELEASING.md` are current.
- No private, customer, carrier, vendor, or production data is included.
- The working tree contains only intentional changes.

Review the repository:

```bash
git status
git diff --check
git diff
```

Do not begin a release from an unexplained or partially staged working tree.

---

## 2. Choose the New Version

The project uses semantic-style versions:

```text
MAJOR.MINOR.PATCH
```

Use the project convention below while the package remains below `1.0.0`.

### Patch release

Use a patch release for bug fixes, documentation corrections, internal
reorganization that preserves the supported public API, and other small
compatible improvements:

```text
0.1.2 → 0.1.3
```

### Minor release

Use a minor release for a meaningful new backward-compatible capability:

```text
0.1.3 → 0.2.0
```

Examples include adding serialization, construction APIs, or another
substantial public feature.

### Major release

Use `1.0.0` when the public API is ready to be treated as stable. After
`1.0.0`, incompatible public API changes require a major-version increase.

Because versions below `1.0.0` represent active development, a minor-version
increase may also communicate a meaningful public API change. Document such
changes clearly in the release notes.

Never reuse a version already published to PyPI. Published files cannot be
replaced with different files under the same version.

---

## 3. Update `pyproject.toml`

Update the project version in `pyproject.toml`:

```toml
[project]
name = "ansi-x12"
version = "0.1.3"
```

After editing the file, load the version into the current shell so later
commands use the exact value from project metadata:

```bash
VERSION="$(uv run python -c '
import tomllib
with open("pyproject.toml", "rb") as file:
    print(tomllib.load(file)["project"]["version"])
')"

printf 'Preparing ansi-x12 %s\n' "$VERSION"
```

The following values must agree exactly:

```text
pyproject.toml:  <version>
Git tag:         v<version>
GitHub Release:  ansi-x12 <version>
PyPI version:    <version>
```

For example:

```text
pyproject.toml:  0.1.3
Git tag:         v0.1.3
GitHub Release:  ansi-x12 0.1.3
PyPI version:    0.1.3
```

---

## 4. Refresh the Lockfile

Refresh `uv.lock` after changing the project version or dependency metadata:

```bash
uv lock
```

If dependencies were added or changed, synchronize the development
environment as well:

```bash
make sync
```

Review the metadata changes:

```bash
git diff -- pyproject.toml uv.lock
```

Confirm that the local project version in `uv.lock` matches the version in
`pyproject.toml`.

---

## 5. Run the Full Release Validation

Run the complete local release validation:

```bash
make release-check
```

The target performs:

- generated-file cleanup;
- Ruff formatting verification;
- Ruff linting;
- strict mypy checking;
- the complete test suite;
- statement and branch coverage;
- wheel and source-distribution builds;
- Twine distribution validation; and
- verification that `x12/py.typed` is included in the wheel.

Successful output should include results equivalent to:

```text
All checks passed
Success: no issues found
All tests passed
Required test coverage of 100% reached
Successfully built ...
PASSED
Wheel contains x12/py.typed
```

Exact test, statement, and branch counts change as the project grows and
should not be hard-coded into this guide.

Do not continue while any release validation step is failing.

---

## 6. Inspect the Built Distributions

A successful build creates files similar to:

```text
dist/ansi_x12-<version>-py3-none-any.whl
dist/ansi_x12-<version>.tar.gz
```

List the wheel contents:

```bash
make wheel-contents
```

Confirm that the wheel contains the supported package structure, including:

```text
x12/__init__.py
x12/py.typed
x12/core/__init__.py
x12/core/envelopes.py
x12/core/exceptions.py
x12/core/inspection.py
x12/core/inspector.py
x12/core/parser.py
x12/core/segments.py
x12/core/separators.py
x12/core/tokenizer.py
x12/transactions/__init__.py
```

The wheel should not contain:

- tests or private fixtures;
- `.coverage`, `coverage.xml`, or `htmlcov/`;
- `.env`, `.pypirc`, or credentials;
- caches or bytecode;
- application-specific integration code; or
- local editor and development files.

Optionally inspect the source distribution:

```bash
tar -tzf "dist/ansi_x12-${VERSION}.tar.gz" | less
```

---

## 7. Install the Local Wheel in a Clean Environment

`make release-check` validates the distributions but does not prove that the
wheel imports correctly after installation. Install the exact local wheel in
a temporary environment before committing the release.

```bash
WHEEL="$(find dist -maxdepth 1 \
    -name "ansi_x12-${VERSION}-*.whl" \
    -print -quit)"

test -n "$WHEEL" || {
    echo "No wheel found for ansi-x12 ${VERSION}."
    exit 1
}

rm -rf /tmp/ansi-x12-wheel-test
uv venv --python 3.11 /tmp/ansi-x12-wheel-test
uv pip install \
    --python /tmp/ansi-x12-wheel-test/bin/python \
    "$WHEEL"
```

Verify distribution metadata, imports, typing marker availability, and the
primary public API:

```bash
/tmp/ansi-x12-wheel-test/bin/python - <<PY
from importlib.metadata import files, version

import x12
from x12 import parse_x12_interchange, tokenize_x12

expected_version = "$VERSION"
installed_version = version("ansi-x12")
installed_files = files("ansi-x12") or ()

assert installed_version == expected_version
assert any(str(path) == "x12/py.typed" for path in installed_files)
assert callable(tokenize_x12)
assert callable(parse_x12_interchange)

print("Distribution version:", installed_version)
print("Imported from:", x12.__file__)
print("Public API names:", len(x12.__all__))
print("Typing marker: x12/py.typed")
PY
```

Clean up:

```bash
rm -rf /tmp/ansi-x12-wheel-test
```

Use `uv pip install --python ...` for this check. A newly created uv virtual
environment is not guaranteed to contain pip for `python -m pip`.

---

## 8. Review and Commit the Release

Review all release changes and generated metadata:

```bash
git status
git diff --check
git diff
```

`dist/`, coverage files, and caches may exist locally but must remain ignored
by Git.

Stage only the intended tracked files:

```bash
git add .
git status
```

Commit using the version from `pyproject.toml`:

```bash
git commit -m "Prepare ansi-x12 ${VERSION} release"
```

Push the release commit:

```bash
git push origin main
```

Record the release commit for later verification:

```bash
RELEASE_COMMIT="$(git rev-parse HEAD)"
printf 'Release commit: %s\n' "$RELEASE_COMMIT"
```

---

## 9. Confirm CI Is Green

The PyPI publishing workflow builds and uploads distributions, but it does not
run Ruff, mypy, or the test suite. Therefore, do not publish the GitHub Release
until the CI workflow for the release commit has succeeded.

Check:

```text
GitHub repository
→ Actions
→ CI
→ Confirm the main-branch run for the release commit is green
```

With GitHub CLI, the recent runs can also be inspected with:

```bash
gh run list --workflow ci.yml --branch main --limit 5
```

Verify that the successful run corresponds to the release commit pushed in the
previous step.

---

## 10. Create and Push the Annotated Tag

First confirm that the version tag does not already exist:

```bash
git tag --list "v${VERSION}"
```

The command should print nothing.

Confirm the working tree is clean and `HEAD` is still the release commit:

```bash
git status --short
test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"
```

Create an annotated tag:

```bash
git tag -a "v${VERSION}" -m "ansi-x12 ${VERSION}"
```

Verify the tag before pushing it:

```bash
git show "v${VERSION}" --stat
```

Push the tag:

```bash
git push origin "v${VERSION}"
```

The tag must point to the exact commit containing the matching version in
`pyproject.toml` and `uv.lock`.

---

## 11. Prepare Release Notes

Release notes should describe user-visible changes, compatibility notes, and
quality guarantees without repeating the commit history line by line.

A reusable template is:

~~~markdown
# ansi-x12 <version>

Briefly describe the purpose of this release.

## Added

- New public capabilities, if any.

## Changed

- Compatible behavior, structure, or documentation changes.

## Fixed

- Corrected parsing, validation, packaging, or API behavior.

## Compatibility

- Mention any changed import paths or intentionally stricter validation.
- State whether the documented top-level `x12` API remains compatible.

## Quality

- Python 3.11–3.14 supported
- Fully typed with `py.typed`
- 100% statement and branch coverage

## Installation

```bash
pip install --upgrade ansi-x12
```
~~~

Keep release notes factual. Do not claim a capability that is not included in
the tagged source.

---

## 12. Publish the GitHub Release

Open:

```text
https://github.com/fifoa-labs/x12/releases/new
```

Complete the release form:

```text
Choose a tag:   v<version>
Release title:  ansi-x12 <version>
Set as latest:  Yes
Pre-release:    No, unless intentionally publishing an alpha, beta, or RC
```

Add the prepared release notes and select **Publish release**.

The release must be published, not left as a draft. The publish workflow is
triggered specifically by the GitHub `release.published` event.

With GitHub CLI, the equivalent command is:

```bash
gh release create "v${VERSION}" \
    --verify-tag \
    --title "ansi-x12 ${VERSION}" \
    --notes-file /path/to/release-notes.md
```

Publishing the release triggers:

```text
.github/workflows/publish.yml
```

Do not publish the release until local validation and CI have both succeeded.

---

## 13. Watch the PyPI Publish Workflow

Open:

```text
GitHub repository
→ Actions
→ Publish to PyPI
```

The workflow should:

1. Check out the tagged source.
2. Install uv.
3. Build the wheel and source distribution with `uv build`.
4. Upload the distributions as a short-lived workflow artifact.
5. Enter the protected `pypi` GitHub environment.
6. Request an OIDC identity token.
7. Publish through `pypa/gh-action-pypi-publish`.

The workflow should finish with a green check.

With GitHub CLI:

```bash
gh run list --workflow publish.yml --limit 3
```

Do not manually upload the same version while the workflow is running.

---

## 14. Verify the PyPI Release

Open:

```text
https://pypi.org/project/ansi-x12/
```

Confirm:

- The new version is listed.
- The project description and README render correctly.
- Project links are correct.
- The Python requirement is correct.
- Both the wheel and source distribution are available.
- The published filenames contain the expected version.

Remember:

```text
PyPI distribution: ansi-x12
Python import:      x12
```

---

## 15. Test the Published Package Outside the Repository

Test the exact PyPI version in a new temporary environment so the repository
source tree cannot mask packaging problems:

```bash
rm -rf /tmp/ansi-x12-release-test
uv venv --python 3.11 /tmp/ansi-x12-release-test
uv pip install \
    --python /tmp/ansi-x12-release-test/bin/python \
    "ansi-x12==${VERSION}"
```

Verify the installed package:

```bash
/tmp/ansi-x12-release-test/bin/python - <<PY
from importlib.metadata import files, version

import x12
from x12 import parse_x12_interchange, tokenize_x12

expected_version = "$VERSION"
installed_version = version("ansi-x12")
installed_files = files("ansi-x12") or ()

assert installed_version == expected_version
assert any(str(path) == "x12/py.typed" for path in installed_files)
assert callable(tokenize_x12)
assert callable(parse_x12_interchange)

print("Distribution version:", installed_version)
print("Imported from:", x12.__file__)
print("Public API names:", len(x12.__all__))
print("Typing marker: x12/py.typed")
PY
```

Expected output includes:

```text
Distribution version: <version>
Imported from: .../site-packages/x12/__init__.py
Typing marker: x12/py.typed
```

Clean up:

```bash
rm -rf /tmp/ansi-x12-release-test
```

---

## 16. Confirm the Final Repository State

After publication and external installation verification:

```bash
git status
```

The tracked working tree should be clean. Generated files such as `dist/`,
`.coverage`, and `htmlcov/` may remain locally but should be ignored by Git.

Optionally clean generated output:

```bash
make clean
```

Verify the release tag one final time:

```bash
git show "v${VERSION}" --stat
```

---

# Fast Release Summary

Use this only after reading and understanding the full procedure above.

```bash
# 1. Update [project].version in pyproject.toml.

uv lock

VERSION="$(uv run python -c '
import tomllib
with open("pyproject.toml", "rb") as file:
    print(tomllib.load(file)["project"]["version"])
')"

make release-check
make wheel-contents

WHEEL="$(find dist -maxdepth 1 \
    -name "ansi_x12-${VERSION}-*.whl" \
    -print -quit)"
rm -rf /tmp/ansi-x12-wheel-test
uv venv --python 3.11 /tmp/ansi-x12-wheel-test
uv pip install \
    --python /tmp/ansi-x12-wheel-test/bin/python \
    "$WHEEL"
/tmp/ansi-x12-wheel-test/bin/python -c \
    'from importlib.metadata import version; import x12; print(version("ansi-x12"), x12.__file__)'
rm -rf /tmp/ansi-x12-wheel-test

git status
git diff --check
git diff

git add .
git commit -m "Prepare ansi-x12 ${VERSION} release"
git push origin main

# Confirm the CI run for this commit is green before continuing.

git tag -a "v${VERSION}" -m "ansi-x12 ${VERSION}"
git push origin "v${VERSION}"
```

Then publish a GitHub Release for `v${VERSION}`. Confirm the **Publish to
PyPI** workflow succeeds, verify the version on PyPI, and install the exact
published version in a clean environment.

---

# Failure and Recovery Guidance

## Local validation fails

Do not commit or tag the release. Fix the issue, rerun the failed target, and
then rerun:

```bash
make release-check
```

## CI fails after the release commit is pushed

Do not create the tag or GitHub Release. Fix the issue in a new commit, push it,
rerun local release validation as needed, and wait for CI to succeed.

## A tag was pushed, but the GitHub Release was not published

If the tag points to the wrong commit and no GitHub Release or PyPI upload has
occurred, delete and recreate the tag carefully:

```bash
git tag -d "v${VERSION}"
git push origin ":refs/tags/v${VERSION}"
```

Then create the corrected annotated tag and push it again.

Do not rewrite a tag after users may have consumed it or after any package file
has reached PyPI.

## The publish workflow fails before PyPI accepts any files

Inspect the workflow logs first. Confirm on PyPI that the version does not
exist before retrying or replacing the release/tag. The workflow checks out the
tagged source, so changing only `main` does not change an existing release run.

## PyPI accepts any file for the version

That version is consumed. Do not rebuild or replace it. Fix the problem and
publish a new version. If the release is seriously defective, consider yanking
it on PyPI and immediately publish a corrected version.

---

# Important Rules

## GitHub Actions is the official publisher

Do not run:

```bash
twine upload dist/*
```

The project uses PyPI Trusted Publishing through GitHub OIDC. Manual Twine
upload is not part of the normal or recovery workflow.

## Never reuse a published version

Once PyPI accepts a version, its files cannot be replaced with different
artifacts under the same version number.

## The version, tag, and release must match

Correct:

```text
pyproject.toml: 0.1.3
Git tag:        v0.1.3
Release title:  ansi-x12 0.1.3
```

Incorrect:

```text
pyproject.toml: 0.1.3
Git tag:        v0.1.4
```

## Do not publish from an unvalidated commit

Before tagging, all of the following must be true:

- `make release-check` passes locally;
- the local wheel installs and imports successfully;
- the release commit is pushed to `main`; and
- GitHub CI for that exact commit is green.

## Do not store PyPI credentials

The `pypi` GitHub environment should use Trusted Publishing and require no
PyPI API token:

```text
Secrets:   none
Variables: none
```

The publish job receives only the `id-token: write` permission needed for
OIDC authentication.

---

# Release Checklist

```text
[ ] Code, tests, and documentation are complete
[ ] No private or production data is included
[ ] Version updated in pyproject.toml
[ ] uv.lock refreshed
[ ] Version in pyproject.toml and uv.lock agrees
[ ] make release-check passes
[ ] Wheel contents reviewed
[ ] Local wheel installs and imports in a clean environment
[ ] git diff --check passes
[ ] Full git diff reviewed
[ ] Release commit pushed to main
[ ] CI succeeds for the exact release commit
[ ] Annotated version tag created
[ ] Tag verified and pushed to GitHub
[ ] Release notes prepared
[ ] GitHub Release published for the matching tag
[ ] Publish to PyPI workflow succeeds
[ ] New version and both distributions appear on PyPI
[ ] Exact PyPI version installs and imports cleanly
[ ] Final tracked working tree is clean
```

# First contribution walkthrough

This guide takes a small change from a fresh fork to an open pull request. The
commands work in Bash on macOS/Linux and PowerShell on Windows unless a note
says otherwise. Allow about ten minutes for the steps here, plus the time for
`python tasks.py check` and CI.

## 1. Fork and clone your fork

On GitHub, open the [AAMR repository](https://github.com/krapcys1-maker/adaptive-agent-memory-research)
and select **Fork**. Then clone your fork (replace `YOUR-USERNAME` with your
GitHub username):

```text
git clone https://github.com/YOUR-USERNAME/adaptive-agent-memory-research.git
cd adaptive-agent-memory-research
```

This full clone matters: one integrity test reads an earlier commit from Git
history. If you already cloned the upstream repository, you can instead add
your fork as `origin` and fetch it, but a fresh fork clone is the simplest
starting point.

### Windows note

If Git reports `Filename too long` while cloning or checking out files, enable
long paths and retry:

```powershell
git config --global core.longpaths true
```

This is a per-user Git setting. It is only needed on Windows when the checkout
hits that path-length limit.

## 2. Create a branch and make a small change

Start a branch for one focused change:

```text
git switch -c docs/fix-a-typo
```

For a first practice change, correct a typo or clarify one sentence in a
Markdown document. Save the file, then inspect what you changed:

```text
git status --short
git diff
```

Keep the pull request to one topic. If you want to work on an issue, read its
acceptance criteria first and comment there before starting so another
contributor does not duplicate the work.

## 3. Run the local checks

Create a virtual environment, install the development requirements into it,
then run the quick integrity check and the full local check. In PowerShell on
Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python tasks.py fast
python tasks.py check
```

On macOS or Linux, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python tasks.py fast
python tasks.py check
```

If PowerShell does not allow activation, use `.venv\Scripts\python.exe` in
place of `python` for the install and both check commands. The virtual
environment keeps these requirements separate from other Python projects.

`fast` checks memory integrity and the source pipeline. `check` runs the test
suite and the repository integrity audits and takes several minutes. A fresh
clone may report optional tests as skipped; see [Quick start](../../CONTRIBUTING.md#quick-start)
for what those skips mean. If a check fails, include the command and its
relevant output in your pull request or issue report.

## 4. Commit and push your branch

Set the commit message to describe the change, then push the branch to your
fork:

```text
git add path/to/the-file-you-changed.md
git commit -m "docs: clarify the setup instructions"
git push -u origin docs/fix-a-typo
```

The `origin` remote in a fresh fork clone points to your fork. You can confirm
that with `git remote -v` before pushing.

## 5. Open a pull request and read CI

On GitHub, open your fork and select **Compare & pull request** for the branch
you pushed. Check that the base repository is
`krapcys1-maker/adaptive-agent-memory-research` and the base branch is `main`.
Explain what changed and list the checks you ran, including any failures or
skips. Link the issue if the change addresses one.

After opening the pull request, read its **Checks** tab. Wait for the checks
to finish, open any failed job, and share the relevant error with the pull
request if you need help. A green local run does not replace the hosted CI
result.

## Commands by operating system

The Git commands above are the same on Windows, macOS, and Linux. Use a
terminal with Git and Python available. The virtual-environment activation
command differs between PowerShell and Bash as shown above. On Windows, use
`python`; on macOS and Linux, use `python3`. The
`core.longpaths` setting above is only needed on Windows if Git reports a
path-length error.

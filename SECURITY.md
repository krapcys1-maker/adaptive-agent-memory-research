# Security policy

This is a research repository. Its memory engine (`tools/project_memory/`) is a local, offline, dependency-free tool that reads and writes files inside the project root you give it; it has no network listener and no authentication layer of its own. Anything that reaches it is trusted as the local user.

## What to report

- A way to make the memory tools read or write outside the given `--root`.
- A committed secret, credential, token or private text (the repository publishes only aggregates of private texts).
- A flaw in a workflow under `.github/workflows/` that lets a pull request run with elevated permissions or exfiltrate secrets.
- A vulnerability in a pinned dependency that the repository's own code reaches.

Weaknesses in the research itself (a leakage path in a benchmark, an attack on the sealed split, a counterexample to a memory guard) are not security reports; open an ordinary issue, they are wanted.

## How to report

Please do **not** post exploit details or live secrets in a public issue. Use GitHub's private vulnerability reporting for this repository (the "Report a vulnerability" button on the Security tab) if it is available. If it is not, open a public issue that says only that you have a security report and no details, and a maintainer will arrange a private channel.

If you find a secret that is already committed, say which file and commit, not the value, and treat the secret as compromised: the owner of the credential must rotate it.

## Supported versions

Only the current `main` branch. There are no release lines.

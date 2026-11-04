# LifeSim portability check — issue 82

CI now runs the pinned golden vectors and ten dependency-light LifeSim suites on `windows-latest` and `macos-latest`, each with Python 3.13 and 3.14. The existing Ubuntu Python 3.11/3.12 full-suite matrix is unchanged. Only pytest is installed for the new jobs; unrelated scientific-package pins cannot prevent this check from running.

The jobs record `python -VV`, the actual platform and CPU architecture before running tests. Windows enables Git long paths on its disposable runner before checkout. Golden digests, generator code, seeds and confirmation epochs are not edited. The tested worlds are the existing test fixtures; no confirmatory experiment is opened.

Local Part A was run on Python 3.12.10, `Windows-11-10.0.26300-SP0`, AMD64. Commands:

```text
python -VV
python -c "import platform; print(platform.platform(), platform.machine())"
python -m pytest -q tests/test_lifesim_rng.py tests/test_lifesim_world.py -k golden
python -m pytest -q tests/test_lifesim_rng.py tests/test_lifesim_world.py tests/test_lifesim_schema.py tests/test_lifesim_vocab.py tests/test_lifesim_scorers.py tests/test_lifesim_queries.py tests/test_lifesim_verbalise.py tests/test_lifesim_channel.py tests/test_lifesim_appraisal.py tests/test_lifesim_integration.py
```

Results and measured job times are recorded in the PR after execution. Passing these fixtures is evidence about deterministic implementation across the tested environments, not evidence that LifeSim's instrument validity gates pass or that a memory design works. Existing failing development gates remain failures until separately repaired and measured.

Local results: `4 passed, 112 deselected in 0.95s`; `728 passed in 67.03s (0:01:07)`. Platform/interpreter evidence: [local-results.json](lifesim-portability-2026-11-04/local-results.json).

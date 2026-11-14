{
 "reproduced": true,
 "summary": "6/6 oczekiwań zgodnych z dokumentacją",
 "expectations": [
  {
   "command": 0,
   "equals": 0.9444,
   "label": "bitemporal exact = 0.944",
   "path": "arms.bitemporal.exact",
   "type": "json_path",
   "observed": 0.9444,
   "ok": true
  },
  {
   "command": 0,
   "equals": 0,
   "label": "bitemporal: 0 przecieków",
   "path": "arms.bitemporal.future_leaks",
   "type": "json_path",
   "observed": 0,
   "ok": true
  },
  {
   "command": 0,
   "equals": 0.3889,
   "label": "one_timestamp exact = 0.389",
   "path": "arms.one_timestamp.exact",
   "type": "json_path",
   "observed": 0.3889,
   "ok": true
  },
  {
   "command": 0,
   "label": "C3 (as_known_at) błędny w ramieniu bitemporal",
   "pattern": "^\\s*bitemporal\\s+C3 as_known_at\\s+expected",
   "type": "regex",
   "observed": "  bitemporal        C3 as_known_at  expected",
   "ok": true
  },
  {
   "command": 1,
   "label": "H2 dev: newest-first 0.200",
   "pattern": "^\\s*newest\\s+0\\.200",
   "type": "regex",
   "observed": "  newest         0.200",
   "ok": true
  },
  {
   "command": 1,
   "label": "H2 dev: resolver 1.000",
   "pattern": "^\\s*resolver\\s+1\\.000",
   "type": "regex",
   "observed": "  resolver       1.000",
   "ok": true
  }
 ],
 "commands": [
  {
   "command": [
    "python",
    "scripts/run_revision_v0.py"
   ],
   "exit_code": 0,
   "timed_out": false,
   "backend": "docker",
   "output_file": "[machine-local path omitted]",
   "tail": "     C6 valid_at     expected owner is alice             got owner is bob\n  one_timestamp     C7 as_known_at  expected None                       got city is Warsaw LEAK\n  one_timestamp     C7 valid_at     expected None                       got city is Warsaw\n  transaction_only  C2 valid_at     expected hair is brown              got hair is green\n  transaction_only  C3 valid_at     expected rate is 5 percent          got rate is 7 percent\n  transaction_only  C3 as_known_at  expected rate is 5 percent          got rate is 7 percent\n  transaction_only  C6 valid_at     expected owner is alice             got owner is bob\n  transaction_only  C7 valid_at     expected None                       got city is Warsaw\n  valid_only        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  valid_only        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  valid_only        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  valid_only        C5 as_known_at  expected status is open             got status is closed LEAK\n  bitemporal        C3 as_known_at  expected rate is 5 percent          got rate is 7 percent\n"
  },
  {
   "command": [
    "python",
    "scripts/run_temporal_resolver_h2.py",
    "--split",
    "dev"
   ],
   "exit_code": 0,
   "timed_out": false,
   "backend": "docker",
   "output_file": "[machine-local path omitted]",
   "tail": "PMLAB-H2-TEMP-E1 — dev, model-free, no API cost\n\n  arm          correct  wrong rec  abstain     CONFLIC  CORRECT   FUTURE  HISTORI  OVERLAP\n  newest         0.200      0.600    0.000       0.000    1.000    0.000    0.000    0.000\n  resolver       1.000      0.000    0.200       1.000    1.000    1.000    1.000    1.000\n"
  }
 ],
 "isolation": "docker"
}

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 7, source file `response.md`, SHA-256 of the original `280a9d689d610c534cd598aee261826fb9949ee4c4d17830368a4ffc651fdc29`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **VERIFIED-REPRODUCTION**. Nothing in it is an approved decision. See `README.md` in this directory.

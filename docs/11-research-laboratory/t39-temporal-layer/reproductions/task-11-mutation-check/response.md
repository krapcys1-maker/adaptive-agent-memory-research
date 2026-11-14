{
 "reproduced": true,
 "summary": "3/3 oczekiwań zgodnych z dokumentacją; warianty: 3",
 "expectations": [
  {
   "command": 0,
   "equals": 0.9444,
   "label": "oryginał: bitemporal exact = 0.944",
   "path": "arms.bitemporal.exact",
   "type": "json_path",
   "observed": 0.9444,
   "ok": true
  },
  {
   "command": 0,
   "label": "oryginał: C3 as_known_at błędny",
   "pattern": "^\\s*bitemporal\\s+C3 as_known_at\\s+expected",
   "type": "regex",
   "observed": "  bitemporal        C3 as_known_at  expected",
   "ok": true
  },
  {
   "absent": true,
   "command": 0,
   "label": "oryginał: valid_only poprawny na C7 as_known_at (twierdzenie Fable o danych)",
   "pattern": "^\\s*valid_only\\s+C7 as_known_at",
   "type": "regex",
   "observed": null,
   "ok": true
  },
  {
   "command": 0,
   "equals": -1,
   "label": "M1: bitemporal exact (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.exact",
   "type": "json_path",
   "variant": "M1",
   "observed": 0.6111,
   "ok": false
  },
  {
   "command": 0,
   "equals": -1,
   "label": "M1: bitemporal future_leaks (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.future_leaks",
   "type": "json_path",
   "variant": "M1",
   "observed": 6,
   "ok": false
  },
  {
   "command": 0,
   "label": "M1: czy bitemporal myli się na C7 as_known_at (obserwacja)",
   "observe": true,
   "pattern": "^\\s*bitemporal\\s+C7 as_known_at",
   "type": "regex",
   "variant": "M1",
   "observed": "  bitemporal        C7 as_known_at",
   "ok": true
  },
  {
   "command": 0,
   "equals": -1,
   "label": "NOFALLBACK: bitemporal exact (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.exact",
   "type": "json_path",
   "variant": "NOFALLBACK",
   "observed": 0.9444,
   "ok": false
  },
  {
   "command": 0,
   "equals": -1,
   "label": "NOFALLBACK: bitemporal future_leaks (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.future_leaks",
   "type": "json_path",
   "variant": "NOFALLBACK",
   "observed": 0,
   "ok": false
  },
  {
   "command": 0,
   "label": "NOFALLBACK: czy bitemporal myli się na C7 as_known_at (obserwacja)",
   "observe": true,
   "pattern": "^\\s*bitemporal\\s+C7 as_known_at",
   "type": "regex",
   "variant": "NOFALLBACK",
   "observed": null,
   "ok": false
  },
  {
   "command": 0,
   "equals": -1,
   "label": "M1_NOFALLBACK: bitemporal exact (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.exact",
   "type": "json_path",
   "variant": "M1_NOFALLBACK",
   "observed": 0.6667,
   "ok": false
  },
  {
   "command": 0,
   "equals": -1,
   "label": "M1_NOFALLBACK: bitemporal future_leaks (obserwacja)",
   "observe": true,
   "path": "arms.bitemporal.future_leaks",
   "type": "json_path",
   "variant": "M1_NOFALLBACK",
   "observed": 4,
   "ok": false
  },
  {
   "command": 0,
   "label": "M1_NOFALLBACK: czy bitemporal myli się na C7 as_known_at (obserwacja)",
   "observe": true,
   "pattern": "^\\s*bitemporal\\s+C7 as_known_at",
   "type": "regex",
   "variant": "M1_NOFALLBACK",
   "observed": null,
   "ok": false
  }
 ],
 "commands": [
  {
   "variant": "base",
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
   "variant": "M1",
   "command": [
    "python",
    "scripts/run_revision_v0.py"
   ],
   "exit_code": 0,
   "timed_out": false,
   "backend": "docker",
   "output_file": "[machine-local path omitted]",
   "tail": "ected owner is alice             got owner is bob\n  transaction_only  C7 valid_at     expected None                       got city is Warsaw\n  valid_only        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  valid_only        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  valid_only        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  valid_only        C5 as_known_at  expected status is open             got status is closed LEAK\n  bitemporal        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  bitemporal        C2 as_known_at  expected hair is brown              got hair is green LEAK\n  bitemporal        C3 as_known_at  expected rate is 5 percent          got rate is 7 percent\n  bitemporal        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  bitemporal        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  bitemporal        C5 as_known_at  expected status is open             got status is closed LEAK\n  bitemporal        C7 as_known_at  expected None                       got city is Warsaw LEAK\n"
  },
  {
   "variant": "NOFALLBACK",
   "command": [
    "python",
    "scripts/run_revision_v0.py"
   ],
   "exit_code": 0,
   "timed_out": false,
   "backend": "docker",
   "output_file": "[machine-local path omitted]",
   "tail": "one_timestamp     C6 valid_at     expected owner is alice             got owner is bob\n  one_timestamp     C7 as_known_at  expected None                       got city is Warsaw LEAK\n  one_timestamp     C7 valid_at     expected None                       got city is Warsaw\n  transaction_only  C2 valid_at     expected hair is brown              got hair is green\n  transaction_only  C3 valid_at     expected rate is 5 percent          got rate is 7 percent\n  transaction_only  C3 as_known_at  expected rate is 5 percent          got rate is 7 percent\n  transaction_only  C6 valid_at     expected owner is alice             got owner is bob\n  transaction_only  C7 valid_at     expected None                       got city is Warsaw\n  valid_only        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  valid_only        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  valid_only        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  valid_only        C5 as_known_at  expected status is open             got status is closed LEAK\n  bitemporal        C3 as_known_at  expected rate is 5 percent          got None\n"
  },
  {
   "variant": "M1_NOFALLBACK",
   "command": [
    "python",
    "scripts/run_revision_v0.py"
   ],
   "exit_code": 0,
   "timed_out": false,
   "backend": "docker",
   "output_file": "[machine-local path omitted]",
   "tail": "ion_only  C3 as_known_at  expected rate is 5 percent          got rate is 7 percent\n  transaction_only  C6 valid_at     expected owner is alice             got owner is bob\n  transaction_only  C7 valid_at     expected None                       got city is Warsaw\n  valid_only        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  valid_only        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  valid_only        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  valid_only        C5 as_known_at  expected status is open             got status is closed LEAK\n  bitemporal        C1 as_known_at  expected hair is brown              got hair is black LEAK\n  bitemporal        C2 as_known_at  expected hair is brown              got None\n  bitemporal        C3 as_known_at  expected rate is 5 percent          got None\n  bitemporal        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK\n  bitemporal        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK\n  bitemporal        C5 as_known_at  expected status is open             got status is closed LEAK\n"
  }
 ],
 "captures": {
  "base/cmd-0": {
   "^\\s*bitemporal\\s+C\\d": [
    "  bitemporal        C3 as_known_at  expected rate is 5 percent          got rate is 7 percent"
   ]
  },
  "M1/cmd-0": {
   "^\\s*bitemporal\\s+C\\d": [
    "  bitemporal        C1 as_known_at  expected hair is brown              got hair is black LEAK",
    "  bitemporal        C2 as_known_at  expected hair is brown              got hair is green LEAK",
    "  bitemporal        C3 as_known_at  expected rate is 5 percent          got rate is 7 percent",
    "  bitemporal        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK",
    "  bitemporal        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK",
    "  bitemporal        C5 as_known_at  expected status is open             got status is closed LEAK",
    "  bitemporal        C7 as_known_at  expected None                       got city is Warsaw LEAK"
   ]
  },
  "NOFALLBACK/cmd-0": {
   "^\\s*bitemporal\\s+C\\d": [
    "  bitemporal        C3 as_known_at  expected rate is 5 percent          got None"
   ]
  },
  "M1_NOFALLBACK/cmd-0": {
   "^\\s*bitemporal\\s+C\\d": [
    "  bitemporal        C1 as_known_at  expected hair is brown              got hair is black LEAK",
    "  bitemporal        C2 as_known_at  expected hair is brown              got None",
    "  bitemporal        C3 as_known_at  expected rate is 5 percent          got None",
    "  bitemporal        C4 as_known_at  expected weight is 60 kg            got weight is 68 kg LEAK",
    "  bitemporal        C4 as_known_at  expected weight is 70 kg            got weight is 68 kg LEAK",
    "  bitemporal        C5 as_known_at  expected status is open             got status is closed LEAK"
   ]
  }
 },
 "variants": [
  {
   "name": "M1",
   "description": "M1 na obecnym resolwerze: as_known_at bez filtra created_at <= T (fallback or-live zostaje)",
   "patches": [
    {
     "file": "scripts/run_revision_v0.py",
     "sha256_before": "d34f90ab1550b78f9ddcb15d3562df256807d83731de231273b83f4bc8cd3113",
     "sha256_after": "b313e8d57b91d5b7e259bb7b671a937db2fb8ab1ab62e450d5246d87469c05f2",
     "diff": "--- scripts/run_revision_v0.py\n+++ scripts/run_revision_v0.py (wariant)\n@@ -104,7 +104,7 @@\n     if kind == \"as_known_at\":\n         # Only records written by T may be consulted. Anything later is future\n         # information and must not influence the answer.\n-        visible = [e for e in chain if e[\"created_at\"] <= at]\n+        visible = list(chain)  # MUTANT M1: bez filtra created_at <= T\n         if not visible:\n             return None\n         successor = _superseded_by(visible)\n"
    }
   ]
  },
  {
   "name": "NOFALLBACK",
   "description": "obecny resolver bez fallbacku or-live (filtr transakcyjny zostaje)",
   "patches": [
    {
     "file": "scripts/run_revision_v0.py",
     "sha256_before": "d34f90ab1550b78f9ddcb15d3562df256807d83731de231273b83f4bc8cd3113",
     "sha256_after": "d5c17b2e764161da1ff24fa5bfd7123e7c2be5b6f6266d45a4a568d9d62081c2",
     "diff": "--- scripts/run_revision_v0.py\n+++ scripts/run_revision_v0.py (wariant)\n@@ -110,7 +110,9 @@\n         successor = _superseded_by(visible)\n         live = [e for e in visible if e[\"id\"] not in successor]\n         # Among what was live then, take the one in force at that time.\n-        in_force = [e for e in live if e[\"valid_from\"] <= at] or live\n+        in_force = [e for e in live if e[\"valid_from\"] <= at]  # WARIANT: bez fallbacku or-live\n+        if not in_force:\n+            return None\n         return max(in_force, key=lambda e: (e[\"valid_from\"], e[\"created_at\"]))[\"title\"]\n \n     visible = chain\n"
    }
   ]
  },
  {
   "name": "M1_NOFALLBACK",
   "description": "M1 na resolwerze bez fallbacku (projekt z planu usuwa fallback)",
   "patches": [
    {
     "file": "scripts/run_revision_v0.py",
     "sha256_before": "d34f90ab1550b78f9ddcb15d3562df256807d83731de231273b83f4bc8cd3113",
     "sha256_after": "b313e8d57b91d5b7e259bb7b671a937db2fb8ab1ab62e450d5246d87469c05f2",
     "diff": "--- scripts/run_revision_v0.py\n+++ scripts/run_revision_v0.py (wariant)\n@@ -104,7 +104,7 @@\n     if kind == \"as_known_at\":\n         # Only records written by T may be consulted. Anything later is future\n         # information and must not influence the answer.\n-        visible = [e for e in chain if e[\"created_at\"] <= at]\n+        visible = list(chain)  # MUTANT M1: bez filtra created_at <= T\n         if not visible:\n             return None\n         successor = _superseded_by(visible)\n"
    },
    {
     "file": "scripts/run_revision_v0.py",
     "sha256_before": "b313e8d57b91d5b7e259bb7b671a937db2fb8ab1ab62e450d5246d87469c05f2",
     "sha256_after": "7db047456d467f5e44d91e6aa50598001003fb8633ff9eb3a858877ab309f402",
     "diff": "--- scripts/run_revision_v0.py\n+++ scripts/run_revision_v0.py (wariant)\n@@ -110,7 +110,9 @@\n         successor = _superseded_by(visible)\n         live = [e for e in visible if e[\"id\"] not in successor]\n         # Among what was live then, take the one in force at that time.\n-        in_force = [e for e in live if e[\"valid_from\"] <= at] or live\n+        in_force = [e for e in live if e[\"valid_from\"] <= at]  # WARIANT: bez fallbacku or-live\n+        if not in_force:\n+            return None\n         return max(in_force, key=lambda e: (e[\"valid_from\"], e[\"created_at\"]))[\"title\"]\n \n     visible = chain\n"
    }
   ]
  }
 ],
 "isolation": "docker"
}

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 11, source file `response.md`, SHA-256 of the original `b7f3062407e27d32ff237aa672ae95eec6a1efe7f602cf862ea5f56db9593c51`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **VERIFIED-REPRODUCTION**. Nothing in it is an approved decision. See `README.md` in this directory.

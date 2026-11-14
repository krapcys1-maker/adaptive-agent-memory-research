"""K1: read-only review of the manual stage T (CHECKLISTA_STARTOWA_K1.md, section D). Reads base/run/ only; writes nothing,
calls nothing. Prints every approval criterion with OK / CHECK / NO and a summary.
Usage: python -I -X utf8 -B tools/review_T.py [--base DIR]   (default D:/aamr-k1-executor/base)"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import k1_lib as kl  # noqa: E402

base = Path(sys.argv[sys.argv.index("--base") + 1]) if "--base" in sys.argv else ROOT / "base"
run = base / "run"
cfg = kl.load_cfg()
res = []


def row(level, name, detail=""):
    res.append(level)
    print(f"[{level:5}] {name}{': ' + str(detail) if detail else ''}")


def rj(name):
    p = run / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


for bad in ("STOPPED.json", "c_d_FAILED.json", "T_ref_FAILED.json"):
    if (run / bad).exists():
        row("NO", f"{bad} present (stage T stopped)", rj(bad) if bad != "T_ref_FAILED.json" else "see file")
T, cd, pc, tm, fr = rj("T.json"), rj("c_d.json"), rj("P_check.json"), rj("T_m.json"), rj("STIM_T_FROZEN.json")
row("OK" if (run / "T_DONE.json").exists() else "NO", "T_DONE.json present")
row("OK" if not (run / "sessions" / "A.jsonl").exists() else "NO", "block A not started")
if T:
    row("OK" if T.get("status") == "done" else "NO", "preflight T.json status done", T.get("reason"))
    row("OK" if T.get("digest_ok") and T.get("gpu_full") else "NO", "model digest and full GPU offload",
        {"digest_ok": T.get("digest_ok"), "gpu_full": T.get("gpu_full"), "ollama": T.get("ollama")})
    row("OK" if all(p.get("ok") and not p.get("thinking_present") for p in T.get("probes", [])) and len(T.get("probes", [])) == 3
        else "NO", "3 transport probes ok, no thinking")
if cd:
    ref = cd.get("ref_check", [])
    row("OK" if len(ref) == 6 and all(x["prompt_eval_count"] == x["reference"] for x in ref) else "NO",
        "T12: 6 reference counts equal NIGHT-2", [(x["task"], x["rep"], x["prompt_eval_count"], x["reference"]) for x in ref])
    lo, hi = cfg["T"]["plausible_tokens_per_char"]
    for d, r in cd["domains"].items():
        rel = r.get("recal", {}).get("T_length_rel", r["T_length_rel"]) if not r["pass"] else r["T_length_rel"]
        row("OK" if r["pass"] or r.get("pass_after_recal") else "NO", f"T-length (b) {d}", f"{100 * rel:+.2f}% (limit +-5%)"
            + ("; after recalibration" if not r["pass"] else ""))
        rp = r.get("recal", {}).get("rho_P", r["rho_P"]) if not r["pass"] else r["rho_P"]
        row("OK" if 0.18 <= rp <= 0.32 else "CHECK", f"prose tokens/char {d}", f"{rp:.4f} (hard guard {lo}-{hi}; expected about 0.20-0.30)")
        c = cd["c_d"][d]
        row("OK" if 0.8 <= c <= 1.5 else "CHECK", f"c_d {d}", f"{c:.4f} (expected about 0.8-1.5)")
if pc:
    row("OK" if pc.get("pass") and pc["L4b_max"] <= cfg["l4b_max_jaccard"] and pc["header_failures"] == 0 and pc["max_len_dev"] <= 12
        else "NO", "P blocks with c_d: header, length, L4b", {k: pc[k] for k in ("blocks", "header_failures", "max_len_dev", "L4b_max")})
row("OK" if fr and cd and kl.sha_file(run / "c_d.json") == fr.get("c_d.json") else "NO", "c_d frozen (STIM_T_FROZEN.json)")
if tm:
    m = tm["mean"]
    g = kl.gate_before_a(sum(1 for _ in open(run / "attempts.jsonl", encoding="utf-8")), m, cfg)
    row("OK" if g["go"] else "NO", "budget gate before A (projection)", {"m": round(m, 2), "need": g["need"], "used": g["used"]})
    row("OK" if m <= 11.1 else "CHECK", "m vs pilot 9.5 (S3 at risk above about 11.1)", round(m, 2))
    proj = g["used"] + m * (444 + 3 * 740)
    row("OK" if proj <= cfg["hard_limit"] else "CHECK", "expected total calls", f"{proj:.0f} of {cfg['hard_limit']}; about {proj * 1.44 / 3600:.1f} h")
n_t = sum(1 for line in open(run / "attempts.jsonl", encoding="utf-8") if '"bucket": "T"' in line) if (run / "attempts.jsonl").exists() else 0
row("OK" if 0 < n_t <= cfg["budgets"]["T"] else "NO", "stage-T calls", f"{n_t} of {cfg['budgets']['T']}")
print("\nSTAGE T: " + ("APPROVABLE (owner decision to continue to block A)" if "NO" not in res and "CHECK" not in res
                       else "LOOK AT CHECK ITEMS (owner decision)" if "NO" not in res else "NOT APPROVABLE (a NO item)"))

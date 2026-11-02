"""LifeSim systems, interface and gates (slice step D1-E).

Generator side: ``scripts/corpus/lifesim`` (package ``corpus.lifesim``). Instrument side: this
package, imported with ``scripts`` on ``sys.path`` as ``lifesim``.

=============  ===============================================================  ======
module         contents                                                         step
=============  ===============================================================  ======
interface      Record, ContextItem, LifeAnswer (from the schema), LifeMemory,   D1-E
               count_units, fill_to_budget, enforce_budget, wrap_arena_adapter,
               ArenaView, run_stream, evidence metrics
systems        BM25 engine and the baseline ladder (Prior, Heuristic, Recency,  D1-E
               RandomK, BM25, BM25Time, Dense, Hybrid, OracleText, OracleStruct,
               OracleStore) and GatedMemory with the retention policies
gates          the X0 gates G-DET ... G-LEAK as pure functions, and the planted D1-E
               artefact fixtures that every gate must fire on
=============  ===============================================================  ======

This ``__init__`` imports nothing on purpose, so that the modules can be imported
independently of each other.

What this package does NOT do: it makes no model call and no network call, reads no clock,
uses neither ``random`` nor ``hash()``, and needs neither numpy nor scipy outside the
statistics of ``gates`` (and an optional fast path of the dense store). It owns no data and
writes no file. It does not run experiments: the runner (``scripts/run_lifesim.py``) is a later
step.
"""

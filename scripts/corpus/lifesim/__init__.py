"""LifeSim: a deterministic synthetic-life generator and memory-benchmark instrument.

Generator id ``lifesim-v0.1``. Design: ``docs/11-research-laboratory/
lifesim-design-panel-digest-2026-11-01.md`` (a design, not a result).

Module ownership (slice D1-A to D1-F)
-------------------------------------
=============  ==========================================================  ======
module         contents                                                    step
=============  ==========================================================  ======
rng            Rng, stream, deterministic math kit, quantiser q            D1-A
schema         every dataclass, TierCfg, JSON round trip, digests, IO      D1-A
vocab          name inventories, answer pools, aliases, closed_vocab       D1-A
appraisal      appraise, surprisal_bits, mood_step                         D1-B
scenes         SCENES, host_facts                                          D1-B
world          build_world, check_world, delete_events, world_digest       D1-B
channel        make_channel, solve_sigma                                   D1-B
verbalise      render, render_question, pad_to_length                      D1-C
queries        build_queries, gold_slow, candidate_pool, ...               D1-D
scorers        normalise, extract_candidates, score, parse_answer, ...     D1-D
=============  ==========================================================  ======

Systems, interface and gates live in the sibling package ``scripts/lifesim/``
(``lifesim.interface``, ``lifesim.systems``, ``lifesim.gates``), not in this one.

What this package does NOT do: it makes no model call and no network call, reads
no clock, uses neither ``random`` nor ``hash()``, and needs neither numpy nor scipy
to generate or to score (they are allowed only in statistics and gate code). It
claims nothing about people: every generator constant is an ASSUMED parameter.

This ``__init__`` imports nothing on purpose, so that the modules can be built and
imported independently of each other.
"""

GENERATOR_ID = "lifesim-v0.1"

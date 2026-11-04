# LifeSim development diagnosis — issues 80 and 81

Tier E descriptive diagnosis, fixed before this execution. No generator, renderer, system, gate, threshold, registration or golden digest is changed. This is not X0 confirmation and does not consume a sealed epoch.

- Use L1 development seeds 5 through 24 and canonical C0: reproduce all sixteen X0 gates at their shipped settings. Record the complete outputs and source digests.
- Diagnose evidence G-TELL with the existing grouped-CV logistic regression and its unchanged bootstrap: six numeric columns individually and together; skeleton hash, channel and n-grams individually; all features minus rare-token share; all minus n-grams; and all features with the text-prefix proxy replacing latent skeleton metadata. These are diagnostic feature ablations, not replacement gate decisions or renderer fixes.
- Report the G-POS evidence/other quartile tables and per-frame counts/positions, including line length and slot count. Do not change padding to force independence.
- Replay B0h chronologically; report accuracy and chance by family/ask, mode-answer concentration per world/group and correct/incorrect answer counts. Inspect how the constant-guess cap is actually normalized. A sample cap is not assumed to imply a held-out blind bound.
- Measure canonical G-FEAS for C0, C0r, C+ and C- at R=.10 and .25. For C0, compare the GS online surprisal weight and the G-TELL rare-token feature against evidence labels, with per-world and pooled AUCs and rank correlations. This is association, not proof of one causal tell; no text repair has been made.
- Check every prefix of the fixed twenty C0 worlds for G-DEPTH, including the four-world prefix. A passing prefix is only an empirical minimum for this fixed sequence, not a guarantee for other seeds or L2. Compare C0 and C0r world, rendered-text and query digests, and trace rehearsal configuration use.

Only existing local dependencies are used. Outputs are written to a new directory, with progress flushed after each stage. Exceptions fail the run; no diagnostic is silently replaced by zero. Preserve negative findings and leave unfulfilled fixes open.

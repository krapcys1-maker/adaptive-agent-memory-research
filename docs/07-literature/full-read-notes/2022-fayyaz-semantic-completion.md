# Fayyaz et al. — A Model of Semantic Completion in Generative Episodic Memory

- Status: full preprint read; extracted; first challenge pass complete; journal-version delta not audited
- Version read: arXiv:2111.13537v1, 26 November 2021, 15 pages
- Canonical journal article: https://doi.org/10.1162/neco_a_01520
- Preprint: https://arxiv.org/abs/2111.13537
- Cached file: `sources/papers/semantic-completion-2111.13537.pdf` (2,492,778 bytes)
- SHA-256: `D598620D95E034BD7A9C724CB19842E7D400A9438E625BD82EFF2E748D238161`

## Research question

Can a compressed partial episodic trace be completed by a learned semantic model, and can that reproduce systematic context-congruent memory errors?

## System, method, and comparison

The model uses a VQ-VAE to compress images to a spatial code-index matrix, an attention mask to retain only a fraction as an episodic trace, and a PixelCNN to complete missing codes at recall. Tests use MNIST digits, synthetic background contexts, Fashion-MNIST generalization, classifiers as recall measures, and a modeled human virtual-apartment experiment.

## Extracted results

- The VQ-VAE representation was reported as about 30 times smaller than the image. Semantic completion improved classification at fixed attention and yielded up to roughly another factor of two in capacity efficiency (Figures 3–4, pp. 6–7; conclusion, p. 11).
- Quantization improved robustness to pixel noise, including a reported transfer test to Fashion-MNIST (Figures 5–7, pp. 7–8).
- In the context simulation, low-fidelity traces were often completed with a plausible but episode-incorrect congruent background. The model reproduced the direction of greater congruent recall and more semantic-than-arbitrary errors for incongruent items (Figures 8–9, pp. 9–10).
- The authors state that attention percentages were tuned and that available degrees of freedom limit explanatory power, although the emergence and ratio of semantic/wrong recalls were not directly tuned (conclusion, pp. 11–12).

## Limitations and challenge pass

- The read artifact is the arXiv preprint; differences from the final Neural Computation version remain to be checked.
- The demonstrations use simple images and synthetic contexts, not language-agent histories.
- The attention selector is primitive, representations are not hierarchically completed, hippocampal storage is absent, and episodes are snapshots rather than sequences (pp. 11–12).
- Classification accuracy rewards plausible category completion and can conceal unsupported detail. A semantically convincing output may be factually wrong about the episode.
- Fit flexibility and a narrow modeled experiment prevent strong causal or biological claims.

## Project relevance

Semantic completion may be useful for a cheap derived representation or generative query aid, but it must never silently overwrite canonical episodes. A reader should expose provenance and distinguish retrieved support from model-filled detail.

## Falsifiable hypothesis

A semantic layer will improve answerability per retrieved token but increase plausible unsupported details on rare/incongruent events. Reject it for autonomous answering unless provenance-aware verification keeps unsupported-detail rate below the preregistered threshold while retaining the efficiency gain.

# Human memory and what machines can take from it: an integrated synthesis (2026-11-02)

Status: literature synthesis written by an editor from four reader reports; architecture-neutral; a map of evidence and a ranked list of tests, not a result and not a specification. Nothing in it is registered as an experiment. A plain-language Polish companion for the lab's owner is [pamiec-czlowieka-i-maszyn.md](../pl/pamiec-czlowieka-i-maszyn.md).

## How to read this document

**Who read what.** Four readers surveyed human memory for the lab. R1: the machinery (storage, chemistry versus electricity, efficiency, forgetting, learning from few examples). R2: emotion, drive and creativity. R3: self, personality, change and breakdown. R4: translation to computing. Reading was almost entirely at abstract level: R1 read two sources at length (Kumaran 2016; Josselyn and Tonegawa 2020, first 100,000 of 241,046 characters), R2 four (Mather 2016; Mattar and Daw 2018; Rouhani and Niv 2021; Park 2023, about 70%), R3 none, R4 one (Titans, first 100k of 136k characters). Numbers that readers took from abstracts through extraction models are leads, not measurements.

**Editor's re-check.** Before writing, the editor chose the ten claims on which the lab implications in section (h) rest most heavily and verified each by an independent fetch of the abstract or full text (Appendix A, claims C1 to C10). The editor added eleven spot checks and confirmed the existence (title, first author, year, venue) of 46 further references through the arXiv and Europe PMC listings. Where a check changed a claim, this text uses the corrected claim and says so. A few figures in the text (in c2, e1, e2 and Appendix A) come from these checks rather than from the readers; they are marked "checked".

**Grades.** ESTABLISHED: replicated or textbook-level (still mostly rodent unless stated). DEBATED: credible evidence on more than one side. SPECULATIVE: a proposal with thin or indirect support. "Inference" marks the editor's own reasoning, which no source states.

**Verification levels in the reference list (section i).** FULL: long section read by a reader this session. ABSTRACT: abstract or review summary read. RECALLED: memory only. EC1: the editor re-fetched the record and confirmed the claim as used here. EC0: the editor confirmed only that the record exists. No mark: not re-checked by the editor.

**Lab sources used second-hand.** [L1] `docs/07-literature/persona-memory-research-digest-2026-11-01.md`; [L2] `docs/11-research-laboratory/lifesim-design-panel-digest-2026-11-01.md` (read by the editor); [L3] `docs/05-benchmarks/human-memory-taxonomy-and-episodic-benchmarks-2026-11-01.md`. Also used: `docs/13-brain-ai-transfer/gap-analysis-v0.md` (the gap analysis), `docs/13-brain-ai-transfer/benchmark-portfolio-v0.md` (the portfolio), `docs/00-project/operating-doctrine.md` (the doctrine) and `memory/CURRENT_STATE.md`. "F1" is the lab's finding that real engagement carried no per-note signal and that 234 published notes held zero callbacks; "E5" and "E6" are the lab's replay and persona experiments.

**Test ids.** Candidate ids from the portfolio are written without their registry prefix (BTA-SEP-001, BTA-TIME-001 and so on) because they are candidates, not registered experiments. The ten hypotheses of section (h) are named HM-1 to HM-10 and are new in this document.

**Already settled in lab documents and not re-argued here:** selective, phase-specific and central-versus-peripheral emotional enhancement, mood congruence, flashbulb confidence, the inverted-U as one arm only, and rejection of literal transfers (`docs/12-interdisciplinary-memory/emotion-salience-synthesis.md`, `docs/12-interdisciplinary-memory/emotion-salience-primary-source-audit-v1.md`, [L2], the gap analysis); retention shaped by the probability of need, and the shapes of forgetting curves ([L2]); a behavioural pattern-separation task ([L3], [L2]); the self-memory system, source-monitoring and false-memory paradigms, and small average effects of life events ([L1], [L2]); the rejected literal equations (hippocampus = vector database, sleep = scheduled summarisation, forgetting = deletion, and the others listed in the gap analysis).

## (a) The picture in one page

**One sentence.** Human memory looks like a set of cooperating control loops whose job is to make later decisions better, not to keep records (Richards and Frankland 2017); emotion, drive, self and creativity are the loops that decide what is kept, what is used and what is recombined.

**How the parts fit.** This is the editor's integration; each step is sourced in sections (b) to (f).

1. *Capture.* Experience changes how strongly neurons drive each other and sometimes their contacts; a sparse set of cells active during an event is bound into an engram. The hippocampus keeps a fast, sparse index and event record; cortex slowly extracts lasting structure, helped by offline replay (Kumaran 2016; Josselyn and Tonegawa 2020).
2. *Gate.* Electrical events (spikes, rhythms) carry information and timing in milliseconds. Chemistry (calcium, enzymes, gene activity, neuromodulators) decides within seconds to hours whether a passing coincidence persists: a synaptic tag lasting seconds becomes lasting change only when a third factor arrives (reward, punishment, surprise, novelty), and later activity can still decide the outcome (Gerstner 2018; Redondo and Morris 2011).
3. *Prioritise.* Arousal systems (amygdala, noradrenaline, cortisol) act, for a limited window, as extra gain on what is already prioritised and as suppression of rivals: vivid centre, holes around it, and confidence that does not track accuracy (Mather 2016, a proposed mechanism; Hirst 2015). Dopamine reads better as a signal of surprise, novelty and wanting than as pleasure (Berridge and Robinson 1998; Schultz 1997).
4. *Drive.* No will centre has been found. Acting looks like three cooperating machines: a thermostat for body set-points, an accountant weighing reward against effort, and an explorer that treats information as reward (R2 synthesis of Keramati and Gutkin 2014, Shenhav 2013, Gottlieb 2013; all normative accounts, thinly tested for cognition).
5. *Recombine.* The machinery that remembers the past also builds imagined futures; creativity looks like memory run generatively, priced in distortion (Schacter 2007, 2011).
6. *Self.* No single seat. Three layers (McAdams and Pals 2006): broad dispositions spread over many circuits (heritability about .40; Vukasovic and Bratko 2015), self-knowledge held as ordinary semantic knowledge, and a life story rebuilt from episodes. They can fail independently, which is what patients show (section f).
7. *Forget.* Forgetting is partly active and partly a loss of access. It weakens the pull of outdated information and the risk of overfitting to particular events (Richards and Frankland 2017); some memories that cannot be recalled are still stored (Josselyn and Tonegawa 2020).

| Grade | Content |
|---|---|
| ESTABLISHED | Synaptic plasticity rules; fast hippocampal and slow cortical learning with replay (mostly rodent); chemical gating of plasticity; energy-driven sparsity (estimates); selective emotional enhancement; double dissociations in patients |
| DEBATED | What an engram does beyond what experiments can trigger; standard versus transformation accounts of consolidation; whether sleep net-downscales or adds synapses; reconsolidation in humans; the dopamine source for hippocampal memory (ventral tegmental area versus locus coeruleus); whether a salience network acts as a switch; where, if anywhere, the self sits in the midline cortex |
| SPECULATIVE | Replay as training of generative models; replay ordered by gain x need as a general selector; neuromodulators as meta-parameters; a dopamine-creativity link; traits as set-points of control loops |

**For the lab.** The gap analysis already states the useful question: does a bounded operation from biological memory solve a measurable agent failure better than a simpler control at the same cost? The survey's answer is a partial yes. What transfers is control functions (what to write, when to promote, how to rank, how to monitor sources, when to demote reversibly), not chemistry and not feelings. Every function that transfers needs a positive control, a preregistered margin and a cost account (the lesson of the lab's E0 experiment).

## (b) Mechanisms: storage, chemistry versus electricity, consolidation and replay

### b1. Where and how a memory is stored

Not in one place. Experience changes synaptic strength, sometimes grows or removes contacts, and binds a small set of cells active during the event.

ESTABLISHED (mostly rodent)
- Long-term potentiation and depression occur at probably every excitatory synapse, by varied mechanisms (textbook point, R1). In cultured rat neurons, spiking within 20 ms after input gave potentiation and within 20 ms before gave depression (Bi and Poo 1998). Calcium activates CaMKII, which localises potentiation and then enlarges the synapse (Lisman 2012). Spines and boutons come and go with experience while gross morphology stays stable (Holtmaat and Svoboda 2009).
- Engrams: allocation favours more excitable or CREB-high neurons; events 30 min to 6 h apart share cells (one amygdala study); ablating the ensemble impairs recall and optogenetic reactivation evokes it; after protein-synthesis blockade, reactivation still recovered the memory 8 days later; there is no compelling cellular evidence in humans (Josselyn and Tonegawa 2020).

DEBATED
- Training-test ensemble overlap is only 10 to 40%; manipulations show what engrams can do, not what they do; protein-synthesis amnesia confounds storage with retrieval (Josselyn and Tonegawa 2020).

### b2. Chemistry versus electricity: two clocks

Both, at different speeds. Electricity carries content and timing; chemistry decides what lasts. The table is the editor's arrangement of R1 and R2 findings.

| Time scale | Event | Mostly carried by | Source |
|---|---|---|---|
| milliseconds | spikes, synaptic transmission | electrical | textbook point |
| about 20 ms | spike-timing window for potentiation versus depression | electrical timing | Bi and Poo 1998 |
| seconds | eligibility trace: a synaptic flag | chemical state (calcium, enzymes) | Gerstner 2018 |
| seconds to minutes | third factor (a burst of dopamine, noradrenaline or acetylcholine, or a specific input) turns the flag into weight change | neuromodulators | Gerstner 2018; Brzosko 2019 |
| minutes to hours | CaMKII, protein synthesis, tagging and capture | molecular | Lisman 2012; Redondo and Morris 2011 |
| hours to days | systems consolidation; hours to days when new material fits a schema | network | Tse 2007; Kumaran 2016 |
| each sleep | replay and net synaptic change | network, structural | Girardeau 2009; Tononi and Cirelli 2014 |

ESTABLISHED (animals): chemistry gates electricity.
- Acetylcholine and monoamines control spike-timing plasticity (Brzosko 2019).
- Activating tyrosine-hydroxylase-positive locus coeruleus neurons in mice mimicked the memory boost of novelty even with the ventral tegmental area silenced, potentiated hippocampal CA1 synapses, and was abolished by blocking D1/D5 dopamine receptors but not adrenoceptors (Takeuchi 2016; checked, Appendix A).
- Seconds-long eligibility traces become weight change only with a third factor such as reward, punishment, surprise or novelty; the review's abstract counts four key experiments in support, its body five papers (Gerstner 2018; C3).
- Tagging and capture: inducing lasting potentiation creates a potential for lasting change, not a commitment; activity before or after induction can decide whether it persists. The authors themselves now revise the original hypothesis, because setting a tag and expressing potentiation can be separated (Redondo and Morris 2011; C3).

DEBATED
- The source of the hippocampal dopamine signal: a ventral tegmental loop (Lisman and Grace 2005) versus the locus coeruleus (Takeuchi 2016).
- Human evidence for all of this is indirect.

### b3. Consolidation and replay

ESTABLISHED (mostly rodent)
- Hippocampal damage hurts recent more than remote memory. Complementary learning systems: fast hippocampal storage plus slow interleaved cortical learning avoids catastrophic interference in models (McClelland 1995; Frankland and Bontempi 2005; Kumaran 2016).
- Ripples replay waking sequences about 20-fold compressed; removing them after training impairs spatial memory (Kumaran 2016; Girardeau 2009).
- Schemas: rats learned flavour-place pairs in a single trial; memory became independent of the hippocampus quickly, but only when an existing schema could absorb it, which argues that schemas play a causal role (Tse 2007; outline confirmed, specific figures dropped, C8).
- Indexing theory has aged well by its own authors' review (Teyler and Rudy 2007; original: Teyler and DiScenna 1986, RECALLED).

DEBATED
- Standard versus transformation accounts: detail stays in the posterior hippocampus while gist and schema move to medial prefrontal cortex (Frankland and Bontempi 2005; Sekeres 2018; Winocur and Moscovitch 2011).
- Timescales shrank from years to hours or days for schema-consistent material. What replay selects is open; replay is reward-biased and serves planning (Kumaran 2016).
- Reconsolidation: in rats, anisomycin after reactivation caused amnesia unless delayed to 6 h (Nader 2000); human evidence is broadly consistent but mixed (Elsey 2018). Do not universalise.
- Sleep: net synaptic downscaling (the axon-spine interface was about 18% smaller after sleep, 6,920 mouse synapses; Tononi and Cirelli 2014; de Vivo 2017) versus spines added on learning-related branches (Yang 2014).

SPECULATIVE
- Replay trains cortical generative models; the hippocampus keeps the unusual details and cortex reconstructs the predictable parts (Spens and Burgess 2024).
- Human replay ordered by gain x need (Mattar and Daw 2018): it reproduces many replay phenomena in simulation, but only in spatial tasks and without emotion, and the authors concede the gain term is unrealistic.

### b4. Separation and completion

Sparse competitive coding in the dentate gyrus separates similar inputs; recurrent autoassociation in CA3 completes partial cues and allows one-trial association (Rolls 2013; textbook-level and largely model-based). A behavioural pattern-separation task is already in the lab ([L3]).

## (c) Efficiency, forgetting and learning from few examples

### c1. Why the brain is efficient

ESTABLISHED (estimates, mostly rodent)
- Signalling dominates the energy bill, and most of that goes to action potentials (47% of signalling energy) and postsynaptic glutamate effects (34%); the authors infer that at most 15% of neurons can be active at once under a distributed code (Attwell and Laughlin 2001; checked).
- Sparse coding of natural images yields receptive fields like those of primary visual cortex (Olshausen and Field 1996). Plasticity costs 4.0 to 11.2% of the energy of fast excitatory transmission (Karbowski 2019, a model estimate).
- Storage and computation share the same synapses (textbook point): a cheap, lossy store.
- In models, synapses with several timescales, where each memory starts in fast variables and drifts into slow ones, reach a capacity that grows almost linearly with the number of synapses instead of with its square root (Benna and Fusi 2016; checked; a model result).

DEBATED: cortex as mostly prediction errors awaits implementation tests (Keller and Mrsic-Flogel 2018); theta-gamma coupling as an ordered multi-item code is a proposal (Lisman and Jensen 2013).

SPECULATIVE: moving plasticity from labile to stable states as an energy saver (Li and van Rossum 2020).

### c2. Why forget

- Memory serves decisions rather than archiving. The authors argue that forgetting weakens the influence of outdated information and prevents overfitting to particular events, which helps generalisation (Richards and Frankland 2017; checked, C4). This is a strong hypothesis, not a measured law. The abstract does not name interference; interference where pattern separation is weak is argued by Hardt, Nader and Nadel (2013).
- Forgetting is partly active: in animals, dopamine from "forgetting cells" acts through Rac1 and cofilin on engram cells (Davis and Zhong 2017); regulated decay mostly in sleep is one account (Hardt 2013), and sleep-time downscaling is one candidate mechanism (Tononi and Cirelli 2014). The accounts are not exclusive.
- Some lost memories remain stored but unreachable (recovery after protein-synthesis blockade, Josselyn and Tonegawa 2020). Forgetting is therefore not deletion (the gap analysis already rejects that equation).
- Flashbulb memories of 11 September 2001: both memory for how people learned of the attack and memory for the event itself fell fast in the first year and then levelled off through year ten, while confidence stayed high (Hirst 2015; checked). The comparison with ordinary memories ("fell at similar rates") belongs to Talarico and Rubin 2003 as reported in [L2], not to Hirst.

### c3. How a few examples can be enough

- If new information fits an existing schema, cortex can take it up in hours to days instead of weeks, and the hippocampus can store a single event in one trial (Tse 2007; Kumaran 2016; Rolls 2013).
- Strong priors let one example constrain a lot. Concepts as probabilistic programs allow one-shot generalisation (Lake 2015; SPECULATIVE as a brain mechanism); dopamine may train prefrontal cortex into a free-standing learner that supplies priors (Wang 2018; SPECULATIVE); plateau-driven plasticity over seconds is a one-trial rule shown for hippocampal place fields (Bittner 2017; generality unknown).
- A special "fast mapping" route that rescues amnesic patients did not hold up: healthy adults show integration with competition and next-day priming (Coutanche 2014), while hippocampal-damage patients were impaired in fast and explicit learning alike (Smith 2014).
- Inference (R1 and the editor): a lossy, prior-heavy store is cheap, and priors make few examples enough. In language models, in-context few-shot prompting (Brown 2020) works because priors sit in the weights; an external memory should retrieve the relevant prior plus a few examples rather than hope to teach from scratch.

## (d) Emotion, neuromodulators, motivation, creativity

### d1. How emotion is tied to memory

ESTABLISHED
- Stress hormones enhance consolidation of arousing events through noradrenergic activation in the amygdala; high circulating levels impair retrieval and working memory (Roozendaal 2008). The amygdala boosts hippocampal and prefrontal operations at encoding, consolidation and retrieval (LaBar and Cabeza 2006).
- Selectivity: arousal helps prioritised material and impairs rivals ("winner take more, loser take less"; collated by Mather 2016 and by the lab audits).
- Surprise and curiosity raise later memory (behaviour solid, neural attribution hypothetical): unsigned outcome prediction errors raised memory for outcome images (beta 0.19, N = 81; 0.09 and 0.11, N = 331 and 354) while signed outcome errors did not; signed errors at the cue did raise memory for cue images (Rouhani and Niv 2021; checked, C2). Curiosity improved memory for targeted and incidental material at immediate and one-day tests (Gruber 2014).

DEBATED
- The mechanism of selectivity. The GANE proposal says glutamate spillover triggers local noradrenaline hotspots that amplify strong signals and let weak ones lapse (Mather 2016; core claim checked, C9). R2 (who read the target article in full) reports that the authors say the brain mechanisms behind priority-by-arousal effects have yet to be tested and that the noradrenaline levels needed for beta-adrenergic potentiation exceed measured ones; the editor could not locate that remark in the abstract or by search, so it stands as reader-reported.
- The inverted-U: rats trained in 19 degrees C water outperformed those at 16 and 25 with trait effects (Salehi 2010); moderate dopamine as best for creativity (Boot 2017). Treat both as one arm, not a premise.

### d2. Which chemical does what

Fast signalling is electrical; chemicals are slow dials on how easily synapses change. Each chemical has several jobs.

| Chemical | What it appears to do | Caveat |
|---|---|---|
| Noradrenaline | amplifies what is already active, quiets the rest | mechanism is the GANE proposal (DEBATED) |
| Cortisol | aids storage soon after an event, hurts retrieval when high (Roozendaal 2008) | animal-heavy |
| Dopamine | surprise (reward prediction error: Schultz 1997), novelty, expected reward and effort; wanting more than liking. In rats with dopamine depleted by up to 99%, hedonic reactions and learning stayed intact; the authors conclude dopamine is needed for wanting, not liking (Berridge and Robinson 1998; checked) | what it encodes is not exclusive: prediction error, wanting, average reward rate setting response vigour (Niv 2007), information value (Gruber 2014) |
| Acetylcholine | high in active waking favours encoding, low in quiet waking and slow-wave sleep favours consolidation (Hasselmo 1999) | DEBATED; acetylcholine as expected and noradrenaline as unexpected uncertainty (Yu and Dayan 2005) |
| Serotonin | mostly aversion and inhibition (Cools 2008) | memory role unclear |
| Oxytocin | no established effect on human memory | intranasal studies are generally underpowered (Walum 2016) |

SPECULATIVE: neuromodulators as meta-parameters (dopamine = prediction error, serotonin = reward timescale, noradrenaline = action randomness, acetylcholine = update speed; Doya 2002). That is vocabulary, not a mapping, and the gap analysis rejects "dopamine = reward or surprise field" as an architecture claim.

### d3. Motivation: where the will to act comes from

DEBATED, with normative accounts that are thinly tested for cognition
- No single will centre. Acting looks like three cooperating machines (R2): a thermostat keeping body states near set-points (homeostatic reinforcement learning, Keramati and Gutkin 2014); an accountant allocating effort by the expected value of control, anchored in dorsal anterior cingulate, striatum and dopamine (Shenhav 2013); an explorer that treats information as reward, with curiosity as learning progress or information gain (Gottlieb 2013).
- Tonic dopamine as the average reward rate that sets response vigour (Niv 2007).
- A salience network (anchored in dorsal anterior cingulate; Seeley 2007) acting as a switch between networks is inference, not a result.

### d4. Creativity

- Imagining the future reuses remembering machinery (Schacter 2007, ABSTRACT). Imagination inflation and gist errors may be by-products of future simulation (Schacter 2011; SPECULATIVE framing).
- Default and executive networks, usually antagonistic, co-activate in creative tasks (Beaty 2016; correlational).
- Positive mood raises creativity slightly over neutral (r = .15 across 102 effect sizes); negative mood does not (r = -.03) (Baas 2008). Incubation helps on average, more for divergent thinking, less after demanding break tasks (Sio and Ormerod 2009).
- Sleep and insight: over twice as many participants gained insight after 8 h of sleep (Wagner 2004), but there was no effect in 77 participants (Schonauer 2018). Mixed.
- Dopamine and creativity is unsettled: the popular eye-blink-rate proxy showed no link to striatal dopamine synthesis in PET (N = 94; Bayes factors favoured absence; van den Bosch 2023).
- SPECULATIVE (the lab's design reading): creativity is offline recombination priced in distortion; the machine version must keep simulated content separate from remembered content (gap analysis rank 1).

## (e) Self, personality and change

### e1. Where personality is stored

Nowhere in particular. Three layers (McAdams and Pals 2006): dispositional traits, characteristic adaptations (goals, values, stances) and life narratives. Amnesic patients keep the middle layer, and a patient with large damage to "self" regions kept self-awareness; there is no single seat (R3).

ESTABLISHED
- Average heritability of personality is .40 (Vukasovic and Bratko 2015; checked: 62 independent effect sizes from over 100,000 participants; twin studies gave higher estimates, .47, than family and adoption studies, .22).
- Brain-behaviour associations are smaller than assumed and need thousands of people (Marek 2022; checked: three datasets totalling about 50,000); a Big Five structural-MRI meta-analysis found no replicable result (Chen and Canli 2022). Lesion, intervention and within-person effects are larger. Lesson (R3): copy lesion dissociations, not brain-trait correlations.
- Identity survives episodic loss, not cleanly. Bilateral medial temporal resections reaching the hippocampus impaired recent memory, severely in two of nine cases (Scoville and Milner 1957). Patient W.J. kept trait self-knowledge through episodic amnesia (Klein 1996); traits, roles and beliefs do not depend on the medial temporal lobe, autobiographical facts partly do (Grilli and Verfaellie 2014). Yet Clive Wearing's amnesia included semantic deficits and a lasting "just awoken" belief that the authors call a delusion (Wilson 1995).
- Transient global amnesia is reversible CA1 hippocampal dysfunction (Bartsch and Deuschl 2010); that identity is spared by the classic criteria is RECALLED.

DEBATED
- Is the self in the cortical midline hubs? Northoff 2006 call them the core of the self; one patient with extensive insular, cingulate, medial prefrontal and temporal damage kept core and extended self-awareness (Philippi 2012).
- Do episodes stay hippocampal? Consolidation as a hand-over to cortex (McClelland 1995) versus transformation, where episodic memories keep needing the hippocampus while gist moves out (Winocur and Moscovitch 2011).

### e2. How personality changes

ESTABLISHED (small on average, uneven between people)
- Rank-order stability rises in early life and levels off in young adulthood, with little evidence of a further rise after 25 (189 studies, N = 178,503); mean-level change across the lifespan is slightly smaller than earlier estimates, and emotional stability rises more consistently than other traits (276 studies, N = 242,542) (Bleidorn 2022; checked, C10). The first-pass phrase "rank among peers stays fairly constant" was therefore too strong.
- Traits predict life events more often than events change traits, with wide individual variation; some effects contradict the idea that mature roles raise maturity (Denissen 2019).
- Deliberate interventions change traits measurably: 207 studies, about 24 weeks on average, an effect of d = .37 (small to moderate), emotional stability most (Roberts 2017; checked, C10; the first-pass word "marked" is dropped).
- Values move coherently, more after life-changing events (Bardi 2009).
- Brain disease changes conduct. All seven patients with bilateral ventromedial prefrontal lesions showed dampened emotion, poor social decisions and lack of insight (Barrash 2000). Patients with frontotemporal dementia misjudge their own personality, early Alzheimer's patients mostly do not (Rankin 2005; 12 and 10 patients). The Phineas Gage legend of lasting change is disputed (Macmillan and Lena 2010), so build on lesion series, not the anecdote.
- Dopamine shifts decision style, not knowledge: off medication, Parkinson's patients learn better from negative outcomes, and medication reverses it (Frank 2004). Motivation and apathy effects were not checked.

DEBATED
- Psilocybin and Openness: raised, and above baseline for over a year in those with mystical experiences; a first test, no effect sizes in the abstract (MacLean 2011).

SPECULATIVE
- Traits as set-points of neuromodulatory control loops (DeYoung 2015, RECALLED); at most indirect support.
- Traits of language models as directions in activation space that move with fine-tuning (Chen 2025): evidence about models, not people.

Inference (editor): the lab's LifeSim character dynamics are authored and every constant is assumed ([L2]). The literature supports their direction (small, bounded, selective, persistent change; rank order largely stable; turning points matter more than ordinary events) but not their magnitudes, so results can be read only as conformance to the authored rules, never as psychology.

## (f) What disorders teach

Each row is a lesion pattern an architecture can try to copy. The lesson column is the editor's reading (inference) of the cited findings. Rows are ordered from stores to control.

| Condition | What breaks | What is spared | Architectural lesson | Source |
|---|---|---|---|---|
| Bilateral medial temporal (hippocampal) amnesia | recent episodic memory | habit and skill learning; trait self-knowledge; old knowledge | a separately lesionable episodic store with its own write path; identity is more than episodes, but not cleanly (see Wearing) | Scoville and Milner 1957; Klein 1996; Grilli and Verfaellie 2014; Wilson 1995 |
| Early hippocampal damage (3 patients; injury at birth, by age 4, at age 9) | everyday episodes | factual knowledge, language, literacy, mainstream schooling | the semantic layer can have write paths that do not run through the episodic store (told and read facts) | Vargha-Khadem 1997 (checked) |
| Amnesia versus Parkinson's disease | amnesia: declarative memory of the training; Parkinson's: learning the probabilistic classification task | amnesia: learning of the task; Parkinson's: memory of the training | a separate habit or procedural system with its own learning rule; test first action, not recall | Knowlton 1996 (checked) |
| Korsakoff versus Huntington disease | Korsakoff: word recognition; Huntington: slow skill learning and recall worse than recognition | Korsakoff: mirror-reading skill; Huntington: recognition | storage-type and retrieval-type failures differ; recognition forks and cue recovery tell them apart | Martone 1984 |
| Alzheimer's disease | recent episodic memory first (entorhinal cortex and hippocampus, later isocortex) | remote memory early; skills | a temporal gradient: a fast store that fails first and a slow store that lasts; a transmitter deficit (cholinergic) is linked to memory loss, but trials disappointed | Braak and Braak 1991 (83 brains); Graham and Hodges 1997; Bartus 1982 |
| Semantic dementia | semantic knowledge | relatively, recent episodes | the reverse pattern: episodic and semantic dissociate both ways, so they deserve separate query families | Graham and Hodges 1997 |
| Ventromedial prefrontal damage; frontotemporal dementia | conduct, insight, accurate self-description | memory content | control, monitoring and the self-model are separable from stored content; a self-report can be wrong, so validate by an informant judging behaviour | Barrash 2000; Rankin 2005 |
| Spontaneous confabulation after anterior communicating artery aneurysm (4 confabulators, 8 non-confabulating patients, 16 controls) | early, rapid, pre-conscious post-retrieval monitoring | non-confabulating patients with similar aneurysms did not show the false-alarm pattern | a monitor separate from the generator; provenance; plausibility checks. In the lab, wrong answers to zero-match questions were plausible, not random [L3] | Gilboa 2006 (checked) |
| Posttraumatic intrusions | context-bound retrieval of vivid sensory memory | ordinary contextual memory | store vivid detail with a pointer to its context; retrieve on context match, never on salience alone. A rival account says the current memory, not the event, drives symptoms | Brewin 2010; Rubin 2008 |
| Epilepsy | long-term retention (accelerated forgetting) and remote memory, missed by standard short-delay tests | short-delay performance | test at long delays; consolidation can fail silently | Butler and Zeman 2008 |
| Parkinson's disease on and off dopaminergic medication | balance of learning from gains versus losses | knowledge | a neuromodulator behaves like a learning-bias parameter; asymmetry of learning from good and bad outcomes is a candidate bounded temperament knob | Frank 2004 |
| Transient global amnesia | forming new memories, for hours | identity (RECALLED); recovers | the write path can fail temporarily; keep an append-only raw log so gaps can be repaired | Bartsch and Deuschl 2010 |
| Dopamine depletion in rats (animal model, not a disease of memory) | wanting (incentive salience) | liking and learning of hedonic value | separate priority ("wanting") from valence and from learning signals in any scoring scheme | Berridge and Robinson 1998 (checked) |

Limits of lesion logic (R3). The separations are real but not clean modules. Lesion data show what the brain needs, within its own architecture; a machine lesion test shows which separations are sufficient to reproduce a pattern, not that the brain uses them. A language model has a fifth store, its weights, that users of an API cannot lesion.

## (g) Translation to computing

### g1. Mechanism to machine analogue, with evidence, cost and verdict

Verdict key. YES: implementable now and measured to help in at least one setting relevant to agents. PARTLY: implementable, but the benefit is shown only in narrow settings, transfers only in part, or is untested for agent memory. NO: not worth copying here, or not implementable today. "Evidence" separates the biology from machine results; machine results are the authors' own unless marked. Costs and losses are the readers' and editor's reasoning (inference) unless a source is given. Test ids HM-n are defined in section (h).

| # | Mechanism (biology) | Machine analogue | Evidence it helps | Cost / loss | Where we could test it | Verdict |
|---|---|---|---|---|---|---|
| 1 | Two-speed store with replay (complementary learning systems) | append-only episode log plus a semantic layer (lessons, profile, traces) rebuilt periodically from the raw episodes with old and new interleaved; for a parametric memory, interleave old items with generated replay | theory and simulation (McClelland 1995; Kumaran 2016). Replay seems necessary when task identity must be inferred, because weight protection fails there (van de Ven and Tolias 2019; checked). Replay of hidden features, with no stored data, reached state of the art on class-incremental CIFAR-100 (van de Ven 2020; checked). For text memories no direct evidence; rewritten lessons trail raw traces [L1] | one consolidation pass per N sessions (model calls) or fine-tuning. An external log has no storage interference, only retrieval crowding, so the rationale shrinks unless memory is parametric; summaries drop detail [L3] | HM-9 (writer-world, interleaved versus chronological rebuild at equal tokens); optional local 7B adapter variant | PARTLY |
| 2 | Hippocampal index over content | sparse entity, time and place keys pointing to raw episodes; LLM-built knowledge graph with Personalized PageRank | HippoRAG: up to 20% better on multi-hop question answering than leading methods, 10 to 30 times cheaper and 6 to 13 times faster than iterative retrieval (Gutierrez 2024; checked). Structure-augmented retrieval is noticeably worse than plain retrieval on basic factual memory; HippoRAG 2 gains 7% on associative tasks (Gutierrez 2025; checked). Lab: association graph as retrieval fusion is closed, negative (E3 measured -0.114 Recall@5; the flaw was seeding expansion from lexical hits) (CURRENT_STATE) | extraction call per item, index upkeep; only extracted entities bind; biology learns index and content jointly and completes by recurrent dynamics, explicit keys are brittle. The abstract maps no component to a brain region; the gain may come from graph plus PageRank, not the framing (R4) | HM-6 (multi-hop SE3 versus single-fact EP1 and IN4, equal budgets) | PARTLY |
| 3 | Associative memory | content-addressable recall by a continuous modern Hopfield network, whose update is transformer attention; attention approximates Kanerva's sparse distributed memory | formal results (Ramsauer 2020; Bricken and Pehlevan 2021, conditions met in GPT-2); 3 of 4 multiple-instance tasks improved | silent on what to store; the learning rule and dynamics differ from the brain | none needed; an analysis tool | YES (as mathematics, not as a design lever) |
| 4 | Pattern separation at write, completion at read | sparse entity- and time-bound keys; a neighbour check at write; false merges charged as errors; completion only through cue-bound retrieval, bridges marked as inference | model-based (Rolls 2013). Lab: a similarity gate tuned to 5% false alarms at store size 8 reached 84 to 100% at 2,048 [L3]; a superseded fact and its replacement sit at the 99.5th percentile of corpus similarity, two pairs at cosine exactly 1.000, so similarity cannot separate versions (STALE-E1, CURRENT_STATE) | one similarity query per write; separation trades against completion (R1) | HM-6; BTA-SEP-001 | PARTLY (cheap to build; benefit unmeasured) |
| 5 | Tag-then-capture (eligibility trace plus third factor) | provisional trace for everything; promotion to durable only when a later consequence signal arrives within a window; otherwise demote | biology (Gerstner 2018; Redondo and Morris 2011; both checked). Machine: none direct; the nearest is replay prioritised by the learner's own error (row 6) | a buffer and a promotion pass. Biological tags are free and local; in software the third factor must be measured, and real engagement carried no per-note signal (F1) | HM-7 (extra arm with a credit channel); BTA-REPLAY-001 is a neighbour | PARTLY |
| 6 | Replay prioritised by learning signal | replay or consolidate items by estimated improvement x probability of use; prioritised experience replay | prioritised replay beat uniform replay on 41 of 49 Atari games (Schaul 2016; checked). Gain x need reproduces replay phenomena in simulation, in spatial tasks only (Mattar and Daw 2018) | gain needs foresight (probe queries plus a usage model); no affect; spatial evidence only (R2) | bench list in (h) (gain x need versus uniform); HM-7 is the nearest ranked test | YES in reinforcement learning; PARTLY for agent memory |
| 7 | Surprise as a write signal | write what the model did not predict. Titans update a memory at test time by the gradient of an associative loss ("surprise") with momentum and a forgetting gate; EM-LLM places event boundaries at Bayesian-surprise peaks | Titans: dropping weight decay raised perplexity from 27.01 to 29.04, dropping momentum to 28.98 (authors, small models, replication unchecked; R4 read the method in full). EM-LLM beats InfLLM and RAG on LongBench and InfiniteBench and correlates with human-perceived events (authors, abstract). Humans: unsigned outcome errors enhance outcome memory (Rouhani and Niv 2021; checked). Curiosity-only agents did well in 54 environments but are fooled by stochastic noise, the noisy-TV problem (Burda 2018) | one scoring pass. Surprise is not need: incidental details are low-surprise yet needed later; model surprisal confuses rare wording with real surprise; F1 predicts a likely null on real notes | HM-4 | PARTLY |
| 8 | Reversible, multi-timescale forgetting | demote, do not delete: a fast-to-slow cascade per item, an accessibility weight in ranking, recovery by a strong cue | capacity near-linear in synapse number in models (Benna and Fusi 2016; checked); transience aids decisions in theory (Richards and Frankland 2017; checked). Machine: MemoryBank lets memories fade or be reinforced (no forgetting ablation in its abstract); FadeMem claims 45% less storage and better multi-hop retrieval (authors, baselines unseen). In LUFY, keeping everything still beat the forgetting pipeline [L1]; in a finite parametric memory, forgetting was the most valuable Titans component | negligible compute. Software storage is cheap, so any gain must show as decision quality; decay is wrong if need is flat and buries sleepers [L2] | HM-3; BTA-TIME-001 is a neighbour | PARTLY (a cost tool today, an unproven accuracy tool) |
| 9 | Schema-gated integration | congruent items go straight to the semantic layer; incongruent ones stay episodic and are interleaved later | Tse 2007 (outline checked); a simulation in Kumaran 2016. Machine: none direct | one check per write; cortical schema is distributed weights, a cluster summary erases exceptions (R1; gap analysis item 7) | bench list (BTA-SCHEMA-001) | PARTLY (untested) |
| 10 | Source and reality monitoring | provenance tags (lived, told, read, imagined, planned, inferred, simulated), read-before-write, abstention, plausibility checks on retrieved items, a monitor separate from the generator | patients (Gilboa 2006; checked); lab gap analysis rank 1; E6: improvised details need write-back, and write-back risks contamination [L2]. No machine ablation of a monitor yet | about one extra call per write or answer, or deterministic rules; a same-family monitor shares the generator's biases; human monitoring is fast and pre-conscious (R3) | HM-5; BTA-SOURCE-001; LifeSim X7 | PARTLY (deterministic parts yes; model-based monitor unproven) |
| 11 | Arousal as priority-conditional gain | boost items already tied to an active goal and damp rivals, in the phase the signal arrives; salience inside the gate, never a channel through it | Mather 2016 (core claim checked). Machine: Generative Agents add LLM-rated importance, but their ablations remove observation, planning and reflection in nested combinations, never importance alone (Park 2023; checked). Lab: emotion-only retention scored 0.201 against 0.300 for random [L1] | one re-rank per query and a goal-relevance field; biology needs prior priority, so arousal alone adds nothing; quiet-critical facts get lost; model ratings measure wording, not consequence (R2) | HM-8; LifeSim X1 | NO for LLM-rated emotion as a retention weight; PARTLY for goal-conditional ranking |
| 12 | Curiosity as learning progress | rank goals or items by expected reduction of the agent's own error | curiosity-only agents (Burda 2018); metacognitive learning-progress predictions guide LLM agents (Gaven 2025, abstract) | a competence predictor and evaluation episodes; no affect or social motive; may collapse onto trivial tasks (R2) | bench list (learning progress versus novelty) | PARTLY |
| 13 | Homeostatic and effort drives | internal variables with set-points (stale facts, open commitments, uncertainty about user goals, token budget); act to cut deviation; scale retrieval depth by the expected value of control | normative accounts only (Keramati and Gutkin 2014; Shenhav 2013). Machine: none | designing the variables; no real stakes; reward hacking (R2) | bench list (effort gating, drive-based upkeep) | PARTLY (control functions yes, feelings no); SPECULATIVE |
| 14 | Sleep: idle-time consolidation and recombination | idle-time jobs that pre-compute inferences, pair distant episodes and store hypotheses tagged as simulated, with provenance | sleep-time compute cut test-time compute about 5-fold at equal accuracy and raised accuracy by up to 13% and 18% on two stateful reasoning benchmarks, working best when queries are predictable from context (Lin 2025; checked). A sleep-like replay phase reduced forgetting in networks (Tadros 2022, secondary) | idle tokens grow with pairs; source confusion turns simulation into false history (gap analysis rank 1) | HM-10 | PARTLY (predictable queries only) |
| 15 | Neuromodulated plasticity | networks that learn to gate their own plasticity | beat standard LSTMs on language modelling at equal parameters (Miconi 2019, authors); untested as agent memory | parametric training; no agent-level evidence | none now | PARTLY (research stage) |
| 16 | Reconsolidation | an evidence-bearing revision (versioned update with provenance and rollback), not an overwrite and not a labile window on retrieval | biology mixed (Nader 2000; Elsey 2018). Lab: a bitemporal resolver was best on historical questions, which is evidence for versioning, not for a labile window (CURRENT_STATE) | versions accumulate; superseded claims can resurface | BTA-RECON-001 | PARTLY as versioning; NO as a labile window |
| 17 | Predictive coding, active inference | training or control by prediction error | predictive coding is mathematically close to backpropagation (Millidge 2021); no LLM-scale evidence and no active-inference benchmark on agent memory was found (R4) | large | none | NO today |
| 18 | Spiking efficiency | neuromorphic hardware | spiking networks match efficient ANNs on energy only at very high spike sparsity, 0.15 to 1.38 spikes per synapse per inference (Dampfhoffer 2023, secondary) | hardware; no benefit for text agents | none | NO |
| 19 | Neurotransmitter chemistry, literal attractor dynamics, forgetting-curve constants as laws, LLM "poignancy" scores | literal copies | R4's list of things probably not worth copying here; the gap analysis rejects the equations | the cost is the collapse of several mechanisms into one label | none | NO |

### g2. Can it be done?

- **Functional mechanisms: a partial yes.** Of the 19 rows, two get a clean yes (attention as associative memory; prioritised replay in reinforcement learning), thirteen a partial yes and four a no (rows with a split verdict are counted by their first clause). Replay, prioritised replay, associative retrieval and surprise-gated writes work in narrow, measured settings (R4).
- **Human-like memory as a whole: no today, and it is unclear that it is needed (R4).** Deployed agents typically keep model weights frozen, so there is nothing to consolidate into and text rewriting is a weak stand-in [L1]; value is not grounded in a body's needs; and agent-memory claims lack positive controls and ablations of the part that carries the biological name.
- **The gap (R4 synthesis).** No deployed agent (1) learns fast and consolidates slowly into one substrate online (Titans-style test-time memory is the nearest research prototype, untested on agent tasks); (2) lets recall rewrite a memory through a gated window; (3) takes salience from a body's needs and modulators before outcomes are known; (4) replays selectively, compressed and recombined; (5) learns locally at low energy.
- **What public agent memories borrow.** Mostly vocabulary: MemGPT and MemoryOS borrow operating-system paging and tiers, A-MEM the Zettelkasten, Mem0 and Zep invoke no biology in their abstracts, Hindsight separates facts, experiences, entity summaries and beliefs, Generative Agents add rated importance, recency decay and reflection (R4; Park 2023 checked: retrieval sums recency with decay factor 0.995 per game hour, importance rated 1 to 10 and relevance, all weights 1; reflection fires when summed importance exceeds 150, about two or three times a day). Reported gains (for example Hindsight 39.0% to 83.6% against full context on LongMemEval with a 20B model; Mem0 +26% relative judge score against OpenAI memory) come from different baselines, budgets and judges; LoCoMo has label defects, LongMemEval is near ceiling, and a plain filesystem agent was claimed to beat Mem0 [L3]. None is a clean test of a biological mechanism.
- **What we would learn from building it (R4).** Exact bridges (a modern Hopfield update is the mathematics of attention); theories become engineering claims (does interleaved replay prevent forgetting? In image benchmarks, yes). But a machine that behaves like memory does not show that the brain works that way, and most bio-named agent memories never switched off the bio-named part, so they teach little about either side. LifeSim tests conformance to authored rules, not psychology [L2].

## (h) Concrete implications for this lab

Everything in this section is the editor's proposal (inference) built on the sourced material above. Nothing is registered. Constraints from the doctrine: bias hard toward Tier E (hours, model-free, existing data); at most two experiments per track may sit in "designed, not executed" (LifeSim X0 and X1 are the two); new registry rows are paused (`memory/CURRENT_STATE.md`); no claim inherits a tier from a neighbour; every result ends in a recorded decision. The five doctrine questions are written Q1 to Q5: Q1 the atomic unit of agent memory; Q2 storage versus retrieval versus reasoning failure; Q3 future utility measured causally; Q4 when to consolidate; Q5 updating without losing provenance, uncertainty or superseded states.

The owner's three examples in the terms of this document:

| Example | LifeSim family | What the literature says it exercises |
|---|---|---|
| Who you are | SE4/SE5 state-as-of identity, CH-R stance versions | the semantic and self-knowledge layer; trait self-knowledge survives episodic loss (Klein 1996), personal facts partly depend on the medial temporal lobe (Grilli and Verfaellie 2014) |
| What I ate for breakfast yesterday | EP1 at 1 day | an episodic record under fan and interference with a flat prior over foods; hippocampus-dependent in people |
| The colour of a car in an article read two weeks ago | IN1 at 14 days | a peripheral detail of a third-party story; survival depends on goal relevance ([L2]) and on remembering that it was read, not lived (source monitoring) |

### h1. The memory module (`scripts/wmb/kernel/memory_kernel.py`, version 0.2.0)

What was read: the live file on branch `revival/kernel-0-2` (still under review) on that branch, 871 lines, standard library only, deterministic, no network or files, and its README; the frozen 0.1.0 (`scripts/wmb/memory_kernel.py`, the instrument of the study WMB-R1) is never edited. Public calls: `build_index`, `retrieve`, `render`, `log_record`, `guard`, `calibrate`, plus `write_back_item`. Items are `kind` (note, reply, comment, event), `origin` (account_history, fiction_autobio, world_knowledge), text, an optional trace (gist, angle, open) and `meta` (including `supersedes`).

**What the literature confirms in the current design (keep).**
1. Thresholded, context-gated injection (at most three items, nothing below the threshold). Arousal acts on content already prioritised by context (Mather 2016); salient memories retrieved without a matching cue are the intrusion pattern of posttraumatic disorders (Brewin 2010); the lab's E5 found that memory shown always is worse where no related earlier piece exists.
2. Raw text always kept beside the optional trace, with a render mode for each. Transformation accounts keep detail in an episodic store while gist moves out (Winocur and Moscovitch 2011; Sekeres 2018), and rewritten lessons trail raw traces [L1].
3. Supersession counted from the replacing item's own date, so a task before it still sees the old item. This is versioned revision rather than overwrite, and the lab found that similarity cannot do this job (STALE-E1).
4. Origin classes, with invented autobiography only for named task types and the class never reaching the prompt. This reflects E6, where the invented past leaked into tasks where it must not appear. See K1 for the tension with source monitoring.
5. The name channel (rare capitalised words pass the gate alone) works like a sparse key, the lexical analogue of separation keys (inference).
6. An injection log of keyed hashes with no text, and a reference guard that is a floor and never a gate. A deterministic checker outside the generator is the architecture the confabulation findings favour (Gilboa 2006).
7. Deterministic and offline. Consolidation, monitoring models and idle-time jobs belong outside it.

**Gaps against the literature.** No provenance beyond three origin classes; no staging between write and durable; no graded accessibility (a hard gate and supersession only); no near-duplicate or changed-attribute detection at write (only explicit `supersedes`); no salience, importance or surprise features, by design; a guard that checks references but not invented details; no consolidation (the trace is supplied by the caller).

**Proposed changes for a 0.3.0.** All are optional profile keys whose defaults reproduce 0.2.0. Locations refer to the 0.2.0 file read on 2026-11-02.

| ID | Change | Basis | Where | Cost and risk | Test |
|---|---|---|---|---|---|
| K1 | Source tags that can reach the prompt on request. `meta["source"]` in lived, told, read, imagined, planned, inferred, simulated, validated at build time. `render(..., sources=True)` prefixes a short tag, enabled only for task types named in a new `source_task_types` profile key (the pattern of `persona_task_types`). `log_record` carries the sources. `guard` gains a flag `imagined_as_experienced`: a first-person past experience whose only support in the injected items has a non-lived source. `write_back_item` tags its output as self-generated | Gilboa 2006; source monitoring ([L2]); gap analysis rank 1; E6 (improvised details need write-back, naive write-back contaminates) | `Item.meta`, `build_index`, `_body` and `render`, `log_record`, `guard`, `write_back_item` | negligible compute, a few prompt tokens per item. Risk: tags can leak and change behaviour as the E6 invented past did, hence task-type gating and an arm with tags stripped | HM-5 |
| K2 | Write staging by versions: provisional, durable, dormant. State is an append-only version using the existing supersession mechanism (`meta["supersedes"]`, `meta["state"]`), written by an outside consolidation job after a consequence signal. A `dormant_factor` multiplies the gate for dormant items so that a strong cue (a name, high BM25) still finds them. Nothing is deleted | tagging and capture (Redondo and Morris 2011; Gerstner 2018); prioritised replay (Schaul 2016); accessibility versus availability (Josselyn and Tonegawa 2020) | the supersession pass in `build_index`; the skip condition in `retrieve`; `log_record` | the outside job plus one multiplication. Risk: the third factor must be measured (F1); a same-text replacement must be shown not to disturb ranks, so read the supersession tests first. A design sketch only | HM-7, HM-3 |
| K3 | An accessibility weight in the rank, never in the gate: an optional multiplier (half-life, floor, refresh on use) applied to `strength` after a candidate has passed, so decay can reorder candidates when more than k pass but cannot hide one that passes | Richards and Frankland 2017; Benna and Fusi 2016; retention follows need ([L2]) | the sort in `retrieve` (strength is set just before `found.sort`) | about ten lines. Risk: a null is expected where need is flat (keep-all beat forgetting in LUFY [L1]); sleepers are protected by construction because the gate is untouched | HM-3 |
| K4 | Near-duplicate and changed-attribute detection at build time. `build_index` records, per item, earlier items above a high lexical similarity with a different date (`index.near`); an optional `diversify_near` shows only the latest of a near-duplicate group; `log_record` reports suppressed counts. Explicit `supersedes` stays the source of truth; the heuristic can also feed a review queue | Rolls 2013 (model); STALE-E1 (similarity cannot separate versions); gates degrade with store size [L3] | after the term-frequency pass in `build_index`; the candidate list in `retrieve` | an inverted-index scan per item, standard library only. Risk: false merges (hiding a genuinely different earlier item), to be charged as errors | HM-6 |
| K5 | Keep salience out of the gate. A design rule: no salience, importance or arousal field passes the gate alone. If one is added to `meta`, it multiplies the `strength` of already-gated candidates, bounded; `log_record` gains `salience_used` | GANE; Brewin 2010; E5; emotion-only retention 0.201 against 0.300 for random [L1] | the `reasons` logic in `retrieve` (name, lexical, embedding stay the only ways in) | nil | HM-8 |
| K6 | Computed novelty and prediction error as logged instrumentation: `meta["novelty"]` = 1 minus the highest lexical similarity to earlier items; when the agent supplies a prediction, signed and unsigned error; logged only, no effect on retrieval by default | Rouhani and Niv 2021; Titans and EM-LLM (authors' claims); F1 predicts a null on real notes | `build_index`, `log_record` | low. Lets HM-4 run on live logs without a reader | HM-4 |
| K7 | Consolidation stays outside; log what was rendered. Trace building, lesson rebuilding and idle-time recombination remain jobs that emit new items with traces; `log_record` gains `rendered_mode` per item so gist-versus-raw effects can be audited; recombination outputs carry `meta["source"] = "simulated"` and are injected only for task types named in `source_task_types` | Winocur and Moscovitch 2011; Lin 2025; gap analysis rank 1 | `render`, `log_record` | nil in the kernel | HM-9, HM-10 |
| K8 | Guard: invented details, not only references. A new floor flag `unsupported_detail`: a first-person factual detail (named entity, date, number) in the output that is absent from the injected items and unhedged. Log it; do not reject (the existing rule for the guard). Measure precision and recall on a hand-written bank, as for the reference patterns | Gilboa 2006 (implausible lures accepted, indiscriminate confidence); E6 (a confident wrong first-job answer 6 of 6 [L2]) | `guard` | patterns only. Risk: false positives on generic text, so build the bank first | HM-5 |

**Do not add:** LLM-rated poignancy or a scalar emotion as a retention gate; deletion as forgetting; a labile overwrite on retrieval; neurotransmitter chemistry; model calls inside the kernel.

**Process.** Land the changes in a version 0.3.0 with a CHANGELOG paragraph, leaving 0.2.0 and the review of it untouched; flip no default until a positive control, a preregistered margin and a cost account exist. K1, K4 and K8 are the cheapest to build and the most tightly tied to the lab's own measured failures.

### h2. The LifeSim generator and experiments X0 to X7

Source: [L2], which is a design, not a result. The literature changes the following. "Timing" respects the work-in-progress limit: arms may be added to X0 and X1 before their preregistration commits; everything else stays a draft.

| Item | What the literature adds | Concrete change | Timing |
|---|---|---|---|
| Generator: schema-congruence dial | schemas speed integration; summaries erase exceptions (Tse 2007; Kumaran 2016; BTA-SCHEMA-001) | tag each new fact as congruent or incongruent with the life's established routines, with quotas. The generator has script-absent probes (FM4, FM5) but no encoding-side dial | v0.2 |
| Generator: source classes earlier | Gilboa 2006; source monitoring | pull the imagined and planned classes of SO2/SO3 (v0.2) into the W2 families so HM-5 has material. `Fact.src` is lived, told or read today | W2 |
| Generator: signed and unsigned prediction error, noisy-TV lines | Rouhani and Niv 2021; Burda 2018 | add `pe_signed` and `pe_unsigned` on goal progress (expected versus realised) beside the unsigned surprisal; hold a signed-only mapping out as M4, leaving M3 as unsigned prediction error only; plant random-surprise lines with no later need and extend the corr(n,k) gate to them | before PREREG-X1 |
| Protocol: a credit channel | tagging and capture needs a consequence signal | after each answered query an arm-specific callback tells the memory which delivered items the reader cited (read-only otherwise, like the write-back arm); the leakage tests (reversed query order, canaries) must cover it | with HM-7 only |
| Config: family-to-store map | dissociations (section f) | map each family to the store that should carry it (log: EP, IN; fact table: SE; later procedural); lesion arms remove one store at query time at equal context budget | X0 |
| Probes: cue recovery at R below 1 | Martone 1984; Knowlton 1996 | for every Day-1 family, a cued or forced-choice probe from the same store for items that failed free recall (EP1 and IN1 already have open-recall and forced-choice forks on separate snapshots) | X0 ladder |
| Dials already sufficient | HM-3 needs need decay and sleepers | delayed-relevance lag (7, 30, 120 days), mundane-decisive mass, update rate and chain depth exist | no change |
| X0 instrument gate (registered, Tier E) | dissociation logic | add the lesion-by-family check (HM-1) and the cue-recovery diagnostic (HM-2) as free ladder outputs; add rank-time decay arms at R = 1 on the need dials (HM-3) | arms |
| X1 value of a feeling-like signal (registered, Tier C by corpus) | Rouhani and Niv 2021; tagging and capture | split the surprise policy GS into signed and unsigned variants and add a noisy-TV cell (HM-4); consider one exploratory capture arm only if the credit channel is accepted (HM-7). Add nothing after the preregistration commit (the lab's looks and seeds rule) | before PREREG-X1 |
| X2 reader calibration (draft) | Gilboa 2006 | no change; keep the confident-wrong rate on abstention items in the calibration reading | none |
| X3 signal with a reader in the loop (draft) | answer-level follow-up | run only if X1 decides in favour of a signal | after X1 |
| X4 black-box product with and without the gate (draft) | HippoRAG results | add a white-box entity-graph arm beside the product so that SE3 against EP1 reads against a known graph baseline (HM-6) | draft |
| X5 narrowing, gist versus raw (draft) | schema congruence | add congruent and incongruent variants, because gist traces are predicted to lose exceptions and peripheral detail | draft |
| X6 bounded, selective, persistent change (draft) | Bleidorn 2022; Denissen 2019; Roberts 2017; McAdams and Pals 2006 | add dissociation arms (minus log, minus budget, minus core) and a rank-order stability readout across at least eight persona profiles (three archetypes plus one held out is too few). The literature supports small, uneven, rank-stable change but not the magnitudes: keep every constant assumed and swept | draft |
| X7 write-back and false memory (draft) | Gilboa 2006 | arms for tags stripped, kept, and a monitor gate (a deterministic rule, then a second reader family), scored by d-prime or AUROC rather than accuracy; plus cue recovery. This is HM-5 | draft |
| Not LifeSim | HM-8 and HM-9 use the E5/NX3 replay notes and the NX2 writer-world | | outside the registry |

What stays: LifeSim's decision that human phenomena are diagnostics and planted controls, never the answer key, and that no tier is called human-level. The survey agrees; it supplies no human data for these lives.

### h3. Ten ranked hypotheses

Ranking method (inference): the doctrine's factors scored 0 to 3 by the editor, namely falsification value (F), moves a doctrine question or unblocks other work (U), and runnable now and cheap (R); ties are broken by the gap analysis rank. These are judgements, not measurements. Cost figures marked "estimate" are the editor's extrapolation from the call counts and CPU figures in [L2]; a pilot must fix them. Margins are suggestions to preregister, as the readers say, and are set against controls, not against literature numbers. Every test needs a positive control (the lesson of E0).

| Rank | Id | Hypothesis | Tier | F | U | R | Total | Moves |
|---|---|---|---|---|---|---|---|---|
| 1 | HM-1 | Stores dissociate | E | 3 | 3 | 3 | 9 | Q1, Q2 |
| 2 | HM-2 | Cue recovery separates storage from retrieval failure | E | 2 | 3 | 3 | 8 | Q2 |
| 3 | HM-3 | Reversible demotion helps only where need decays | E | 3 | 2 | 3 | 8 | Q4, Q5 |
| 4 | HM-4 | Computed surprise adds value beyond relevance, recency and frequency | E | 3 | 2 | 3 | 8 | Q3 |
| 5 | HM-5 | Provenance tags plus a separate monitor cut false-experienced answers without losing hits | E, then C | 3 | 3 | 1 | 7 | Q5, Q2 |
| 6 | HM-6 | A sparse entity- and time-bound index cuts false merges; graph indexes help relational questions only | E | 3 | 2 | 2 | 7 | Q1, Q2 |
| 7 | HM-7 | Consequence-gated promotion beats write-time scoring | E | 2 | 3 | 1 | 6 | Q3, Q4 |
| 8 | HM-8 | Salience without a context gate produces intrusions | E, then C | 2 | 1 | 3 | 6 | Q2 |
| 9 | HM-9 | Interleaved rebuilding beats chronological rebuilding | C | 2 | 2 | 1 | 5 | Q4 |
| 10 | HM-10 | Idle-time consolidation pays only for predictable questions | C | 2 | 2 | 1 | 5 | Q4 |

**HM-1. Stores dissociate.** (R3 H1; Knowlton 1996, Graham and Hodges 1997, Vargha-Khadem 1997.)
- Claim: lesioning a raw log (BM25 plus a date window) hurts EP1, IN1 and IN4 but not SE4/SE5; lesioning a versioned fact table (a rule-based extractor over canonical slot strings) does the reverse; the intact pair beats both.
- Cheapest fair test: the X0 ladder with the two stores and their lesions at equal context budget; oracle_store as positive control; ablated worlds as negative control.
- Measurement: lesion-by-family interaction in gold-in-context@C, cluster bootstrap over worlds.
- Refuted if: no interaction; one store carries every family; ablated worlds not at chance.
- Cost: no paid model calls; under one CPU-hour beyond the X0 ladder (estimate). Slot: X0 arm. Why first: if it fails, the separate-store premise behind K1 and K2 and the family design is unsupported, and the design simplifies.

**HM-2. Cue recovery separates storage from retrieval failure.** (R3 H6; Martone 1984; doctrine Q2.)
- Claim: at retention R below 1, items that failed free recall but are still stored are recovered by a cued or forced-choice probe from the same store at a high rate, while items the retention gate dropped are recovered at floor.
- Cheapest fair test: LifeSim at R in {0.10, 0.25, 1}; probes from the same store; blind and shuffled-context readers (retrieval level: an oracle-store arm) as controls.
- Measurement: recovery rate by class (retained but not retrieved versus dropped); recognition-minus-recall gap.
- Refuted if: equal recovery in both classes, or a blind reader recovers as much (then behavioural probes cannot split storage from retrieval in a black box).
- Cost: no paid model calls; hours. Slot: X0 ladder or X1.

**HM-3. Reversible demotion helps only where need decays.** (R4 H3; R1 H1; Richards and Frankland 2017; Benna and Fusi 2016.)
- Claim: graded, reversible demotion beats keep-everything at equal retrieval budget on current-answer accuracy where facts change and need decays, without losing sleeper-detail recall; it does not beat keep-everything where need is flat.
- Cheapest fair test: an R = 1 ladder with uniform, recency, ACT-R-style ln of summed t^-d (d fitted on development worlds), recency-aware reranking of the full store, and oracle retention, crossed with the need dials (lag 7, 30, 120 days; mundane-decisive mass 0 versus 0.3 to 0.6).
- Measurement: current-answer accuracy, stale-answer rate, sleeper recall (IN4), cost.
- Refuted if: decay beats uniform where need is flat (an artefact); misses the preregistered margin (R4 suggests 0.25 of the pilot headroom) where need decays; recency-aware reranking matches it; or sleeper recall falls more than stale answers do.
- Cost: no paid model calls; CPU hours. Slot: X0 ladder arms or the X1 grid. The lab prior (keep-all won in LUFY [L1]) makes a null likely in some cells, which is itself a decision.

**HM-4. Computed surprise adds value; signed and unsigned differ.** (R2 H1; Rouhani and Niv 2021; Burda 2018.)
- Claim: surprise computed by code from the agent's own predictions, split into signed and unsigned, predicts later need beyond relevance, recency and frequency, and beats rated importance, consequence-only and uncertainty-only arms; planted random-surprise items do not fool it.
- Cheapest fair test: X1 with GS split, a Generative-Agents-style rated-importance arm and a planted noisy-TV cell.
- Measurement: change in AUC for "used within k queries" with a bootstrap interval; SIGNAL as defined in X1.
- Refuted if: the interval includes 0 or the gain is below 0.02 AUC (R2's suggestion), or the gain vanishes when noise items are present. F1 predicts a null on real notes; a clean null is a result.
- Cost: no paid model calls within X1. Slot: X1 arm before the preregistration commit.

**HM-5. Provenance tags plus a separate monitor cut false-experienced answers without losing hits.** (R3 H4; Gilboa 2006; gap analysis rank 1; E6.)
- Claim: stripping provenance raises source errors and false-experienced rates for imagined events without lowering item hits; a monitor gate lowers false alarms more than hits.
- Cheapest fair test: stage 1 (free), a rule-based monitor on LifeSim SO1, SO2 and FM2 at retrieval level, asking whether the lure's evidence is present and whether the tag is sufficient to disambiguate; stage 2, X7 with tags stripped, kept, and a monitor gate (deterministic rule, then a second reader family).
- Measurement: d-prime or AUROC for experienced versus imagined (not accuracy); item hits on EP1; false alarms on FM1 lures.
- Refuted if: no difference with and without tags (the reader ignores them); a gate that cuts hits as much as false alarms (a threshold shift only); a monitor that fails planted-control validation.
- Cost: stage 1 needs no paid model calls; stage 2 is a small paid pilot whose cost is for the maintainers to decide. Slot: after W2, which supplies the SO and FM families.

**HM-6. A sparse entity- and time-bound index cuts false merges; graph indexes help relational questions only.** (R1 H3; R4 H2; Rolls 2013; Gutierrez 2024 and 2025; gap analysis rank 2.)
- Claim: against dense retrieval at equal recall, a sparse entity- and time-bound index reduces false merges mostly in high-similarity lure bins, increasingly as the store grows; an entity graph with Personalized PageRank gains on multi-hop SE3 and loses on single facts (EP1, IN4).
- Cheapest fair test: identical stored, context and ingest budgets for dense, BM25 plus time, and entity graph plus PageRank; graded-lure bins; several store sizes; the control that ablating any hop line must break the item.
- Measurement: false merges against store size; SE3 gain; change on EP1 and IN4.
- Refuted if: no lure-bin by method interaction; recall loss exceeds the false-merge reduction; SE3 gain below +0.05 with an interval including 0 (R4's margin). A drop above 0.05 on EP1 and IN4 would confirm the trade-off.
- Cost: no paid model calls; 1 to 2 CPU-hours (the X1 figure for a comparable grid; dense embeddings dominate). Slot: after W2 (needs SE3); BTA-SEP-001.

**HM-7. Consequence-gated promotion beats write-time scoring.** (R1 H4; R4 H5; Redondo and Morris 2011; Gerstner 2018; Schaul 2016.)
- Claim: a provisional write-all with promotion on a later consequence yields more later-needed items per consolidation call than write-time scoring (rated importance, surprise) at equal durable size, with a dependence on the promotion window.
- Cheapest fair test: an X1 variant with the credit channel: random promotion, write-time promotion, and capture with windows swept.
- Measurement: delayed utility per consolidation call at fixed durable size.
- Refuted if: random or write-time promotion matches it; the window has no effect; or no consequence signal other than engagement can be defined (engagement carried no per-note signal: F1).
- Cost: no paid model calls, but needs the protocol decision. Slot: an exploratory X1 arm only if the credit channel is accepted; otherwise a draft.

**HM-8. Salience without a context gate produces intrusions; the gate flattens the slope.** (R3 H5; Brewin 2010; Mather 2016; E5.)
- Claim: adding a random salience tag with weight 0, 0.25, 0.5 or 1 to retrieval raises the rate at which items are injected into unrelated tasks monotonically when ungated; a context-similarity gate flattens the slope at small cost in grounded callbacks.
- Cheapest fair test: a kernel profile sweep on the E5/NX3 replay notes with tags planted at random (nothing is claimed about real importance); retrieval level first (injection rate on unrelated prompts, free), writer level only if the slope is not flat. E5's always-on arm already reached only 0.18 on unrelated notes (R3).
- Measurement: injection rate and guard-flagged spurious-reference rate on unrelated prompts; grounded callbacks on related ones.
- Refuted if: slope near zero, or the gate loses more callbacks than it prevents intrusions.
- Cost: no paid model calls at retrieval level; the writer step needs a small paid pilot (cost unmeasured). Slot: a kernel test with no registry row.

**HM-9. Interleaved rebuilding beats chronological rebuilding.** (R4 H1; R1 H2; van de Ven and Tolias 2019; van de Ven 2020.)
- Claim: lessons rebuilt from raw sources while interleaving old and new retain earlier rules better than chronological or recency-weighted rebuilds at equal tokens; thresholded raw retrieval may beat all three.
- Cheapest fair test: the NX2 writer-world with two rule blocks (R1 in episodes 1 to 20, R2 in 21 to 40, R1 still scored); controls thresholded raw, oracle and false-lesson. An optional parametric variant: a local 7B model with low-rank adapters, blocked versus interleaved facts, by similarity bin (blocked training must forget first, else void).
- Measurement: R1 retention and R2 acquisition.
- Refuted if: interleaved minus chronological is below 0.1 of pilot headroom (paired interval includes 0), or thresholded raw beats all three.
- Cost: a small paid pilot (cost to be decided); the parametric variant needs no paid calls but GPU hours. Slot: draft (work-in-progress limit).

**HM-10. Idle-time consolidation pays only for predictable questions.** (R4 H4; Lin 2025.)
- Claim: an end-of-day consolidation job helps when queries are predictable from stored context and hurts (omission, hallucination, stale intrusion) when they are not.
- Cheapest fair test: the LifeSim end-of-day hook with arms none, write-time extraction, idle-time rebuild from sources, and a token-matched extra-retrieval control; query predictability varied by anchor mix and family.
- Measurement: net memory gain, omission versus hallucination, stale intrusion.
- Refuted if: no arm-by-predictability interaction (the gain is extra tokens), or the rebuild loses more on IN4 than it gains elsewhere.
- Cost: a small paid pilot (cost to be decided). Slot: draft.

**Not in the top ten (bench), with reasons.** Schema gating (BTA-SCHEMA-001; needs the congruence dial, Tier C). Gain x need replay (R2 H2; Tier E; overlaps HM-7). Learning progress against novelty (R2 H3). Effort gating by expected value of control (R2 H4; Tier C). Tagged recombination (R2 H5; Tier X; source-confusion risk). Drive-based upkeep (R2 H6). Memory-versus-control dissociation (R3 H2; needs the persona harness). Small, selective, rank-stable change (R3 H3; this is X6). The claim that the biology-named parts of public agent memories are decorative (R4 H6; the costliest, so last).

### h4. What this section does not do

It selects no architecture (the doctrine refuses to name one until three independent mechanisms pass at least tier I1). It registers nothing, so the work-in-progress limit is untouched. It does not block or pre-empt the review of kernel 0.2.0. It supplies no human data.

## (i) References, with verification levels

Merged and de-duplicated across the four readers. Level: FULL, ABSTRACT or RECALLED is the highest level any reader reached (a second level is given where readers differed). EC1: the editor re-fetched the record and confirmed the claim as used here. EC0: the editor confirmed only that the record exists with the same first author, year and venue. No mark: not re-checked. A trailing "…" means the reader gave a shortened title. "Secondary" means the reader saw a secondary summary rather than the abstract. Names are written without diacritics.

**A to C**
- Anderson JR, Schooler LJ 1991. Reflections of the environment in memory. Psychol Sci 2:396-408. RECALLED (second-hand via [L2]).
- Attwell D, Laughlin SB 2001. An energy budget for signaling in the grey matter of the brain. J Cereb Blood Flow Metab. ABSTRACT; EC1.
- Baas M, De Dreu CKW, Nijstad BA 2008. A meta-analysis of 25 years of mood-creativity research. Psychol Bull. ABSTRACT.
- Bardi A et al. 2009. The structure of intraindividual value change. J Pers Soc Psychol. ABSTRACT.
- Barrash J, Tranel D, Anderson SW 2000. Acquired personality disturbances associated with bilateral damage to the ventromedial prefrontal region. Dev Neuropsychol. ABSTRACT; EC0.
- Bartsch T, Deuschl G 2010. Transient global amnesia: functional anatomy and clinical implications. Lancet Neurol. ABSTRACT; EC0.
- Bartus RT et al. 1982. The cholinergic hypothesis of geriatric memory dysfunction. Science. ABSTRACT.
- Beaty RE et al. 2016. Creative cognition and brain network dynamics. Trends Cogn Sci. ABSTRACT.
- Behrouz A, Zhong P, Mirrokni V 2025. Titans: learning to memorize at test time. arXiv:2501.00663. FULL (method and experiments); EC0.
- Benna MK, Fusi S 2016. Computational principles of synaptic memory consolidation. Nat Neurosci. ABSTRACT; EC1.
- Berridge KC, Robinson TE 1998. What is the role of dopamine in reward…. Brain Res Rev. ABSTRACT; EC1.
- Bi G, Poo M 1998. Synaptic modifications in cultured hippocampal neurons…. J Neurosci. ABSTRACT.
- Bittner KC et al. 2017. Behavioral time scale synaptic plasticity underlies CA1 place fields. Science. ABSTRACT.
- Bleidorn W et al. 2022. Personality stability and change: a meta-analysis of longitudinal studies. Psychol Bull. ABSTRACT; EC1.
- Boot N et al. 2017. Creative cognition and dopaminergic modulation of fronto-striatal networks. Neurosci Biobehav Rev. ABSTRACT.
- Braak H, Braak E 1991. Neuropathological stageing of Alzheimer-related changes. Acta Neuropathol. ABSTRACT; EC0.
- Brewin CR et al. 2010. Intrusive images in psychological disorders. Psychol Rev. ABSTRACT; EC0.
- Bricken T, Pehlevan C 2021. Attention approximates sparse distributed memory. NeurIPS; arXiv:2111.05498. ABSTRACT; EC0.
- Brown TB et al. 2020. Language models are few-shot learners. arXiv:2005.14165. ABSTRACT; EC0.
- Brzosko Z et al. 2019. Neuromodulation of spike-timing-dependent plasticity…. Neuron. ABSTRACT.
- Burda Y et al. 2018. Large-scale study of curiosity-driven learning. arXiv:1808.04355. ABSTRACT; EC0.
- Buzzega P et al. 2020. Dark experience for general continual learning: a strong, simple baseline. NeurIPS; arXiv:2004.07211. ABSTRACT; EC0.
- Butler CR, Zeman AZ 2008. Recent insights into the impairment of memory in epilepsy…. Brain. ABSTRACT.
- Chen R et al. 2025. Persona vectors: monitoring and controlling character traits in language models. arXiv:2507.21509. ABSTRACT; EC0.
- Chen, Canli 2022. "Nothing to see here": no structural brain differences…. Personality Neuroscience. ABSTRACT.
- Chhikara P et al. 2025. Mem0: building production-ready AI agents with scalable long-term memory. arXiv:2504.19413. ABSTRACT; EC0.
- Cools R, Roberts AC, Robbins TW 2008. Serotoninergic regulation of emotional and behavioural control processes. Trends Cogn Sci. ABSTRACT.
- Coutanche MN et al. 2014. Fast mapping rapidly integrates information into existing memory networks. J Exp Psychol Gen. ABSTRACT.

**D to G**
- Dampfhoffer M et al. 2023. Are SNNs really more energy-efficient than ANNs? An in-depth hardware-aware study. IEEE Trans Emerg Top Comput Intell 7(3):731-741. ABSTRACT (secondary).
- Davis RL, Zhong Y 2017. The biology of forgetting: a perspective. Neuron. ABSTRACT; EC0.
- de Vivo L et al. 2017. Ultrastructural evidence for synaptic scaling across the wake/sleep cycle. Science. ABSTRACT; EC0.
- Denissen JJA et al. 2019. Transactions between life events and personality traits across the adult lifespan. J Pers Soc Psychol. ABSTRACT; EC0.
- DeYoung CG 2015. Cybernetic Big Five Theory. J Res Pers. RECALLED.
- Doya K 2002. Metalearning and neuromodulation. Neural Netw. ABSTRACT.
- Elsey JWB et al. 2018. Human memory reconsolidation: a guiding framework and critical review of the evidence. Psychol Bull. ABSTRACT.
- Fountas Z et al. 2025. Human-inspired episodic memory for infinite context LLMs. ICLR; arXiv:2407.09450. ABSTRACT; EC0.
- Frank MJ, Seeberger LC, O'Reilly RC 2004. By carrot or by stick: cognitive reinforcement learning in parkinsonism. Science. ABSTRACT; EC0.
- Frankland PW, Bontempi B 2005. The organization of recent and remote memories. Nat Rev Neurosci. ABSTRACT; EC0.
- Gaven L et al. 2025. MAGELLAN: metacognitive predictions of learning progress guide autotelic LLM agents…. arXiv:2502.07709. ABSTRACT; EC0.
- Gerstner W et al. 2018. Eligibility traces and plasticity on behavioral time scales: experimental support of neoHebbian three-factor learning rules. Front Neural Circuits. ABSTRACT; EC1.
- Gilboa A, Alain C, Stuss DT, Melo B, Miller S, Moscovitch M 2006. Mechanisms of spontaneous confabulations: a strategic retrieval account. Brain 129:1399-1414. ABSTRACT; EC1.
- Girardeau G et al. 2009. Selective suppression of hippocampal ripples impairs spatial memory. Nat Neurosci. ABSTRACT; EC0.
- Gottlieb J et al. 2013. Information-seeking, curiosity, and attention…. Trends Cogn Sci. ABSTRACT.
- Graham KS, Hodges JR 1997. Differentiating the roles of the hippocampal complex and the neocortex in long-term memory storage…. Neuropsychology. ABSTRACT; EC0.
- Grilli MD, Verfaellie M 2014. Personal semantic memory: insights from neuropsychological research on amnesia. Neuropsychologia. ABSTRACT.
- Gruber MJ, Gelman BD, Ranganath C 2014. States of curiosity modulate hippocampus-dependent learning via the dopaminergic circuit. Neuron. ABSTRACT.
- Gutierrez BJ, Shu Y, Gu Y, Yasunaga M, Su Y 2024. HippoRAG: neurobiologically inspired long-term memory for large language models. NeurIPS; arXiv:2405.14831. ABSTRACT; EC1.
- Gutierrez BJ et al. 2025. From RAG to memory: non-parametric continual learning for large language models. ICML; arXiv:2502.14802. ABSTRACT; EC1.

**H to M**
- Hardt O, Nader K, Nadel L 2013. Decay happens: the role of active forgetting in memory. Trends Cogn Sci. ABSTRACT; EC0.
- Hasselmo ME 1999. Neuromodulation: acetylcholine and memory consolidation. Trends Cogn Sci. ABSTRACT.
- Hassabis D et al. 2017. Neuroscience-inspired artificial intelligence. Neuron 95(2):245-258. ABSTRACT (secondary).
- Hirst W et al. 2015. A ten-year follow-up of a study of memory for the attack of September 11, 2001. J Exp Psychol Gen 144:604-623. ABSTRACT; EC1.
- Holtmaat A, Svoboda K 2009. Experience-dependent structural synaptic plasticity in the mammalian brain. Nat Rev Neurosci. ABSTRACT.
- Johnson MK, Hashtroudi S, Lindsay DS 1993. Source monitoring. Psychol Bull 114:3-28. Not read by a reader; bibliographic, via [L2].
- Josselyn SA, Tonegawa S 2020. Memory engrams: recalling the past and imagining the future. Science 367:eaaw4325. FULL (first 100,000 of 241,046 characters); EC0.
- Kang J et al. 2025. Memory OS of AI agent. arXiv:2506.06326. ABSTRACT; EC0.
- Karbowski J 2019. Metabolic constraints on synaptic learning and memory. J Neurophysiol. ABSTRACT.
- Keller GB, Mrsic-Flogel TD 2018. Predictive processing: a canonical cortical computation. Neuron. ABSTRACT.
- Keramati M, Gutkin B 2014. Homeostatic reinforcement learning for integrating reward collection and physiological stability. eLife. ABSTRACT.
- Kirkpatrick J et al. 2017. Overcoming catastrophic forgetting in neural networks. PNAS; arXiv:1612.00796. ABSTRACT; EC0.
- Klein SB, Loftus J, Kihlstrom JF 1996. Self-knowledge of an amnesic patient: toward a neuropsychology of personality and social psychology. J Exp Psychol Gen. ABSTRACT; EC0.
- Knowlton BJ, Mangels JA, Squire LR 1996. A neostriatal habit learning system in humans. Science 273:1399-1402. ABSTRACT; EC1.
- Kumaran D, Hassabis D, McClelland JL 2016. What learning systems do intelligent agents need? Complementary learning systems theory updated. Trends Cogn Sci 20:512-534. FULL (key sections; R1), ABSTRACT (R4); EC0.
- LaBar KS, Cabeza R 2006. Cognitive neuroscience of emotional memory. Nat Rev Neurosci. ABSTRACT.
- Lake BM et al. 2015. Human-level concept learning through probabilistic program induction. Science. ABSTRACT; EC0.
- Latimer C et al. 2025. Hindsight is 20/20: building agent memory that retains, recalls, and reflects. arXiv:2512.12818. ABSTRACT (search summary); EC0.
- Li HL, van Rossum MCW 2020. Energy efficient synaptic plasticity. eLife. ABSTRACT.
- Lin K et al. 2025. Sleep-time compute: beyond inference scaling at test-time. arXiv:2504.13171. ABSTRACT; EC1.
- Lisman J et al. 2012. Mechanisms of CaMKII action in long-term potentiation. Nat Rev Neurosci. ABSTRACT.
- Lisman JE, Grace AA 2005. The hippocampal-VTA loop…. Neuron. ABSTRACT.
- Lisman JE, Jensen O 2013. The theta-gamma neural code. Neuron. ABSTRACT.
- MacLean KA, Johnson MW, Griffiths RR 2011. Mystical experiences occasioned by the hallucinogen psilocybin…. J Psychopharmacol. ABSTRACT.
- Macmillan M, Lena ML 2010. Rehabilitating Phineas Gage. Neuropsychol Rehabil. ABSTRACT; EC0.
- Marek S et al. 2022. Reproducible brain-wide association studies require thousands of individuals. Nature 603:654-660. ABSTRACT; EC1.
- Martone M et al. 1984. Dissociations between skill learning and verbal recognition in amnesia and dementia. Arch Neurol. ABSTRACT; EC0.
- Mather M, Clewett D, Sakaki M, Harley CW 2016. Norepinephrine ignites local hotspots of neuronal excitation: how arousal amplifies selectivity in perception and memory. Behav Brain Sci (doi 10.1017/S0140525X15000667). FULL (target article; commentaries unread); EC1 (core claim, abstract only).
- Mattar MG, Daw ND 2018. Prioritized memory access explains planning and hippocampal replay. Nat Neurosci. FULL.
- McAdams DP, Pals JL 2006. A new Big Five…. Am Psychol. ABSTRACT; EC0.
- McClelland JL, McNaughton BL, O'Reilly RC 1995. Why there are complementary learning systems in the hippocampus and neocortex…. Psychol Rev 102:419-457. ABSTRACT (R1, R3), RECALLED (R4); EC0.
- Miconi T et al. 2019. Backpropamine: training self-modifying neural networks with differentiable neuromodulated plasticity. ICLR. ABSTRACT.
- Millidge B, Seth A, Buckley CL 2021. Predictive coding: a theoretical and experimental review. arXiv:2107.12979. ABSTRACT; EC0.

**N to Z**
- Nader K, Schafe GE, LeDoux JE 2000. Fear memories require protein synthesis in the amygdala for reconsolidation after retrieval. Nature. ABSTRACT; EC0.
- Niv Y et al. 2007. Tonic dopamine: opportunity costs and the control of response vigor. Psychopharmacology. ABSTRACT.
- Northoff G et al. 2006. Self-referential processing in our brain…. NeuroImage. ABSTRACT.
- Olshausen BA, Field DJ 1996. Emergence of simple-cell receptive field properties by learning a sparse code for natural images. Nature. ABSTRACT.
- Packer C et al. 2023. MemGPT: towards LLMs as operating systems. arXiv:2310.08560. ABSTRACT; EC0.
- Park JS et al. 2023. Generative agents: interactive simulacra of human behavior. arXiv:2304.03442 (UIST). FULL (R2, about 70%); EC1.
- Philippi CL et al. 2012. Preserved self-awareness following extensive bilateral brain damage…. PLoS ONE. ABSTRACT; EC0.
- Ramsauer H et al. 2020. Hopfield networks is all you need. arXiv:2008.02217 (ICLR 2021, RECALLED). ABSTRACT; EC0.
- Rankin KP et al. 2005. Self awareness and personality change in dementia. J Neurol Neurosurg Psychiatry. ABSTRACT; EC0.
- Rasmussen P et al. 2025. Zep: a temporal knowledge graph architecture for agent memory. arXiv:2501.13956. ABSTRACT; EC0.
- Redondo RL, Morris RGM 2011. Making memories last: the synaptic tagging and capture hypothesis. Nat Rev Neurosci 12:17-30. ABSTRACT; EC1.
- Richards BA, Frankland PW 2017. The persistence and transience of memory. Neuron. ABSTRACT; EC1.
- Roberts BW et al. 2017. A systematic review of personality trait change through intervention. Psychol Bull. ABSTRACT; EC1.
- Rolls ET 2013. The mechanisms for pattern completion and pattern separation in the hippocampus. Front Syst Neurosci. ABSTRACT; EC0.
- Roozendaal B et al. 2008. Adrenal stress hormones, amygdala activation, and memory for emotionally arousing experiences. Prog Brain Res. ABSTRACT.
- Rouhani N, Niv Y 2021. Signed and unsigned reward prediction errors dynamically enhance learning and memory. eLife 10:e61077. FULL (main text; appendix unread); EC1.
- Rubin DC, Berntsen D, Bohni MK 2008. A memory-based model of posttraumatic stress disorder…. Psychol Rev. ABSTRACT.
- Rubin DC, Wenzel AE 1996. One hundred years of forgetting. Psychol Rev 103:734-760. RECALLED (second-hand via [L2]).
- Salehi B, Cordero MI, Sandi C 2010. Learning under stress: the inverted-U-shape function revisited. Learn Mem. ABSTRACT.
- Schacter DL, Addis DR, Buckner RL 2007. Remembering the past to imagine the future: the prospective brain. Nat Rev Neurosci. ABSTRACT.
- Schacter DL, Guerin SA, St Jacques PL 2011. Memory distortion: an adaptive perspective. Trends Cogn Sci. ABSTRACT.
- Schaul T et al. 2016. Prioritized experience replay. ICLR; arXiv:1511.05952. ABSTRACT; EC1.
- Schonauer M et al. 2018. Sleep does not promote solving classical insight problems and magic tricks. Front Hum Neurosci. ABSTRACT.
- Schultz W, Dayan P, Montague PR 1997. A neural substrate of prediction and reward. Science. ABSTRACT.
- Scoville WB, Milner B 1957. Loss of recent memory after bilateral hippocampal lesions. J Neurol Neurosurg Psychiatry. ABSTRACT.
- Seeley WW et al. 2007. Dissociable intrinsic connectivity networks for salience processing and executive control. J Neurosci. ABSTRACT.
- Sekeres MJ et al. 2018. The hippocampus and related neocortical structures in memory transformation. Neurosci Lett. ABSTRACT.
- Shenhav A, Botvinick MM, Cohen JD 2013. The expected value of control…. Neuron. ABSTRACT.
- Sio UN, Ormerod TC 2009. Does incubation enhance problem solving? A meta-analytic review. Psychol Bull. ABSTRACT.
- Smith CN et al. 2014. Comparison of explicit and incidental learning strategies in memory-impaired patients. PNAS. ABSTRACT.
- Spens E, Burgess N 2024. A generative model of memory construction and consolidation. Nat Hum Behav. ABSTRACT; EC0.
- Tadros T et al. 2022. Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks. Nat Commun 13:7742. ABSTRACT (secondary).
- Takeuchi T et al. 2016. Locus coeruleus and dopaminergic consolidation of everyday memory. Nature. ABSTRACT; EC1.
- Talarico JM, Rubin DC 2003. Confidence, not consistency, characterizes flashbulb memories. Psychol Sci 14:455-461. Not read by a reader; verified by the LifeSim designers, via [L2].
- Teyler TJ, DiScenna P 1986. The hippocampal memory indexing theory. Behav Neurosci 100:147-154. RECALLED.
- Teyler TJ, Rudy JW 2007. The hippocampal indexing theory and episodic memory: updating the index. Hippocampus. ABSTRACT.
- Tononi G, Cirelli C 2014. Sleep and the price of plasticity…. Neuron. ABSTRACT; EC0.
- Tse D et al. 2007. Schemas and memory consolidation. Science. ABSTRACT; EC1 (outline only).
- van de Ven GM, Tolias AS 2019. Three scenarios for continual learning. arXiv:1904.07734. ABSTRACT; EC1.
- van de Ven GM, Siegelmann HT, Tolias AS 2020. Brain-inspired replay for continual learning with artificial neural networks. Nat Commun 11. ABSTRACT (secondary, R1 and R4); EC1.
- van den Bosch R et al. 2023. Evidence for absence of links between striatal dopamine synthesis capacity and … spontaneous eye-blink rate…. eLife. ABSTRACT.
- Vargha-Khadem F et al. 1997. Differential effects of early hippocampal pathology on episodic and semantic memory. Science. ABSTRACT; EC1.
- Vukasovic T, Bratko D 2015. Heritability of personality: a meta-analysis of behavior genetic studies. Psychol Bull. ABSTRACT; EC1.
- Wagner U et al. 2004. Sleep inspires insight. Nature. ABSTRACT.
- Walum H, Waldman ID, Young LJ 2016. Statistical and methodological considerations for the interpretation of intranasal oxytocin studies. Biol Psychiatry. ABSTRACT.
- Wang JX et al. 2018. Prefrontal cortex as a meta-reinforcement learning system. Nat Neurosci. ABSTRACT.
- Wei L et al. 2026. FadeMem: biologically-inspired forgetting for efficient agent memory. arXiv:2601.18642. ABSTRACT; EC0.
- Wilson BA, Baddeley AD, Kapur N 1995. Dense amnesia in a professional musician…. J Clin Exp Neuropsychol. ABSTRACT; EC0.
- Winocur G, Moscovitch M 2011. Memory transformation and systems consolidation. J Int Neuropsychol Soc. ABSTRACT.
- Xu W et al. 2025. A-MEM: agentic memory for LLM agents. NeurIPS 2025. ABSTRACT.
- Yang G et al. 2014. Sleep promotes branch-specific formation of dendritic spines after learning. Science. ABSTRACT; EC0.
- Yu AJ, Dayan P 2005. Uncertainty, neuromodulation, and attention. Neuron. ABSTRACT.
- Zhong W et al. 2023. MemoryBank: enhancing large language models with long-term memory. arXiv:2305.10250. ABSTRACT; EC0.

**Lab documents** (not literature, used as sources): [L1], [L2], [L3] as defined at the top; the gap analysis; the portfolio; the doctrine; `memory/CURRENT_STATE.md`; `scripts/wmb/kernel/memory_kernel.py` 0.2.0 and its README (read in full by the editor).

## (j) What remains uncertain

**Biology**
- Engrams in humans: no compelling cellular evidence. In rodents the causal role is shown by manipulation, with only 10 to 40% overlap between training and test ensembles and a confound between storage and retrieval in protein-synthesis experiments (Josselyn and Tonegawa 2020).
- Consolidation: standard versus transformation accounts; what replay selects; whether gain x need holds outside spatial tasks (Mattar and Daw 2018 concede the gain term is unrealistic).
- Sleep: downscaling versus addition of synapses. Reconsolidation in humans: broadly consistent but mixed.
- Dopamine: its source for hippocampal memory (ventral tegmental area versus locus coeruleus) and what it encodes. GANE is a proposal; the reader-reported remark that its mechanisms are untested could not be verified (C9).
- Whether a salience network acts as a switch is inference.
- Personality: no single seat (Philippi 2012 versus Northoff 2006). A heritability of .40 is a population average that depends on study design (twin .47, family and adoption .22) and says nothing about how much of one person's personality is genetic. The psilocybin result is one study; the cybernetic account is RECALLED; persona vectors describe language models.
- Sleep and insight is mixed; dopamine and creativity is unsettled; the mechanisms of one-shot learning (plateau-driven plasticity, probabilistic programs, prefrontal meta-learning) are speculative as brain accounts.

**Translation**
- Almost all machine evidence is the authors' own, in narrow settings, with baselines, budgets and judges that differ. Replay results come from image benchmarks; transfer to text memory is inference. HippoRAG's gain may come from graph plus PageRank rather than the biological framing. Titans results are on small models with replication unchecked. One correlation (EM-LLM) is not a mechanism.
- The lab's own evidence has limits: E0 had no positive control; E6 used one persona and one model family; F1 means emotion-like importance cannot be learned from real engagement; the LifeSim numbers quoted in [L2] are properties of a toy generator and every generator constant is assumed.
- For external memory the weights are frozen, so "consolidation into cortex" has no direct counterpart; the stability-plasticity trade-off moves into representations, retrieval and maintenance (gap analysis).

**About this document**
- Reading depth: almost everything is abstract level; numbers passed through extraction models are leads; 21 claims were re-checked and 46 more references confirmed to exist, but 63 of the 134 entries in section (i) carry no EC mark, and the full-text remarks of readers (for example R2's reading of the GANE target article) were not re-verified.
- The ranking scores, the kernel changes and the cost estimates are the editor's judgement and extrapolation (inference). The 0.2.0 kernel is under review and may change.
- Out of scope for the four readers, though prominent in the gap analysis: prospective memory, procedural and implicit memory (first-action transfer), metamemory and the decision layer, and the comparative biology in `docs/10-comparative-biological-memory/`.
- No human data were collected; nothing here says that a benchmark result about a machine tells us how people remember.

## Appendix A. Claim check (2026-11-02)

Method: for each claim the editor fetched the abstract (Europe PMC record or arXiv page) or the full text (eLife, Frontiers, ar5iv) independently of the readers' fetches, and compared the claim with what the page says. Results: **confirmed** (the claim as used here stands), **corrected** (the readers' phrasing needed a change and the text uses the corrected claim), **could not verify**. Full-text fetches were limited to the first 100,000 characters.

### A1. The ten load-bearing claims

| # | Claim as it rests on the readers' reports, and what depends on it | Source and method | Result | What changed |
|---|---|---|---|---|
| C1 | Confabulation after anterior communicating artery aneurysm is a failure of early post-retrieval monitoring: the 4 confabulating patients alone made extra false alarms, accepted implausible lures and were indiscriminately confident, against 8 non-confabulating patients and 16 controls (Gilboa 2006). Depends on: K1, K8, HM-5, row 10 of g1 and the confabulation row of section f | Europe PMC record of Brain 129:1399-1414 (abstract) | confirmed | none. The abstract adds that other deficits (temporal-context and content confusions) may be needed for spontaneous confabulation; the text keeps "necessary and sufficient" for the early monitoring failure only |
| C2 | Unsigned outcome prediction errors raise memory for outcome images (beta 0.19, N = 81; 0.09 and 0.11, N = 331 and 354); signed outcome errors do not (Rouhani and Niv 2021). Depends on: HM-4, K6, the surprise rows | eLife full text (first 100,000 of 170,853 characters) | confirmed (all figures match; signed outcome beta -0.004, -0.05, -0.06, not significant) | scope added: signed errors at the cue did raise cue-image memory in Experiment 2, so "signed errors do nothing" would be wrong; the text says outcome only. The appendix part of the paper was not read |
| C3 | Eligibility traces lasting seconds become lasting change only with a third factor (reward, punishment, surprise, novelty), supported by four key experiments (Gerstner 2018); tagging and capture lets other activity decide persistence (Redondo and Morris 2011). Depends on: K2, HM-7, row 5 of g1 | Frontiers full text (first 100,000 of 192,569 characters); Europe PMC record of Nat Rev Neurosci 12:17-30 | confirmed | two notes added: the review's abstract says four key experiments while its body refers to five papers; Redondo and Morris now revise the original hypothesis because tag setting and expression of potentiation can be dissociated |
| C4 | Memory's purpose is decision making; transience supports flexibility, prevents overfitting and thereby aids generalisation, and reduces interference (Richards and Frankland 2017). Depends on: K3, HM-3, c2 | Europe PMC abstract | corrected | the abstract supports flexibility and generalisation but does not mention interference; the interference account is attributed to Hardt, Nader and Nadel 2013 as the reader had it |
| C5 | Weight protection fails and replay seems necessary in the class-incremental scenario (van de Ven and Tolias 2019); replay of hidden representations without stored data reached state of the art on class-incremental CIFAR-100 (van de Ven 2020). Depends on: row 1 of g1, HM-9 | arXiv abstract; Europe PMC abstract of Nat Commun 11 | confirmed | scope note: image benchmarks only; transfer to text memory is inference. The first abstract names elastic weight consolidation as the failing example and does not report synaptic intelligence separately |
| C6 | HippoRAG: up to 20% better multi-hop question answering than leading methods, 10 to 30 times cheaper and 6 to 13 times faster than iterative retrieval (Gutierrez 2024); structure-augmented retrieval is noticeably worse than standard retrieval on basic factual memory, HippoRAG 2 gains 7% on associative tasks (Gutierrez 2025). Depends on: row 2 of g1, HM-6, K4 | arXiv abstracts of 2405.14831 and 2502.14802 | confirmed | none; both are the authors' own claims, and the first compares with iterative retrieval such as IRCoT |
| C7 | Sleep-time compute cut test-time compute about 5-fold at equal accuracy, raised accuracy by up to 13% (Stateful GSM-Symbolic) and 18% (Stateful AIME), and helped only when queries are predictable from context (Lin 2025). Depends on: row 14 of g1, HM-10 | arXiv abstract of 2504.13171 | corrected | the abstract says it works best when queries are predictable and that predictability correlated strongly with effectiveness; "only when" was too strong and is now "works best when" |
| C8 | An existing schema makes consolidation fast and hippocampus-independent, "within 2 days", with higher cortical plasticity-gene expression "at 80 min" (Tse 2007, as the reader had it with Kumaran 2016). Depends on: row 9 of g1, the schema bench item | Europe PMC abstract | corrected | outline confirmed (one-trial paired-associate learning was integrated and quickly became hippocampus-independent when a schema existed; schemas had a causal role). The 2-day and 80-minute figures are not in the abstract and could not be verified; the 80-minute gene-expression figure may belong to a later paper of the same group (editor's recollection, not checked). Both figures dropped |
| C9 | Arousal amplifies high-priority representations and weakens the rest through glutamate and noradrenaline hotspots (GANE), and the authors say the mechanisms have yet to be tested (Mather 2016). Depends on: K5, HM-8, d1 | Europe PMC abstract; one web search | core confirmed; the "yet to be tested" remark could not be verified | the remark is labelled reader-reported in d1 and (j). The follow-up literature adds behavioural support but the search did not locate the phrase |
| C10 | Rank-order stability levels off in young adulthood and emotional stability rises across life (Bleidorn 2022); interventions change traits within about 24 weeks across 207 studies (Roberts 2017). Depends on: e2, the X6 row | Europe PMC abstracts | confirmed with corrections | stability rose in early life and levelled off in young adulthood with little evidence of a rise after 25 (189 studies, N = 178,503; mean-level change 276 studies, N = 242,542), so "rank among peers stays fairly constant" was too strong; the intervention effect was d = .37, small to moderate, so "marked" was too strong |

Tally of the ten: confirmed 5 (C1, C2, C3, C5, C6); corrected 4 (C4, C7, C8, C10); core confirmed with one sub-claim that could not be verified 1 (C9).

### A2. Spot checks of other claims

| # | Claim | Source and method | Result |
|---|---|---|---|
| S1 | Rats with dopamine depleted by up to 99% kept hedonic reactions and hedonic learning; dopamine is needed for wanting, not liking (Berridge and Robinson 1998) | Europe PMC abstract | confirmed |
| S2 | Flashbulb memories of 11 September fell fast in year one, then levelled off, with confidence staying high (Hirst 2015); the drive reader added that they "faded like ordinary ones" | Europe PMC abstract | corrected: the abstract compares memory for how people learned of the attack with memory for the event, not with everyday memories; the comparison with ordinary memories is Talarico and Rubin 2003 via [L2]. The abstract also gives follow-ups at 11, 25 and 119 months |
| S3 | Average heritability of personality .40 (Vukasovic and Bratko 2015) | Europe PMC abstract | confirmed (62 independent effect sizes, over 100,000 participants; twin .47, family and adoption .22) |
| S4 | Brain-behaviour associations are small and need thousands; about 50,000 people (Marek 2022) | Europe PMC abstract | confirmed |
| S5 | 47% of signalling energy to action potentials, 34% to postsynaptic glutamate effects, at most 15% of neurons active (Attwell and Laughlin 2001) | Europe PMC abstract | confirmed (resting potential 13%, glutamate recycling 3%) |
| S6 | Multi-timescale synapses reach capacity almost linear in synapse number versus square root (Benna and Fusi 2016) | Europe PMC abstract | confirmed (a model result) |
| S7 | Prioritised replay beat uniform replay on 41 of 49 Atari games (Schaul 2016) | arXiv abstract | confirmed |
| S8 | Amnesic patients learned the probabilistic classification task but could not recall training; Parkinson's patients the reverse (Knowlton 1996) | Europe PMC abstract | confirmed |
| S9 | Three patients with early hippocampal pathology lost everyday episodes yet attended mainstream school (Vargha-Khadem 1997) | Europe PMC abstract | confirmed (injury at birth, by age 4, at age 9) |
| S10 | Locus coeruleus activation mimicked novelty-linked memory enhancement via D1/D5 receptors in mice (Takeuchi 2016) | Europe PMC abstract | confirmed (ventral tegmental area silenced; adrenoceptor blockade did not abolish it) |
| S11 | Generative Agents: ablations total 29.89 against 21.21 TrueSkill; retrieval sums recency (decay 0.995), importance and relevance with equal weights; reflection at summed importance above 150, about two or three times a day (Park 2023) | ar5iv full text (first 100,000 of 144,380 characters) | confirmed. Ablations: full 29.89, no reflection 26.88, no reflection and no planning 25.64, human-authored baseline 22.95, no observation, planning or reflection 21.21; importance was never ablated alone |

Tally of the eleven: confirmed 10, corrected 1 (S2).

### A3. Existence of references

Twenty arXiv identifiers were requested from the arXiv listing in one query: all twenty exist with matching titles (the Park 2023 entry is also S11). One identifier the editor guessed for the reader's Miconi 2019 citation returned a different Miconi paper (differentiable plasticity), so the reader's Backpropamine citation stays without an EC mark. Twenty-eight biomedical titles were requested from Europe PMC in two queries (14 mechanisms and engram papers, 14 self and disorder papers): all twenty-eight exist with the stated first author, year and journal. That gives 46 entries marked EC0 in section (i), in addition to the 25 entries marked EC1 by the checks above (134 entries in all). No reader reference was dropped; the RECALLED ones are marked.

# AAM-E1-SIM results

Entries: 540; stream seeds: [1, 2, 3]; analysis days 7 to the end; arms: M0, M1, M2, M3a, M3b.

## Arm means (analysis days)

| arm | n | overlap4 | union_novelty | overlap8 | rep_rate | callback_strict | callback_ext | hook_coverage | words | shown_copy8 | prompt tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | 90 | 0.016 | 0.975 | 0.002 | 0.000 | 0.000 | 0.000 | 0.619 | 124.18 | - | 214 |
| M1 | 90 | 0.077 | 0.876 | 0.029 | 0.044 | 0.078 | 0.056 | 0.607 | 173.67 | 0.031 | 920 |
| M2 | 90 | 0.052 | 0.914 | 0.017 | 0.011 | 0.056 | 0.022 | 0.581 | 173.69 | 0.017 | 793 |
| M3a | 90 | 0.026 | 0.958 | 0.005 | 0.000 | 0.122 | 0.156 | 0.598 | 138.60 | 0.000 | 370 |
| M3b | 90 | 0.031 | 0.951 | 0.007 | 0.000 | 0.100 | 0.122 | 0.622 | 136.26 | 0.000 | 373 |

## Paired contrasts (first minus second), mean [95% bootstrap interval], per-stream means

### overlap4

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 0.060 | [0.045, 0.079] | 0.084 | 1: 0.043, 2: 0.070, 3: 0.069 |
| M2-M0 | 0.036 | [0.024, 0.049] | 0.061 | 1: 0.054, 2: 0.026, 3: 0.027 |
| M3a-M0 | 0.009 | [0.004, 0.014] | 0.025 | 1: 0.010, 2: 0.013, 3: 0.004 |
| M3b-M0 | 0.015 | [0.009, 0.021] | 0.029 | 1: 0.017, 2: 0.011, 3: 0.016 |
| M3a-M2 | -0.026 | [-0.040, -0.015] | 0.059 | 1: -0.043, 2: -0.013, 3: -0.022 |
| M3b-M2 | -0.021 | [-0.034, -0.010] | 0.059 | 1: -0.037, 2: -0.015, 3: -0.011 |
| M3b-M3a | 0.005 | [-0.001, 0.011] | 0.029 | 1: 0.006, 2: -0.002, 3: 0.011 |

### hook_coverage

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | -0.012 | [-0.069, 0.044] | 0.279 | 1: 0.033, 2: 0.012, 3: -0.082 |
| M2-M0 | -0.038 | [-0.096, 0.019] | 0.283 | 1: -0.008, 2: -0.041, 3: -0.066 |
| M3a-M0 | -0.021 | [-0.072, 0.030] | 0.243 | 1: 0.039, 2: -0.008, 3: -0.094 |
| M3b-M0 | 0.002 | [-0.045, 0.051] | 0.234 | 1: 0.049, 2: 0.014, 3: -0.055 |
| M3a-M2 | 0.017 | [-0.036, 0.070] | 0.259 | 1: 0.046, 2: 0.033, 3: -0.028 |
| M3b-M2 | 0.040 | [-0.018, 0.102] | 0.287 | 1: 0.056, 2: 0.054, 3: 0.011 |
| M3b-M3a | 0.023 | [-0.026, 0.076] | 0.244 | 1: 0.010, 2: 0.022, 3: 0.039 |

### callback_ext

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 0.056 | [0.011, 0.111] | 0.230 | 1: 0.000, 2: 0.167, 3: 0.000 |
| M2-M0 | 0.022 | [0.000, 0.056] | 0.148 | 1: 0.033, 2: 0.000, 3: 0.033 |
| M3a-M0 | 0.156 | [0.089, 0.233] | 0.364 | 1: 0.200, 2: 0.100, 3: 0.167 |
| M3b-M0 | 0.122 | [0.056, 0.189] | 0.329 | 1: 0.067, 2: 0.167, 3: 0.133 |
| M3a-M2 | 0.133 | [0.056, 0.222] | 0.402 | 1: 0.167, 2: 0.100, 3: 0.133 |
| M3b-M2 | 0.100 | [0.033, 0.167] | 0.337 | 1: 0.033, 2: 0.167, 3: 0.100 |
| M3b-M3a | -0.033 | [-0.133, 0.067] | 0.507 | 1: -0.133, 2: 0.067, 3: -0.033 |

### union_novelty

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | -0.099 | [-0.121, -0.079] | 0.102 | 1: -0.079, 2: -0.120, 3: -0.098 |
| M2-M0 | -0.061 | [-0.081, -0.044] | 0.089 | 1: -0.088, 2: -0.050, 3: -0.047 |
| M3a-M0 | -0.017 | [-0.025, -0.009] | 0.039 | 1: -0.021, 2: -0.021, 3: -0.009 |
| M3b-M0 | -0.024 | [-0.033, -0.016] | 0.041 | 1: -0.024, 2: -0.018, 3: -0.032 |
| M3a-M2 | 0.044 | [0.028, 0.063] | 0.086 | 1: 0.066, 2: 0.028, 3: 0.038 |
| M3b-M2 | 0.037 | [0.020, 0.057] | 0.087 | 1: 0.064, 2: 0.032, 3: 0.015 |
| M3b-M3a | -0.007 | [-0.016, 0.002] | 0.044 | 1: -0.003, 2: 0.004, 3: -0.023 |

### words

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 49.489 | [41.544, 57.289] | 38.388 | 1: 48.667, 2: 42.033, 3: 57.767 |
| M2-M0 | 49.511 | [42.911, 56.189] | 33.041 | 1: 62.933, 2: 39.167, 3: 46.433 |
| M3a-M0 | 14.422 | [7.667, 21.433] | 33.737 | 1: 10.567, 2: 22.267, 3: 10.433 |
| M3b-M0 | 12.078 | [5.378, 18.756] | 33.046 | 1: 13.100, 2: 13.067, 3: 10.067 |
| M3a-M2 | -35.089 | [-42.878, -27.244] | 37.973 | 1: -52.367, 2: -16.900, 3: -36.000 |
| M3b-M2 | -37.433 | [-44.611, -30.133] | 35.687 | 1: -49.833, 2: -26.100, 3: -36.367 |
| M3b-M3a | -2.344 | [-10.144, 5.333] | 37.617 | 1: 2.533, 2: -9.200, 3: -0.367 |

## Readings stated in advance, applied mechanically

- raw history helps: no
- raw history hurts: no
- traces beat entries: no
- dynamics add: no
- nothing moves: no

## The same day in every arm (stream seed 1, day 30: A study finds standing meetings run shorter but decide less.)

**M0** - notes drawn from days none. *Standing Still* Today I had a standing meeting with my team, and it felt like we were just standing still. The study made sense: standing meetings do indeed cut down on time, but it seems we just stand there and look at each other, hoping something will happen. We clocked in at 15 minutes, maybe, but we didn't accomplish much. Still, it was a change from the usual, so I'll call it a win. Next time, let's try a walking meeting. Maybe...

**M1** - notes drawn from days [27, 28, 29]. *Standing Tall, Sitting Short* Today’s meeting was a standing one, and boy, did it fly by. The usual hour went by in a mere 37 minutes, according to my grandfather’s four-minute slow watch. But we decided less, which is a plus. Piotr, the productivity guru, would have had us tackle the moon and Mars too. I guess sometimes, standing up really does make you more efficient, or maybe it’s just that you’re done sooner. Either way, I’m a fan. Back at th...

**M2** - notes drawn from days [10, 20, 25]. *Standing Still for Progress* Today, I attended a standing meeting. Piotr, my productivity rival, would have been rolling his eyes. "Efficiency! Get to the point!" he might say. But here’s the thing: the meeting did run shorter, just as the study suggested. Yet, did we decide less? Maybe not. We did decide to continue using the standing meeting format, which is a start. I started tracking my steps again, noting that the emphasis on stairs is a go...

**M3a** - notes drawn from days [4, 5, 7]. *Standing Tall, Sitting Short* Today's standing meeting was a revelation. The usual suspects gathered, but this time, no one pulled out their laptops or tablets, no one muttered about the coffee machine being broken. We just stood there, talking, and somehow, we covered more ground than usual. The clock ticked, but so did our energy levels, keeping us on our toes. Four minutes after the appointed hour, we adjourned, none the worse for wear. Perhap...

**M3b** - notes drawn from days [14, 20, 24]. *Standing Tall, Sitting Short* Today's meeting was a standing one, and sure enough, it was over before I could say “coffee break.” But as they say, brevity is the soul of wit, or at least, the soul of a productive meeting. The study showing that standing meetings run shorter but decide less didn't surprise me. I've been trying to cut down on my sitting time anyway, so this just gave me a good excuse. I wonder if this will lead to more effective di...


# AAM-E1-SIM results

Entries: 1080; stream seeds: [4, 5, 6, 7, 8, 9]; analysis days 7 to the end; arms: M0, M1, M2, M3a, M3b.

## Arm means (analysis days)

| arm | n | overlap4 | union_novelty | overlap8 | rep_rate | callback_strict | callback_ext | hook_coverage | words | shown_copy8 | prompt tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | 180 | 0.049 | 0.926 | 0.017 | 0.000 | 0.161 | 0.011 | 0.663 | 133.46 | - | 202 |
| M1 | 180 | 0.045 | 0.941 | 0.011 | 0.000 | 0.006 | 0.039 | 0.745 | 139.12 | 0.011 | 775 |
| M2 | 180 | 0.034 | 0.953 | 0.007 | 0.000 | 0.178 | 0.050 | 0.714 | 139.19 | 0.005 | 708 |
| M3a | 180 | 0.040 | 0.942 | 0.011 | 0.000 | 0.039 | 0.089 | 0.716 | 136.79 | 0.000 | 379 |
| M3b | 180 | 0.035 | 0.947 | 0.008 | 0.000 | 0.106 | 0.083 | 0.676 | 135.43 | 0.000 | 379 |

## Paired contrasts (first minus second), mean [95% bootstrap interval], per-stream means

### overlap4

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | -0.004 | [-0.010, 0.002] | 0.039 | 4: 0.031, 5: -0.024, 6: -0.031, 7: 0.021, 8: -0.015, 9: -0.007 |
| M2-M0 | -0.015 | [-0.020, -0.011] | 0.030 | 4: -0.011, 5: -0.018, 6: -0.025, 7: -0.005, 8: -0.017, 9: -0.017 |
| M3a-M0 | -0.009 | [-0.014, -0.004] | 0.034 | 4: -0.008, 5: -0.014, 6: -0.013, 7: 0.007, 8: -0.021, 9: -0.004 |
| M3b-M0 | -0.014 | [-0.019, -0.009] | 0.032 | 4: -0.015, 5: -0.011, 6: -0.020, 7: -0.005, 8: -0.025, 9: -0.007 |
| M3a-M2 | 0.006 | [0.002, 0.011] | 0.028 | 4: 0.003, 5: 0.004, 6: 0.011, 7: 0.012, 8: -0.004, 9: 0.013 |
| M3b-M2 | 0.002 | [-0.002, 0.006] | 0.028 | 4: -0.003, 5: 0.007, 6: 0.004, 7: 0.000, 8: -0.008, 9: 0.010 |
| M3b-M3a | -0.005 | [-0.009, -0.001] | 0.030 | 4: -0.006, 5: 0.003, 6: -0.007, 7: -0.012, 8: -0.004, 9: -0.003 |

### hook_coverage

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 0.082 | [0.053, 0.110] | 0.197 | 4: 0.079, 5: 0.062, 6: 0.081, 7: 0.120, 8: 0.116, 9: 0.033 |
| M2-M0 | 0.051 | [0.024, 0.079] | 0.188 | 4: 0.072, 5: 0.002, 6: 0.070, 7: 0.067, 8: 0.104, 9: -0.009 |
| M3a-M0 | 0.053 | [0.024, 0.083] | 0.204 | 4: 0.064, 5: 0.036, 6: 0.052, 7: 0.076, 8: 0.110, 9: -0.020 |
| M3b-M0 | 0.013 | [-0.017, 0.043] | 0.208 | 4: 0.022, 5: -0.073, 6: 0.053, 7: 0.069, 8: 0.044, 9: -0.037 |
| M3a-M2 | 0.002 | [-0.023, 0.026] | 0.168 | 4: -0.008, 5: 0.035, 6: -0.018, 7: 0.009, 8: 0.007, 9: -0.011 |
| M3b-M2 | -0.038 | [-0.068, -0.009] | 0.203 | 4: -0.050, 5: -0.075, 6: -0.017, 7: 0.002, 8: -0.060, 9: -0.028 |
| M3b-M3a | -0.040 | [-0.070, -0.011] | 0.201 | 4: -0.042, 5: -0.109, 6: 0.002, 7: -0.007, 8: -0.067, 9: -0.018 |

### callback_ext

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 0.028 | [-0.006, 0.061] | 0.222 | 4: 0.000, 5: 0.133, 6: -0.033, 7: 0.000, 8: 0.033, 9: 0.033 |
| M2-M0 | 0.039 | [0.006, 0.078] | 0.245 | 4: 0.000, 5: 0.033, 6: 0.100, 7: 0.000, 8: 0.133, 9: -0.033 |
| M3a-M0 | 0.078 | [0.033, 0.122] | 0.307 | 4: 0.100, 5: 0.167, 6: 0.067, 7: 0.133, 8: 0.033, 9: -0.033 |
| M3b-M0 | 0.072 | [0.039, 0.111] | 0.260 | 4: 0.067, 5: 0.033, 6: 0.000, 7: 0.133, 8: 0.067, 9: 0.133 |
| M3a-M2 | 0.039 | [-0.011, 0.089] | 0.340 | 4: 0.100, 5: 0.133, 6: -0.033, 7: 0.133, 8: -0.100, 9: 0.000 |
| M3b-M2 | 0.033 | [-0.017, 0.083] | 0.349 | 4: 0.067, 5: 0.000, 6: -0.100, 7: 0.133, 8: -0.067, 9: 0.167 |
| M3b-M3a | -0.006 | [-0.061, 0.050] | 0.388 | 4: -0.033, 5: -0.133, 6: -0.067, 7: 0.000, 8: 0.033, 9: 0.167 |

### union_novelty

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 0.015 | [0.008, 0.023] | 0.052 | 4: -0.022, 5: 0.035, 6: 0.049, 7: -0.022, 8: 0.022, 9: 0.031 |
| M2-M0 | 0.027 | [0.021, 0.033] | 0.042 | 4: 0.022, 5: 0.026, 6: 0.039, 7: 0.016, 8: 0.021, 9: 0.038 |
| M3a-M0 | 0.016 | [0.009, 0.023] | 0.047 | 4: 0.008, 5: 0.021, 6: 0.032, 7: -0.003, 8: 0.021, 9: 0.018 |
| M3b-M0 | 0.022 | [0.015, 0.028] | 0.045 | 4: 0.021, 5: 0.014, 6: 0.032, 7: 0.009, 8: 0.031, 9: 0.025 |
| M3a-M2 | -0.011 | [-0.017, -0.005] | 0.040 | 4: -0.014, 5: -0.005, 6: -0.007, 7: -0.019, 8: 0.000, 9: -0.020 |
| M3b-M2 | -0.005 | [-0.011, 0.000] | 0.039 | 4: -0.002, 5: -0.013, 6: -0.007, 7: -0.007, 8: 0.010, 9: -0.013 |
| M3b-M3a | 0.006 | [-0.001, 0.012] | 0.043 | 4: 0.013, 5: -0.008, 6: 0.000, 7: 0.011, 8: 0.010, 9: 0.007 |

### words

| contrast | mean | interval | sd of pairs | per stream |
|---|---|---|---|---|
| M1-M0 | 5.661 | [3.844, 7.483] | 12.604 | 4: 4.033, 5: 4.367, 6: 4.533, 7: 11.700, 8: 5.167, 9: 4.167 |
| M2-M0 | 5.733 | [3.994, 7.511] | 12.222 | 4: 7.567, 5: 3.633, 6: 4.167, 7: 3.633, 8: 14.367, 9: 1.033 |
| M3a-M0 | 3.339 | [1.600, 5.056] | 11.969 | 4: 6.067, 5: 2.200, 6: 3.000, 7: 3.400, 8: 4.133, 9: 1.233 |
| M3b-M0 | 1.972 | [0.378, 3.611] | 11.199 | 4: 5.267, 5: 2.367, 6: 2.167, 7: 1.467, 8: 0.767, 9: -0.200 |
| M3a-M2 | -2.394 | [-4.361, -0.389] | 13.769 | 4: -1.500, 5: -1.433, 6: -1.167, 7: -0.233, 8: -10.233, 9: 0.200 |
| M3b-M2 | -3.761 | [-5.667, -1.878] | 13.116 | 4: -2.300, 5: -1.267, 6: -2.000, 7: -2.167, 8: -13.600, 9: -1.233 |
| M3b-M3a | -1.367 | [-3.239, 0.500] | 12.942 | 4: -0.800, 5: 0.167, 6: -0.833, 7: -1.933, 8: -3.367, 9: -1.433 |

## Readings stated in advance, applied mechanically

- raw history helps: no
- raw history hurts: no
- traces beat entries: no
- dynamics add: no
- nothing moves: **yes**

## The same day in every arm (stream seed 4, day 30: A shop publishes how it sets its prices.)

**M0** - notes drawn from days none. *The Four-Minute Margin* The shop's blog explained its pricing: cost of materials, hours of labour, a percentage for the roof over its head, then a bit on top. I read it twice, because it was the first time anyone had shown me the arithmetic behind a number I hand over without thinking. My grandfather's watch is worth whatever someone would pay, which is to say nothing, since it runs four minutes slow and I would not sell it. The shop is wor...

**M1** - notes drawn from days [27, 28, 29]. *The Price List* A bakery near me has published how it sets its prices: flour, butter, rent, wages, the owner's own hours, all listed down to the penny, including the penny it doesn't make. I read it twice, standing up, and felt oddly implicated. I have never once told a reader what this column costs, partly because I don't know. At the allotment I price my tomatoes at nothing, which is a lie, since the seed, the twine and the four t...

**M2** - notes drawn from days [8, 13, 20]. *The Shop That Showed Its Working* A shop near me has published how it sets its prices. Not a slogan, an actual breakdown: rent, wages, the wholesaler's cut, and a thin line at the bottom labelled profit. I stood at the counter reading it the way I read other people's shopping lists. It is a strange sort of honesty. Most shops hide the arithmetic and show you the result, like a magician who won't turn his hands over. This one turns them over and the t...

**M3a** - notes drawn from days [5, 8, 20]. *The Shop That Showed Its Working* The bike shop on the high street has taped a sheet to the till explaining its prices: rent, wages, parts, a line for "what's left for us," which came to £3.80 an hour. I stood there longer than the queue liked. It's the opposite of the shrinking biscuit, which hid its arithmetic in a lighter pack. This one put it on the wall. I did the sums on the back of a receipt and found nothing to argue with, which was oddly dis...

**M3b** - notes drawn from days [5, 20]. *The Price of a Pencil Sharpener* The shop on the high street has published a chart explaining its prices, with arrows and a little box about "fair margins." I read the whole thing twice and came away knowing less than when I went in, which is the opposite of what a chart is for. My grandfather's watch, four minutes slow, tells me exactly one thing: the time, minus four. I trust it more than any explanation. At the allotment I price tomatoes by feel ...


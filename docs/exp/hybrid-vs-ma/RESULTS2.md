# Expanded pool results (snapshot 2026-10-18 12:54 JST)

seeds 1-20 x Red/Blue each pairing; Δ = paired diff vs escort_hunt (EH) on the same seeds; * = >2SE
```
agent | BenchMark | MA | EH | O_RUSH | O_GUARD | O_BMAGG | pool avg (ΔEH±SE) | min
EH | 0.582 23/8/9 Δ+0.000 | 0.759 39/0/1 Δ+0.000 | 0.500 19/2/19 Δ+0.000 | 0.484 18/0/22 Δ+0.000 | 0.591 22/6/12 Δ+0.000 | 0.757 39/1/0 Δ+0.000 | 0.612 | 0.484
MA | 0.612 27/9/4 Δ+0.030 | 0.500(mirror) | 0.241 1/0/39 Δ-0.259* | 0.377 10/0/30 Δ-0.107 | 0.343 7/4/29 Δ-0.249* | 0.646 26/14/0 Δ-0.111* | 0.453 | 0.241
H1 | 0.666 32/3/5 Δ+0.084 | 0.731 38/0/2 Δ-0.028 | 0.530 22/0/18 Δ+0.030 | 0.465 16/0/24 Δ-0.019 | 0.656 30/1/9 Δ+0.065 | 0.768 40/0/0 Δ+0.011 | 0.636 (Δ+0.024±0.020) | 0.465
H3 | 0.619 25/10/5 Δ+0.037 | 0.738 39/0/1 Δ-0.021 | 0.537 22/1/17 Δ+0.037 | 0.441 14/0/26 Δ-0.043 | 0.623 27/3/10 Δ+0.032 | 0.752 40/0/0 Δ-0.005 | 0.618 (Δ+0.006±0.017) | 0.441
V1 | n=0 | n=0 | n=0 | 0.426 13/0/27 Δ-0.059 | n=0 | n=0 | 
V2 | n=0 | n=0 | n=0 | 0.437 14/0/26 Δ-0.048 | n=0 | n=0 | 
V3 | n=0 | n=0 | n=0 | n=25 | n=0 | n=0 | 
V4 | n=0 | n=0 | n=0 | n=0 | n=0 | n=0 | 
```

Opponent sanity vs BenchMark:
```
{"label":"O_BMAGG_vs_BenchMark","n":40,"avg_score":0.2846,"se":0.0182,"win":0,"draw":8,"loss":32,"avg_our_alive":0.5,"avg_enemy_alive":4.4,"launched":960,"hits":27,"hit_rate":0.028,"escort_kills":0,"our_escort_lost":32,"errors":0}
{"label":"O_GUARD_vs_BenchMark","n":40,"avg_score":0.3731,"se":0.0324,"win":6,"draw":11,"loss":23,"avg_our_alive":0.57,"avg_enemy_alive":3.77,"launched":195,"hits":49,"hit_rate":0.251,"escort_kills":6,"our_escort_lost":23,"errors":0}
{"label":"O_RUSH_vs_BenchMark","n":40,"avg_score":0.6233,"se":0.0336,"win":29,"draw":3,"loss":8,"avg_our_alive":2.15,"avg_enemy_alive":3.23,"launched":366,"hits":74,"hit_rate":0.202,"escort_kills":29,"our_escort_lost":8,"errors":0}
{"label":"OBMAGG_vs_BenchMark","n":40,"avg_score":0.2974,"se":0.0195,"win":0,"draw":10,"loss":30,"avg_our_alive":0.53,"avg_enemy_alive":4.53,"launched":955,"hits":23,"hit_rate":0.024,"escort_kills":0,"our_escort_lost":29,"errors":0}
```

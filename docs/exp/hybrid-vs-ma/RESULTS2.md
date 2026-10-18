# Expanded pool final (2026-10-18 13:51 JST)
seeds 1-20 x Red/Blue per pairing (40), make_log only; Δ = paired diff vs EH; * >2SE; n=k = incomplete (pruned)
```
agent | BenchMark | MA | EH | O_RUSH | O_GUARD | O_BMAGG | pool avg (ΔEH±SE) | min
EH | 0.582 23/8/9 Δ+0.000 | 0.759 39/0/1 Δ+0.000 | 0.500 19/2/19 Δ+0.000 | 0.484 18/0/22 Δ+0.000 | 0.591 22/6/12 Δ+0.000 | 0.757 39/1/0 Δ+0.000 | 0.612 | 0.484
MA | 0.612 27/9/4 Δ+0.030 | 0.500(mirror) | 0.241 1/0/39 Δ-0.259* | 0.377 10/0/30 Δ-0.107 | 0.343 7/4/29 Δ-0.249* | 0.646 26/14/0 Δ-0.111* | 0.453 | 0.241
H1 | 0.666 32/3/5 Δ+0.084 | 0.731 38/0/2 Δ-0.028 | 0.530 22/0/18 Δ+0.030 | 0.465 16/0/24 Δ-0.019 | 0.656 30/1/9 Δ+0.065 | 0.768 40/0/0 Δ+0.011 | 0.636 (Δ+0.024±0.020) | 0.465
H3 | 0.619 25/10/5 Δ+0.037 | 0.738 39/0/1 Δ-0.021 | 0.537 22/1/17 Δ+0.037 | 0.441 14/0/26 Δ-0.043 | 0.623 27/3/10 Δ+0.032 | 0.752 40/0/0 Δ-0.005 | 0.618 (Δ+0.006±0.017) | 0.441
V1 | n=39 | n=0 | n=0 | 0.426 13/0/27 Δ-0.059 | n=0 | n=0 | 
V2 | n=0 | n=0 | n=0 | 0.437 14/0/26 Δ-0.048 | n=0 | n=0 | 
V3 | n=11 | n=0 | n=0 | 0.478 17/0/23 Δ-0.006 | n=0 | n=0 | 
V4 | n=0 | n=0 | n=0 | 0.438 14/0/26 Δ-0.046 | n=0 | n=0 | 
V5 | 0.609 27/5/8 Δ+0.028 | 0.743 39/0/1 Δ-0.016 | 0.634 29/2/9 Δ+0.134* | 0.503 19/0/21 Δ+0.019 | 0.676 31/2/7 Δ+0.085 | 0.756 40/0/0 Δ-0.000 | 0.654 (Δ+0.042±0.018) | 0.503
V6 | 0.609 27/5/8 Δ+0.027 | 0.729 38/0/2 Δ-0.030 | 0.661 31/2/7 Δ+0.161* | 0.530 21/0/19 Δ+0.045 | 0.681 32/1/7 Δ+0.090 | 0.757 40/0/0 Δ-0.000 | 0.661 (Δ+0.049±0.017) | 0.530
V6 - H1 pool Δ +0.025 ± 0.013 | V5 - H1 +0.018 ± 0.012 | V6 - V5 +0.007 ± 0.005
```
Opponents: O_RUSH (4 aircraft straight at our escort w/ IRST ID; vs BM 0.623), O_GUARD (1 flanker + 3 defenders near own escort; vs BM 0.373), O_BMAGG (BenchMark kShoot0.3/nMslSimul2; vs BM 0.297, 2.4% hit rate = weak)
Variants: V1 guard1, V2 guard2, V3 escortFireKm40, V4 guard1+fire40, V5 guard2 early-detect(deepX-20,flankX+10,|y|>50), V6 = V5+escortFireKm40
Best: V6. zip: /workspace/research/submit_candidates/submit_V6.zip (built from 264c352, ruff OK, zip_check OK, validate.py youth 3 fights no error) — NOT submitted

# EH vs MA / hybrid pool results (2026-10-18 10:03 JST)

seeds 1-20 x Red/Blue, make_log only (deterministic). ΔEH = paired diff vs escort_hunt on same seed/colour; * = >2SE
```
EH   | BenchMark 0.582±0.034 23/8/9 ΔEH +0.000±0.000 | MA 0.759±0.012 39/0/1 ΔEH +0.000±0.000 | EH 0.500±0.046 19/2/19 ΔEH +0.000±0.000 | pool=0.614
MA   | BenchMark 0.612±0.025 27/9/4 ΔEH +0.030±0.038 | MA: n=0 | EH 0.241±0.012 1/0/39 ΔEH -0.259±0.049*
H1   | BenchMark 0.666±0.029 32/3/5 ΔEH +0.084±0.044 | MA 0.731±0.018 38/0/2 ΔEH -0.028±0.022 | EH 0.530±0.044 22/0/18 ΔEH +0.030±0.058 | pool=0.642
H2   | BenchMark 0.626±0.030 25/10/5 ΔEH +0.044±0.042 | MA 0.704±0.024 36/0/4 ΔEH -0.055±0.027* | EH 0.488±0.044 18/1/21 ΔEH -0.012±0.058 | pool=0.606
H3   | BenchMark 0.619±0.029 25/10/5 ΔEH +0.037±0.042 | MA 0.738±0.014 39/0/1 ΔEH -0.021±0.018 | EH 0.537±0.043 22/1/17 ΔEH +0.037±0.060 | pool=0.631
```
H1: hybrid defPolicy=ma | H2: H1 + defLeashXKm=0 | H3: H1 + MA reserve=0
Agents: workspace/Agents/{EH,MA,H_H1,H_H2,H_H3}; code: branch exp/hybrid-vs-ma (cb5cdae), MA build: /workspace/ma_wt (6866d8e, scripts/build_submission.py)

"""One paired-eval match with full metrics. Usage: python run_one.py MODULE_PATH COLOR SEED OUT_JSON [REPLAY_DIR]
(cwd = repo workspace/). Mirrors local_test/run_eval_paired.run_fight, plus make_log, hits, launches, escort kill."""
import sys, os, json, random
import numpy as np
WS = "/workspace/air_combatAI_5/workspace"; os.chdir(WS); sys.path.insert(0, WS); sys.path.insert(0, "/workspace/air_combatAI_5/local_test")
import run_eval_paired as r
from src.fight import Fight
from ASRCAISim1.core import Fighter, Entity
mod, color, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
replay = sys.argv[5] if len(sys.argv) > 5 else None
my, opp = r.agent_info("0", mod), r.agent_info("1", os.environ.get("OPP", "Agents/BenchMark"))
mi = r.make_match_info(my, opp, seed, True) if color == "Red" else r.make_match_info(opp, my, seed, True)
mi["make_log"] = True
if replay:
    mi["replay"] = True; mi["log_dir"] = replay; os.makedirs(replay, exist_ok=True)
np.random.seed(seed); random.seed(seed)
f = Fight(mi); f.make_matchInfo(); f.set_match()
hits = {"Red": 0, "Blue": 0}; state = {"reg": False}
def onHit(args):
    hits[Entity.from_json(args["wpn"]).getTeam()] += 1
env = f.env; orig = env.step
TR = {"Red": lambda p: (p[1], -p[0]), "Blue": lambda p: (-p[1], p[0])}[color]
track = {}; death = {}; ncall = [0]
def step(a):
    if not state["reg"]:
        env.manager.getRuler()().manager.addEventHandler("Hit", onHit); state["reg"] = True
    res = orig(a); ncall[0] += 1
    assets = {w().getFullName(): w() for w in env.manager.getAssets(lambda x: isinstance(x, Fighter))}
    for w in env.manager.getAgents():
        ag = w(); nm = ag.getFullName()
        if not nm.startswith(color): continue
        try:
            slot = int(nm.split(":")[0].split("_")[-1])
        except ValueError:
            continue
        p = assets.get(ag.parent.getFullName())
        if p is None: continue
        alive = bool(p.isAlive())
        if not alive: death.setdefault(slot, ncall[0])
        if ncall[0] % 10 == 0 and alive:
            pp = p.pos(); X, Y = TR(pp[:2]); track.setdefault(slot, []).append((ncall[0], round(X/1000, 1), round(Y/1000, 1)))
    return res
env.step = step
winner, detail = f.run(False)
enemy = "Blue" if color == "Red" else "Red"
launched = {}; escAlive = {}
for w in env.manager.getAssets(lambda a: isinstance(a, Fighter)):
    x = w(); tm = x.getTeam()
    launched[tm] = launched.get(tm, 0) + (x.numMsls - x.remMsls)
    if x.getFullName().endswith("E"): escAlive[tm] = bool(x.isAlive())
al = detail.get("numAlives", {})
row = {"module": mod, "seed": seed, "color": color, "endReason": detail.get("endReason"), "step_count": detail.get("step_count"),
       "score": detail["scores"].get(color, 0.0), "result": "win" if winner == color else ("loss" if winner == enemy else "draw"),
       "our_alive": al.get(color, 0.0), "enemy_alive": al.get(enemy, 0.0),
       "our_launched": launched.get(color, 0), "our_hits": hits[color], "enemy_launched": launched.get(enemy, 0), "enemy_hits": hits[enemy],
       "enemy_escort_killed": not escAlive.get(enemy, True), "our_escort_killed": not escAlive.get(color, True), "error": bool(detail.get("error")), "death_step": death, "track": track}
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(row, open(out, "w"), indent=1)
json.dump(detail.get("logs", {}).get(color, detail.get("logs", {})), open(out.replace(".json", "_log.json"), "w"), default=str)
print("ROW", json.dumps(row))

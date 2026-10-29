"""Small simulated world-economy model for the Chancellor Simulator.

Country growth rates evolve each in-game year, with persistent country-specific momentum
and random-but-seeded annual surprises. These are game values, not live forecasts.
"""
import random

BASELINES = {
    "United States": 2.0,
    "Euro area": 1.2,
    "Germany": 1.0,
    "France": 1.1,
    "Japan": 0.8,
    "China": 4.5,
    "India": 6.2,
    "Canada": 1.7,
    "Australia": 2.0,
}

def ensure(s):
    if not s.get("world_economy"):
        s.world_economy = {name: {"growth": rate, "momentum": 0.0} for name, rate in BASELINES.items()}
    s.setdefault("world_history", [])

def advance(s):
    """Advance all partner economies by one simulated year; return a ranked table-ready list."""
    ensure(s)
    rng = random.Random(f"{s.get('seed', 0)}-world-{s.get('term', 1)}-{s.get('year', 1)}")
    # Global conditions can create a shared upswing or downturn for trading partners.
    global_cycle = rng.choices([-1.0, -0.45, 0.0, 0.35, 0.8], weights=[8, 16, 42, 24, 10])[0]
    rows = []
    for name, item in s.world_economy.items():
        surprise = rng.uniform(-0.9, 0.9)
        # Mean reversion prevents the simulation from drifting indefinitely.
        old = float(item.get("growth", BASELINES.get(name, 1.5)))
        momentum = float(item.get("momentum", 0.0)) * 0.45 + global_cycle * 0.45 + surprise * 0.55
        growth = max(-5.5, min(9.0, old + momentum * 0.55 + (BASELINES.get(name, 1.5) - old) * 0.18))
        item["growth"] = round(growth, 2)
        item["momentum"] = round(momentum, 2)
        rows.append({"Economy": name, "Real GDP growth (%)": item["growth"], "Change vs last year (pp)": round(item.get("last_growth", old) - old, 2)})
        item["last_growth"] = item["growth"]
    s.world_history.append({"Period": f"Term {s.get('term',1)}, Year {s.get('year',1)}", **{n: v["growth"] for n,v in s.world_economy.items()}})
    del s.world_history[:-30]
    s.world_cycle = global_cycle
    return rows

def rows(s):
    ensure(s)
    return [{"Economy": name, "Real GDP growth (%)": round(float(v["growth"]), 2),
             "Direction": ("Growing" if float(v["growth"]) > 0 else "Contracting" if float(v["growth"]) < 0 else "Flat"),
             "Momentum": ("Accelerating" if v.get("momentum", 0) > 0.18 else ("Slowing" if v.get("momentum", 0) < -0.18 else "Steady"))}
            for name, v in s.world_economy.items()]

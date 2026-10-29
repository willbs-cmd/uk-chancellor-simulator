"""Small simulated world-economy model for the Chancellor Simulator."""
import random

BASELINES = {"United States": 2.0, "Euro area": 1.2, "Germany": 1.0, "France": 1.1,
             "Japan": 0.8, "China": 4.5, "India": 6.2, "Canada": 1.7, "Australia": 2.0}
FLAGS = {"United States": "🇺🇸", "Euro area": "🇪🇺", "Germany": "🇩🇪", "France": "🇫🇷",
         "Japan": "🇯🇵", "China": "🇨🇳", "India": "🇮🇳", "Canada": "🇨🇦", "Australia": "🇦🇺"}
GDP_USD_TN = {"United States": 29.2, "Euro area": 16.5, "Germany": 4.7, "France": 3.2,
              "Japan": 4.1, "China": 18.7, "India": 3.9, "Canada": 2.2, "Australia": 1.8}

def ensure(s):
    # Migrate older save files as well as initialise a fresh game. Always merge
    # the current country roster into saved data so new economies appear without
    # resetting progress already made by the player.
    if not isinstance(s.get("world_economy"), dict):
        s.world_economy = {}
    for name, rate in BASELINES.items():
        item = s.world_economy.get(name)
        if not isinstance(item, dict):
            item = {}
            s.world_economy[name] = item
        item.setdefault("growth", rate)
        item.setdefault("momentum", 0.0)
        item.setdefault("output_index", 100.0)
        item.setdefault("gdp_usd_tn", GDP_USD_TN[name])
    s.setdefault("world_history", [])

def advance(s):
    ensure(s)
    rng = random.Random(f"{s.get('seed', 0)}-world-{s.get('term', 1)}-{s.get('year', 1)}")
    global_cycle = rng.choices([-1.0, -0.45, 0.0, 0.35, 0.8], weights=[8, 16, 42, 24, 10])[0]
    for name, item in s.world_economy.items():
        surprise = rng.uniform(-0.9, 0.9)
        old = float(item.get("growth", BASELINES.get(name, 1.5)))
        momentum = float(item.get("momentum", 0.0)) * 0.45 + global_cycle * 0.45 + surprise * 0.55
        growth = max(-5.5, min(9.0, old + momentum * 0.55 + (BASELINES.get(name, 1.5) - old) * 0.18))
        item["growth"] = round(growth, 2)
        item["momentum"] = round(momentum, 2)
        item["output_index"] = round(float(item.get("output_index", 100.0)) * (1 + growth / 100.0), 1)
        item["gdp_usd_tn"] = round(float(item.get("gdp_usd_tn", GDP_USD_TN.get(name, 1.0))) * (1 + growth / 100.0), 2)
    s.world_history.append({"Period": f"Term {s.get('term',1)}, Year {s.get('year',1)}", **{n: v["growth"] for n,v in s.world_economy.items()}})
    del s.world_history[:-30]
    s.world_cycle = global_cycle

def rows(s):
    ensure(s)
    result = []
    for name, v in s.world_economy.items():
        growth = float(v["growth"])
        result.append({"Economy": name, "Flag": FLAGS.get(name, "🌐"),
                       "Output index": round(float(v["output_index"]), 1),
                       "Growth": f"{growth:+.1f}%",
                       "GDP ($tn)": round(float(v["gdp_usd_tn"]), 2),
                       "Direction": "Growing" if growth > 0 else "Contracting" if growth < 0 else "Flat",
                       "Momentum": "Accelerating" if v.get("momentum", 0) > 0.18 else ("Slowing" if v.get("momentum", 0) < -0.18 else "Steady")})
    return result

"""Headless balance testing for the Chancellor Simulator.

    python sim.py audit               # score every option of every decision and flag outliers
    python sim.py run [N] [difficulty]  # play N full terms per strategy and print win/sack rates\n    python sim.py check [N] [difficulty] # validate data contracts and enforce broad win-rate guardrails

It drives the real game engine with a fake ``st.session_state``, so no browser or Streamlit server is needed.
"""
import collections
import math
import random
import statistics
import sys
import types


def _install_stubs():
    """Use real Streamlit if present; otherwise stand in for it (handy in CI). Either way, fake the session."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        st = types.ModuleType('streamlit')
        st.rerun = lambda: None
        sys.modules['streamlit'] = st
    try:
        import altair  # noqa: F401
    except ImportError:
        sys.modules['altair'] = types.ModuleType('altair')


class FakeState(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        del self[k]


_install_stubs()
import streamlit as st  # noqa: E402

st.session_state = FakeState()

import budget  # noqa: E402
import decisions  # noqa: E402
import engine  # noqa: E402
import imf_outlook  # noqa: E402
import scenarios as scen  # noqa: E402
import state  # noqa: E402
from content_store import load_json  # noqa: E402

# How much one point of each stat is worth to a player (rough, for auditing options)
WEIGHTS = dict(approval=1.0, market_conf=0.5, market=0.5, headroom=0.7, growth=8, deficit=-2, inflation=-4,
               gilt_yield=-6, gilt=-6, unemployment=-4, real_wages=4, nhs_waiting=-3, nhs_morale=0.15,
               child_poverty=-0.8, homes_built=0.12, house_ratio=-2, homeless=-0.1, netzero=0.1,
               energy_bills=-0.01, rail=0.15, schools=0.15, prisons=-0.1, pm_opinion=0.3, cab_opinion=0.2,
               party_opinion=0.3, backbench_opinion=0.3, media_opinion=0.2, debt=-1.5)


def utility(fx):
    return sum(WEIGHTS.get(k, 0) * v for k, v in fx.items() if isinstance(v, (int, float)))


# ---------------------------------------------------------------- audit
def audit():
    flagged = 0
    dominant = 0
    for key, d in sorted(decisions.DECISIONS.items()):
        delayed = decisions.DELAYED.get(key, {})
        rows = []
        for i, fx in enumerate(d['effects']):
            total = dict(fx)
            for k, v in delayed.get(i, {}).get('fx', {}).items():
                total[k] = total.get(k, 0) + v
            rows.append((decisions.IDEOLOGIES[i], utility(total), fx))
        us = [r[1] for r in rows]
        mean, sd = statistics.mean(us), statistics.pstdev(us) or 1
        print(f"\n({key[0]},{key[1]}) {d['title']}   mean {mean:+.1f}  sd {sd:.1f}")
        for ideology, u, fx in sorted(rows, key=lambda r: -r[1]):
            flag = ''
            if (u - mean) / sd > 1.35:
                flag = '  <-- DOMINANT'
                dominant += 1
            elif (u - mean) / sd < -1.35:
                flag = '  <-- trap'
            if flag:
                flagged += 1
            print(f"   {ideology:<18} {u:+6.1f}{flag}")
    print(f"\n{dominant} dominant and {flagged - dominant} trap option(s).")
    return dominant


# ---------------------------------------------------------------- playing
def new_run(party, difficulty, seed, **opts):
    """Start a headless game. ``opts`` may carry scenario=, spad= and pledges= (see state.new_game)."""
    state.new_game(party, difficulty, seed, show_tags=True, **opts)
    budget.ensure()


def pick_option(strategy, options, rng):
    if strategy == 'random':
        return rng.choice(options)
    if strategy == 'sensible':
        core = engine.PURITY.get(st.session_state.party, [])
        return max(options, key=lambda o: utility(o['effect']) + (3 if o['ideology'] in core else 0) + rng.random())
    if strategy == 'core':
        core = engine.PURITY.get(st.session_state.party, [])
        return rng.choice([o for o in options if o['ideology'] in core] or options)
    return next((o for o in options if o['ideology'] == strategy), options[0])


def play_budget(strategy):
    """Very simple budget heuristic for the 'sensible' player; everyone else submits the default."""
    s = st.session_state
    if strategy != 'sensible':
        return
    if s.headroom < 3:
        s['bt_income'] = min(s['bt_income'] + 1, 45)
        s['bs_other'] = max(s['bs_other'] - 1.0, -15.0)
    elif s.headroom > 12:
        s['bs_health'] = min(s['bs_health'] + 1.0, 15.0)


def play(party='Labour', strategy='random', difficulty='Hardcore', seed=1, terms=1, **opts):
    s = st.session_state
    rng = random.Random(seed)
    new_run(party, difficulty, seed, **opts)
    for _ in range(400):
        if s.get('game_over'):
            break
        if s.year > 5:
            r = engine.compute_election()
            if s.get('game_over') or terms <= s.term or not r['win']:
                break
            engine.continue_term()
            continue
        if s.active_crisis:
            crisis = scen.get(s.active_crisis)
            if strategy == 'sensible':
                idx = max(range(len(crisis['opts'])), key=lambda i: utility(crisis['opts'][i][1]))
            else:
                idx = rng.randrange(len(crisis['opts']))
            engine.resolve_crisis(idx)
            continue
        if s.get('active_request'):
            # the 'sensible' player only pays for a minister's pet project when there is headroom to spare
            engine.resolve_request(s.headroom > 6 if strategy == 'sensible' else rng.random() < 0.5)
            continue
        if s.block == 3:
            play_budget(strategy)
            if engine.submit_budget() == 'sacked':
                break
            engine.proceed_to_spring()
            continue
        engine.execute_decision(pick_option(strategy, engine.current_options(), rng))
    r = s.get('election_result') or {}
    return dict(win=bool(r.get('win')) and not s.get('sacked'), sacked=bool(s.get('sacked')),
                seats=r.get('player_seats', 0), approval=s.approval, headroom=s.headroom,
                year=s.year, term=s.term, market=s.market_conf, over=(s.get('game_over') or {}).get('kind'))


def run(n=200, difficulty='Hardcore'):
    strategies = ['random', 'core', 'Hard Left', 'Social Democratic', 'Centric', 'Free-Market', 'Fiscal Austerity', 'sensible']
    print(f'{n} runs per strategy, Labour, {difficulty}\n')
    print(f"{'strategy':<20}{'win%':>6}{'sacked%':>9}{'seats':>7}{'appr':>7}{'headroom':>10}")
    for strat in strategies:
        res = [play('Labour', strat, difficulty, seed=i) for i in range(n)]
        win = sum(r['win'] for r in res) / n * 100
        sacked = sum(r['sacked'] for r in res) / n * 100
        print(f"{strat:<20}{win:6.0f}{sacked:9.0f}{statistics.mean(r['seats'] for r in res):7.0f}"
              f"{statistics.mean(r['approval'] for r in res):7.1f}{statistics.mean(r['headroom'] for r in res):10.1f}")
    print('\nBy party:   random play | own-ideology play | sensible play')
    for party in state.PARTIES:
        row = []
        for strat in ('random', 'core', 'sensible'):
            res = [play(party, strat, difficulty, seed=i) for i in range(n)]
            row.append(f"win {sum(r['win'] for r in res) / n * 100:3.0f}% sacked {sum(r['sacked'] for r in res) / n * 100:3.0f}%")
        print(f"  {party:<20} " + '  |  '.join(row))


# ---------------------------------------------------------------- regression check
def check(n=None, difficulty=None):
    """Fail if editable content breaks its schema or the sensible-strategy win rates collapse.

    Thresholds are broad regression guards, not a claim that one strategy is objectively optimal.
    Run with: python sim.py check [N] [difficulty]
    """
    thresholds = load_json('balance_thresholds.json')
    n = max(int(n or thresholds.get('default_runs', 20)), int(thresholds.get('default_runs', 20)))
    difficulty = difficulty or thresholds.get('default_difficulty', 'Hardcore')
    contract = thresholds['contract']
    failures = []

    if len(decisions.DECISIONS) < contract['minimum_decisions']:
        failures.append(f"Only {len(decisions.DECISIONS)} policy decisions; expected at least {contract['minimum_decisions']}.")
    if len(scen.CRISES) < contract['minimum_crises']:
        failures.append(f"Only {len(scen.CRISES)} crises; expected at least {contract['minimum_crises']}.")
    if len(budget.TAXES) < contract['minimum_tax_levers']:
        failures.append(f"Only {len(budget.TAXES)} tax levers; expected at least {contract['minimum_tax_levers']}.")
    if len(budget.SPEND_DEFAULTS) < contract['minimum_spending_departments']:
        failures.append(f"Only {len(budget.SPEND_DEFAULTS)} spending departments; expected at least {contract['minimum_spending_departments']}.")
    if len(budget.TAX_POLICIES) < contract['minimum_tax_schemes']:
        failures.append(f"Only {len(budget.TAX_POLICIES)} revenue schemes; expected at least {contract['minimum_tax_schemes']}.")
    if len(budget.SPEND_POLICIES) < contract['minimum_spending_schemes']:
        failures.append(f"Only {len(budget.SPEND_POLICIES)} spending schemes; expected at least {contract['minimum_spending_schemes']}.")

    for key, decision in decisions.DECISIONS.items():
        options = decision.get('options', [])
        effects = decision.get('effects', [])
        if len(options) != contract['minimum_options_per_decision'] or len(effects) != contract['minimum_options_per_decision']:
            failures.append(f"Decision {key} ({decision.get('title', 'untitled')}) must have five options and five effects.")
        for ix, effect in enumerate(effects):
            if not isinstance(effect, dict):
                failures.append(f"Decision {key} option {ix + 1} has no effect object.")
            elif any(isinstance(v, (int, float)) and not math.isfinite(v) for v in effect.values()):
                failures.append(f"Decision {key} option {ix + 1} contains a non-finite effect.")

    for key, crisis in scen.CRISES.items():
        opts = crisis.get('opts', [])
        if len(opts) < 2:
            failures.append(f"Crisis {key} needs at least two response options.")
        for ix, opt in enumerate(opts):
            if len(opt) != 2 or not isinstance(opt[1], dict):
                failures.append(f"Crisis {key} response {ix + 1} must be [label, effect-object].")

    for cid in scen.RANDOM_POOL:
        if cid not in scen.CRISES:
            failures.append(f"Random crisis pool refers to missing crisis ID {cid}.")
    for cid in scen.IDEOLOGY_LINKS.values():
        if cid not in scen.CRISES:
            failures.append(f"Ideology crisis link refers to missing crisis ID {cid}.")
    for link in scen.DECISION_LINKS.values():
        if link[0] not in scen.CRISES:
            failures.append(f"Decision crisis link refers to missing crisis ID {link[0]}.")
    for row in imf_outlook.OUTLOOK.values():
        if any(not math.isfinite(float(v)) for v in row.values()):
            failures.append("IMF baseline contains a non-finite numeric value.")
    if not imf_outlook.OUTLOOK or min(imf_outlook.OUTLOOK) > 2026:
        failures.append("IMF baseline must include 2026 and later projection years.")

    for key, delayed in decisions.DELAYED.items():
        if key not in decisions.DECISIONS:
            failures.append(f"Delayed consequences refer to missing decision key {key}.")
        for option_ix, effect in delayed.items():
            if option_ix < 0 or option_ix >= len(decisions.IDEOLOGIES):
                failures.append(f"Delayed consequence at {key} refers to missing option {option_ix}.")
            if not isinstance(effect.get('fx', {}), dict):
                failures.append(f"Delayed consequence at {key}, option {option_ix} has invalid effects.")

    print(f"Content contract: {len(decisions.DECISIONS)} decisions, {len(scen.CRISES)} crises, "
          f"{len(budget.TAXES)} tax levers, {len(budget.SPEND_DEFAULTS)} spending lines.")
    if failures:
        print("\nCONTENT CHECK FAILED:")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("Content contract: PASS")

    print(f"\nBalance regression: {n} sensible-strategy runs per party on {difficulty}.")
    print(f"{'party':<20}{'win%':>8}{'sacked%':>10}{'mean approval':>15}{'mean headroom':>16}  result")
    seed_start = int(thresholds.get('seed_start', 0))
    for party in state.PARTIES:
        results = [play(party, thresholds.get('strategy', 'sensible'), difficulty,
                        seed=seed_start + i) for i in range(n)]
        win_rate = sum(r['win'] for r in results) / n * 100
        sack_rate = sum(r['sacked'] for r in results) / n * 100
        mean_approval = statistics.mean(r['approval'] for r in results)
        mean_headroom = statistics.mean(r['headroom'] for r in results)
        guard = thresholds['party_thresholds'].get(party)
        passed = bool(guard) and win_rate >= guard['minimum_win_percent'] and sack_rate <= guard['maximum_sack_percent']
        for r in results:
            for stat in ('approval', 'headroom', 'market'):
                if not math.isfinite(float(r[stat])):
                    failures.append(f"{party} produced non-finite {stat} in a headless run.")
                    passed = False
        status = "PASS" if passed else "FAIL"
        print(f"{party:<20}{win_rate:7.1f}%{sack_rate:9.1f}%{mean_approval:15.1f}{mean_headroom:16.1f}  {status}")
        if not passed:
            failures.append(
                f"{party}: win {win_rate:.1f}% (min {guard['minimum_win_percent'] if guard else 'n/a'}%), "
                f"sacked {sack_rate:.1f}% (max {guard['maximum_sack_percent'] if guard else 'n/a'}%)."
            )

    if failures:
        print("\nREGRESSION CHECK FAILED:")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("\nREGRESSION CHECK PASSED")
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if cmd == 'audit':
        audit()
    elif cmd == 'check':
        sys.exit(check(int(sys.argv[2]) if len(sys.argv) > 2 else None,
                       sys.argv[3] if len(sys.argv) > 3 else None))
    else:
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 100, sys.argv[3] if len(sys.argv) > 3 else 'Hardcore')

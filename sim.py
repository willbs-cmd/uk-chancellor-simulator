"""Headless balance testing for the Chancellor Simulator.

    python sim.py audit               # score every option of every decision and flag outliers
    python sim.py run [N] [difficulty]  # play N full terms per strategy and print win/sack rates

It drives the real game engine with a fake ``st.session_state``, so no browser or Streamlit server is needed.
"""
import collections
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
import scenarios as scen  # noqa: E402
import state  # noqa: E402

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
def new_run(party, difficulty, seed):
    state.new_game(party, difficulty, seed, show_tags=True)
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


def play(party='Labour', strategy='random', difficulty='Hardcore', seed=1, terms=1):
    s = st.session_state
    rng = random.Random(seed)
    new_run(party, difficulty, seed)
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


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if cmd == 'audit':
        audit()
    else:
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 100, sys.argv[3] if len(sys.argv) > 3 else 'Hardcore')

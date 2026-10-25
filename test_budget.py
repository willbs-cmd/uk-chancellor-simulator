"""Budget tests. Run with:  python tests/test_budget.py   (or pytest)."""
import copy
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):                  # works in a tests/ folder or beside the game files
    sys.path.insert(0, str(_p))
import sim  # noqa: E402  (installs the fake session state)
import econ  # noqa: E402
from sim import budget, engine, st  # noqa: E402


def fresh(party='Labour', difficulty='Normal', seed=1):
    sim.new_run(party, difficulty, seed)
    return st.session_state


def test_defaults_keep_the_books_balanced():
    s = fresh()
    rev, spend = budget.totals(budget.read())
    assert abs(rev - 1150.0) < 1e-6, rev                 # new levers were carved out of 'other receipts'
    assert abs(spend - 1275.4) < 1e-6, spend             # a realistic ~4%-of-GDP deficit
    assert abs((spend - rev) - s.deficit) < 1e-6         # and the opening deficit matches the Budget screen
    assert abs(s.deficit / budget.GDP_BN - 0.04) < 0.001


def test_every_new_lever_moves_revenue_the_right_way():
    s = fresh()
    base = budget.read()
    for k, t in budget.TAXES.items():
        up = copy.deepcopy(base)
        up['tax'][k] = min(t['hi'], t['default'] + max(1, t['step']))
        down = copy.deepcopy(base)
        down['tax'][k] = max(t['lo'], t['default'] - max(1, t['step']))
        r0, r_up, r_dn = (budget.revenues(b)[k] for b in (base, up, down))
        assert r_up > r0 > r_dn, k


def test_commons_vote_matches_the_defeat_rule():
    s = fresh()
    assert budget.commons_ayes(19.9, 0) == 325 and budget.commons_ayes(20, 0) == 326
    for bb in range(0, 101):
        assert (budget.commons_ayes(bb, 0) >= budget.WIN) == (bb >= 20)
    assert budget.commons_ayes(100, 999) == 650           # capped at the size of the House


def test_losing_the_vote_sacks_you_but_whips_can_save_you():
    s = fresh()
    s.backbench_opinion = 12.0
    assert budget.projected_ayes(budget.read()) < budget.WIN
    budget._whip('pork')                                  # +15 votes at £2B
    assert s.whip_ayes == 15 and budget.projected_ayes(budget.read()) >= budget.WIN
    budget._whip('pork')                                  # each lever works once
    assert s.whip_ayes == 15
    assert engine.submit_budget() == 'ok' and s.budget_passed
    assert s.whip_ayes == 0 and s.vote_ayes >= budget.WIN   # reset for next year

    s2 = fresh()
    s2.backbench_opinion = 12.0
    assert engine.submit_budget() == 'sacked' and s2.game_over['kind'] == 'sacked'


def test_revolt_penalty_only_for_a_new_hike_not_every_year():
    s = fresh('Conservative')
    s['bt_corp'] = 30                                     # a hike
    before = s.backbench_opinion
    assert engine.submit_budget() == 'ok'
    assert s.backbench_opinion <= before - 15 + 0.01
    engine.proceed_to_spring()
    s.backbench_opinion = 60.0
    s.party_opinion = 70.0
    # same rate next year: not a hike, so no penalty (this used to hit every single spring)
    assert not budget.rebel_risks(budget.read())
    assert engine.submit_budget() == 'ok' and s.backbench_opinion == 60.0


def test_party_specific_irritants():
    s = fresh('Labour')
    s['bs_welfare'] = -5.0
    assert [r[0] for r in budget.rebel_risks(budget.read())] == ['party_opinion']
    s2 = fresh('Conservative')
    s2['bs_aid'] = 5.0
    s2['bt_fuel'] = 10
    assert len(budget.rebel_risks(budget.read())) == 2
    s3 = fresh('Green Party')
    s3['bt_fuel'] = -10
    assert any('fuel' in r[2] for r in budget.rebel_risks(budget.read()))


def test_old_save_files_still_load():
    s = fresh()
    old = copy.deepcopy(s.budget_applied)
    for k in ('fuel', 'sin', 'cgt', 'iht'):
        del old['tax'][k]
    for k in ('science', 'aid', 'culture'):
        del old['spend'][k]
    for k in ('mansion', 'digital', 'carbon', 'gambling'):
        del old['tax_pol'][k]
    for k in ('nuclear', 'childcare', 'winterfuel', 'potholes'):
        del old['spend_pol'][k]
    s.budget_applied = old
    for k in [k for k in s if str(k).startswith(('bt_', 'bs_', 'btp_', 'bsp_'))]:
        del s[k]
    for k in ('science', 'aid', 'culture'):
        del s.dept_spend[k]
    before_other = s.dept_spend['other'] = 130.0
    del s['budget_last_tax']
    budget.ensure()
    carved = sum(budget.SPEND_DEFAULTS[k]['default'] for k in ('science', 'aid', 'culture'))
    assert abs(s.dept_spend['other'] - (before_other - carved)) < 1e-6   # new lines are carved out of 'Other'
    assert budget.read()['tax']['cgt'] == 24
    assert budget.forecast(budget.read())


def test_forecast_matches_the_real_spring_tick():
    s = fresh()
    s.country['nhs_waiting'], s.country['rail'] = 6.0, 85.0   # keep the political drags out of the way
    rows = budget.forecast(budget.read(), years=2)
    engine.proceed_to_spring()
    r = rows[0]
    assert (r['growth'], r['inflation'], r['debt'], r['headroom'], r['gilt']) == (s.growth, s.inflation, s.debt, s.headroom, s.gilt_yield)
    assert r['market'] == s.market_conf


def test_forecast_reacts_to_the_budget():
    s = fresh()
    base = budget.forecast(budget.read())[-1]['headroom']
    s['bs_health'] = 10.0                                  # a big NHS splurge
    assert budget.forecast(budget.read())[-1]['headroom'] < base - 10


def test_imf_anchor_is_year_aware():
    s = fresh()
    v = {k: s[k] for k in ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf', 'approval')}
    anchored, free = econ.step(v, 2), econ.step(v, None)
    assert anchored['growth'] != free['growth']             # year 2 = 2027, which the IMF covers
    assert econ.step(v, 6) == econ.step(v, None)            # term 2 year 1 must not be dragged back to 2026
    assert econ.game_year(2, 1) == 6 and econ.game_year(1, 5) == 5


def test_market_confidence_never_goes_negative_on_a_bad_budget():
    s = fresh()
    s.approval, s.market_conf = 20.0, 0.5
    engine.submit_budget()
    assert s.market_conf >= 0


def test_new_budget_fallout_crises_exist_and_trigger():
    import scenarios as scen
    assert {'fuel_protest', 'brain_drain'} <= set(scen.CRISES)
    s = fresh()
    s['bt_fuel'] = 40
    budget._apply()
    for seed in range(200):
        s.seed, s.steps, s.fallout_done = seed, 0, []
        engine.reseed('x')
        if scen.pick_next(2, 1, 'Centric') == 'fuel_protest':
            break
    else:
        raise AssertionError('fuel protests never fired')


def test_save_roundtrip_keeps_budget_state():
    s = fresh('Conservative')
    s['bt_cgt'] = 30
    budget._apply()
    budget._whip('dilute')
    text = sim.state.export_save()
    s.clear()
    assert sim.state.import_save(text) is None
    assert s.whip_ayes == 10 and s.budget_applied['tax']['cgt'] == 30 and s['bt_cgt'] == 30


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

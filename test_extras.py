"""Tests for scenarios, advisors, pledges, cabinet requests, the economic cycle, undo and the Budget speech."""
import copy
import pathlib
import random
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):                  # works in a tests/ folder or beside the game files
    sys.path.insert(0, str(_p))
import sim  # noqa: E402  (must come first: installs the fake Streamlit)
import econ  # noqa: E402
import politics  # noqa: E402
from sim import budget, engine, state, st  # noqa: E402


def fresh(party='Labour', difficulty='Normal', seed=1, **opts):
    sim.new_run(party, difficulty, seed, **opts)
    return st.session_state


def test_scenarios_set_the_opening_economy():
    s = fresh(scenario='crash2008')
    assert (s.debt, s.deficit, s.growth, s.macro_cycle) == (60.0, 153.0, -2.5, 'Recession')
    assert abs(s.budget_interest - budget.interest()) < 1e-9       # no phantom interest shock in the first spring
    s = fresh(scenario='winter1978')
    assert s.inflation == 15.5 and s.interest_rate == 12.0 and '1978' in s.message
    s = fresh(scenario='nonsense')
    assert s.scenario == 'fragile' and s.debt == 98.2


def test_every_scenario_plays_through_with_every_advisor():
    for sc in state.SCENARIOS:
        for spad in (None, *politics.SPADS):
            r = sim.play('Labour', 'sensible', 'Normal', seed=3, terms=1, scenario=sc, spad=spad)
            assert r['year'] >= 1


def test_pledges_give_approval_and_are_validated():
    base = fresh().approval
    s = fresh(pledges=['income', 'nhs', 'vat', 'corp'])             # a fourth is ignored
    assert s.pledges == ['income', 'nhs', 'vat'] and s.approval == base + 6.0
    assert fresh(pledges=['bogus']).pledges == []


def test_breaking_a_pledge_hurts_once_and_spin_halves_it():
    def run(spad):
        s = fresh(pledges=['income'], spad=spad)
        s['bt_income'] = 25
        engine.submit_budget()
        return dict(approval=s.approval, broken=list(s.broken_pledges), message=s.message)   # s is one shared session: copy out
    plain, spun = run(None), run('spin')
    assert plain['broken'] == ['income'] and 'U-TURN' in plain['message']
    assert abs((spun['approval'] - plain['approval']) - 6.0) < 1e-6   # 12 vs 6 points
    # a second Budget at the same rate does not break it again
    engine.proceed_to_spring()
    assert politics.broken_by(budget.read()) == []


def test_each_pledge_type_triggers_on_the_right_lever():
    s = fresh()
    s.pledges = ['nhs', 'edu', 'welfare', 'cgt', 'vat', 'corp']     # more than the setup screen allows, to test every rule
    assert politics.broken_by(budget.read()) == []
    s['bs_health'], s['bs_education'], s['bs_welfare'] = -3.0, -3.0, 3.0
    s['bt_cgt'], s['bt_vat'], s['bt_corp'] = 30, 21, 26
    assert set(politics.broken_by(budget.read())) == {'nhs', 'edu', 'welfare', 'cgt', 'vat', 'corp'}


def test_deficit_pledge_is_only_judged_in_year_five():
    s = fresh(pledges=['deficit'])
    assert politics.broken_by(budget.read()) == []                   # year 1: nothing to judge yet
    s.year = 5
    assert politics.broken_by(budget.read()) == ['deficit']          # deficit has not fallen
    s['bt_income'] = 45                                              # a huge tax rise cuts it
    assert politics.broken_by(budget.read()) == []


def test_advisors():
    s = fresh(spad='enforcer')
    assert budget.commons_ayes(20, 0) == 326 + politics.ENFORCER_VOTES
    s = fresh(spad='banker')
    s.market_conf = 3.0
    state.record()
    assert s.market_conf == politics.BANKER_FLOOR

    def spring(spad):
        s = fresh(spad=spad, seed=4)
        engine.proceed_to_spring()
        return s.headroom
    assert abs(spring('hawk') - spring(None) - politics.HAWK_SAVING) < 1e-6


def test_cabinet_requests_cost_money_or_goodwill():
    s = fresh()
    req = copy.deepcopy(politics.CABINET_REQUESTS[0])
    s.active_request = req
    head, deficit = s.headroom, s.deficit
    engine.resolve_request(True)
    assert s.active_request is None and abs(s.headroom - (head - req['cost'])) < 1e-6
    assert abs(s.deficit - (deficit + req['cost'])) < 1e-6
    s.active_request = copy.deepcopy(req)
    cab = s.cab_opinion
    engine.resolve_request(False)
    assert s.cab_opinion == cab + req['refuse']['cab_opinion'] and s.headroom == head - req['cost']


def test_cabinet_requests_actually_appear_in_play():
    seen = 0
    for seed in range(25):
        fresh(seed=seed)
        s = st.session_state
        engine.execute_decision(engine.current_options()[0])
        seen += bool(s.get('active_request'))
    assert 0 < seen < 25


def test_economic_cycle_moves_growth_and_can_shift():
    s = fresh()
    v = {k: s[k] for k in ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf', 'approval')}
    g = {c: econ.step({**v, 'cycle': c})['growth'] for c in econ.CYCLES}
    assert g['Boom'] > g['Stagnation'] > g['Recession']
    s.macro_cycle = 'Stagnation'
    random.seed(0)
    with __import__('unittest.mock').mock.patch('random.random', return_value=0.0):
        politics.shift_macro_cycle()
    assert s.macro_cycle != 'Stagnation' and 'GLOBAL SHIFT' in s.message


def test_debt_is_stable_without_player_action():
    s = fresh()
    for _ in range(5):
        engine.proceed_to_spring()
    assert 90 < s.debt < 115, s.debt                                 # a 4% deficit no longer explodes (or erases) the debt


def test_undo_restores_the_game_and_is_limited_by_difficulty():
    s = fresh(difficulty='Easy')
    assert s.undos_left == 3
    start = (s.steps, s.approval, s.year, s.block)
    engine.execute_decision(engine.current_options()[0])
    assert s.steps == start[0] + 1 and state.can_undo()
    assert state.undo() is True
    assert (s.steps, s.approval, s.year, s.block) == start and s.undos_left == 2
    assert state.undo() is False                                     # nothing left to undo until you act again

    s = fresh(difficulty='Hardcore')
    engine.execute_decision(engine.current_options()[0])
    assert not state.can_undo() and state.undo() is False

    s = fresh(difficulty='Normal')
    engine.execute_decision(engine.current_options()[0])
    assert state.undo() is True
    engine.execute_decision(engine.current_options()[0])
    assert state.undo() is False                                     # Normal gets exactly one


def test_undo_can_reverse_a_sacking():
    s = fresh(difficulty='Easy')
    s.backbench_opinion = 5.0
    assert engine.submit_budget() == 'sacked' and s.game_over
    assert state.undo() is True and not s.get('game_over') and s.backbench_opinion == 5.0


def test_budget_speech_describes_what_you_changed():
    s = fresh()
    s['bt_income'] = 22
    s['bs_science'] = 5.0
    s['btp_mansion'] = True
    engine.submit_budget()
    sp = s.budget_speech
    assert 'Income tax will rise by 2 points to 22%' in sp['text']
    assert 'Science & research funding will rise by 5%' in sp['text']
    assert 'Mansion Tax' in sp['text'] and 'OBR confirms' in sp['text']
    assert [r[0] for r in sp['reactions']] == ['Shadow Chancellor', 'The City', 'The TUC', 'Institute for Fiscal Studies']
    engine.proceed_to_spring()
    s.backbench_opinion = 60.0
    engine.submit_budget()
    assert 'no changes' in s.budget_speech['text']                  # nothing new this year: last year's rise is not repeated


def test_old_format_saves_are_rejected_politely():
    fresh()
    import json
    data = json.loads(state.export_save())
    data['format'] = 1
    err = state.import_save(json.dumps(data))
    assert err and 'older version' in err


def test_save_roundtrip_keeps_new_state():
    s = fresh('Conservative', scenario='crash2008', spad='hawk', pledges=['income'])
    s.active_request = copy.deepcopy(politics.CABINET_REQUESTS[1])
    text = state.export_save()
    s.clear()
    assert state.import_save(text) is None
    assert (s.scenario, s.spad, s.pledges, s.macro_cycle) == ('crash2008', 'hawk', ['income'], 'Recession')
    assert s.active_request['minister'] == 'Defence Secretary'


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

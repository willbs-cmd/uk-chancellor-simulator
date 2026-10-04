"""Headless engine tests. Run with:  python tests/test_engine.py   (or pytest)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sim  # noqa: E402  (installs the fake session state)
from sim import engine, st, state  # noqa: E402


def test_full_run_and_scorecard():
    r = sim.play('Labour', 'sensible', 'Normal', seed=7, terms=2)
    assert r['term'] >= 1 and st.session_state.history
    data = engine.scorecard()
    assert data['grade'] in 'ABCDF' and data['rows'] and 'UK Chancellor Simulator' in data['share']


def test_same_seed_same_result():
    a = sim.play('Labour', 'random', 'Hardcore', seed=11)
    b = sim.play('Labour', 'random', 'Hardcore', seed=11)
    assert a == b


def test_save_roundtrip():
    sim.play('Conservative', 'random', 'Normal', seed=5)
    snap = {k: st.session_state[k] for k in ('party', 'year', 'block', 'approval', 'headroom', 'steps')}
    text = state.export_save()
    json.loads(text)
    st.session_state.clear()
    assert state.import_save(text) is None
    assert {k: st.session_state[k] for k in snap} == snap


def test_bad_save_rejected():
    assert state.import_save('not json') is not None
    assert state.import_save('{"format": 99}') is not None


def test_delayed_consequences_land():
    sim.new_run('Labour', 'Normal', 3)
    s = st.session_state
    opt = next(o for o in engine.current_options() if o['delayed'])
    engine.execute_decision(opt)
    assert s.pending
    while s.pending and not s.get('game_over') and s.year <= 5:
        if s.active_crisis:
            engine.resolve_crisis(0)
        elif s.block == 3:
            engine.submit_budget(); engine.proceed_to_spring()
        else:
            engine.execute_decision(engine.current_options()[0])
    assert not s.pending


def test_no_option_strictly_dominates():
    assert sim.audit() <= 4   # crude weights; traps are fine, runaway dominant options are not


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

"""Drive app.py end to end with a mocked Streamlit: catches NameErrors and bad state handling in the UI paths.

Run with:  python tests/test_ui_smoke.py   (or pytest). Works whether the tests sit in a tests/ folder or beside app.py.
"""
import pathlib
import runpy
import sys
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE if (HERE / 'app.py').exists() else HERE.parent


class Rerun(Exception):
    pass


class Stop(Exception):
    pass


class FakeState(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v


def make_streamlit(clicks, picks=None):
    """``picks`` maps a widget label to the value it should return (so tests can choose a scenario, advisor, ...)."""
    picks = picks or {}
    st = mock.MagicMock(name='streamlit')
    st.session_state = FakeState()
    st.rerun.side_effect = Rerun
    st.stop.side_effect = Stop
    st.columns.side_effect = lambda spec, **kw: [mock.MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
    st.button.side_effect = lambda label, **kw: (not kw.get('disabled')) and label in clicks
    st.radio.side_effect = lambda label, options, **kw: options[0]
    st.selectbox.side_effect = lambda label, options, **kw: picks.get(label, options[0])
    st.multiselect.side_effect = lambda label, options, **kw: picks.get(label, [])
    st.checkbox.side_effect = lambda *a, **kw: kw.get('value', False)
    st.number_input.side_effect = lambda *a, **kw: kw.get('value', 1)
    st.file_uploader.return_value = None
    st.download_button.return_value = False
    return st


def run_script(st):
    sys.modules['streamlit'] = st
    try:
        sys.modules['altair'] = mock.MagicMock(name='altair')
        for f in ROOT.glob('*.py'):                      # every game module holds a reference to the mock: reload them all
            sys.modules.pop(f.stem, None)
        sys.path.insert(0, str(ROOT))
        try:
            runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
        except (Rerun, Stop):
            pass
    finally:
        sys.path.remove(str(ROOT))


def click_for(s):
    if s.year > 5:
        return {'Continue as Chancellor'}
    if s.get('budget_passed'):
        return {'Proceed to Spring'}
    if s.block == 3 and s.active_crisis is None:
        return {'Submit Budget to the Commons & Lords'}
    if s.active_crisis is not None:
        return {'Resolve Crisis'}
    if s.get('active_request'):
        return {'Refuse Request'}
    return {'Execute Policy'}


def play_ui(picks=None, steps=120):
    st = make_streamlit({'Enter Number 11'}, picks)
    run_script(st)
    s = st.session_state
    assert s.step == 'game'
    seen = set()
    for _ in range(steps):
        if s.get('game_over'):
            break
        if s.get('active_request'):
            seen.add('request')
        if s.get('budget_passed') and s.get('budget_speech'):
            seen.add('speech')
        clicks = click_for(s)
        st.button.side_effect = lambda label, c=clicks, **kw: (not kw.get('disabled')) and label in c
        run_script(st)
        if s.term >= 2 and s.year >= 2:
            break
    return st, seen


def test_full_playthrough():
    st, seen = play_ui()
    s = st.session_state
    assert s.history, 'history should have been recorded'
    assert s.term >= 2 or s.get('game_over'), 'game should reach a new term or an ending'
    assert 'speech' in seen, 'the Budget speech screen should have been shown'


def test_playthrough_with_scenario_advisor_and_pledges():
    st, seen = play_ui({'Starting scenario': 'crash2008', 'Special Advisor': 'enforcer',
                        'Manifesto pledges (optional, up to 3)': ['income', 'nhs']})
    s = st.session_state
    assert s.scenario == 'crash2008' and s.spad == 'enforcer' and s.pledges == ['income', 'nhs']
    assert s.history


def test_undo_button_rolls_back_a_decision():
    st = make_streamlit({'Enter Number 11'}, {})
    run_script(st)
    s = st.session_state
    s.difficulty, s.undos_left = 'Easy', 3             # Easy allows undos
    clicks = {'Execute Policy'}
    st.button.side_effect = lambda label, **kw: (not kw.get('disabled')) and label in clicks
    steps_before = s.steps
    run_script(st)
    assert s.steps == steps_before + 1 and s.checkpoint
    clicks = {s_label for s_label in ['↩️ Undo last action (3 left)']}
    run_script(st)
    assert s.steps == steps_before and s.undos_left == 2


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

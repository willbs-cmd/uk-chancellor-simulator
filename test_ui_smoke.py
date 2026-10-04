"""Drive app.py end to end with a mocked Streamlit: catches NameErrors and bad state handling in the UI paths."""
import pathlib
import runpy
import sys
import types
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent


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


def make_streamlit(clicks):
    st = mock.MagicMock(name='streamlit')
    st.session_state = FakeState()
    st.rerun.side_effect = Rerun
    st.stop.side_effect = Stop

    def columns(spec, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        cols = [mock.MagicMock() for _ in range(n)]
        return cols

    st.columns.side_effect = columns
    st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]

    def button(label, **kw):
        if kw.get('disabled'):
            return False
        return label in clicks

    st.button.side_effect = button
    st.radio.side_effect = lambda label, options, **kw: (options[0] if kw.get('index', 0) is not None or True else None)
    st.selectbox.side_effect = lambda label, options, **kw: options[0]
    st.checkbox.side_effect = lambda *a, **kw: kw.get('value', False)
    st.number_input.side_effect = lambda *a, **kw: kw.get('value', 1)
    st.file_uploader.return_value = None
    st.download_button.return_value = False
    return st


def run_script(st):
    sys.modules['streamlit'] = st
    try:
        sys.modules['altair'] = mock.MagicMock(name='altair')
        for m in ('app', 'engine', 'state', 'budget', 'country', 'scenarios', 'decisions', 'theme', 'achievements'):
            sys.modules.pop(m, None)
        sys.path.insert(0, str(ROOT))
        try:
            runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
        except (Rerun, Stop):
            pass
    finally:
        sys.path.remove(str(ROOT))


def test_full_playthrough():
    st = make_streamlit({'Enter Number 11'})
    run_script(st)
    s = st.session_state
    assert s.step == 'game'
    for _ in range(80):
        if s.get('game_over'):
            break
        if s.year > 5:
            clicks = {'Continue as Chancellor'}
        elif s.get('budget_passed'):
            clicks = {'Proceed to Spring'}
        elif s.block == 3 and s.active_crisis is None:
            clicks = {'Submit Budget to the Commons & Lords'}
        elif s.active_crisis is not None:
            clicks = {'Resolve Crisis'}
        else:
            clicks = {'Execute Policy'}
        st.button.side_effect = lambda label, c=clicks, **kw: (not kw.get('disabled')) and label in c
        run_script_state(st)
        if s.term >= 2 and s.year >= 2:
            break
    assert s.history, 'history should have been recorded'
    assert s.term >= 2 or s.get('game_over'), 'game should reach a new term or an ending'


def run_script_state(st):
    """Re-run the app without wiping session state."""
    run_script(st)

"""Tests for the compact layout components (dashboard strip, summary chips, pledge chips). Run: python test_layout.py"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):                  # works in a tests/ folder or beside the game files
    sys.path.insert(0, str(_p))
import sim  # noqa: E402  (must come first: installs the fake Streamlit)
import politics  # noqa: E402
import theme  # noqa: E402
from sim import budget, st  # noqa: E402
from state import CARDS_ECON, CARDS_POLITICAL, CARDS_TOP  # noqa: E402


def captured(fn, *a, **k):
    """Run a drawing function and return every HTML string it sent to st.markdown."""
    out, orig = [], getattr(st, 'markdown', None)      # the headless stand-in has no markdown(): add one for the call
    st.markdown = lambda body, *x, **kw: out.append(body)
    try:
        fn(*a, **k)
    finally:
        if orig is None:
            del st.markdown
        else:
            st.markdown = orig
    return ''.join(out)


def fresh(**opts):
    sim.new_run('Labour', 'Normal', 1, **opts)
    return st.session_state


def test_dashboard_strip_shows_every_stat_in_two_rows():
    fresh()
    html = captured(theme.render_hud, [('The economy', CARDS_TOP + CARDS_ECON), ('Political capital', CARDS_POLITICAL)], note='note')
    assert html.count("sc-card compact") == 14           # 5 headline + 4 economy + 5 political capital
    assert html.count("class='hud-row'") == 2
    assert "class='hud-note'>note<" in html and html.count('hud-note') == 1
    assert '\n\n' not in html                            # a blank line would end the HTML block and break the layout


def test_a_change_that_rounds_to_zero_is_not_shown_as_minus_zero():
    s = fresh()
    s.prev = dict(s.prev)
    s.prev['approval'] = s.approval + 0.5                # a change of exactly -0.5 on a whole-number stat
    html = captured(theme.render_hud, [('x', CARDS_TOP)])
    assert '-0<' not in html and '+0<' not in html


def test_compact_cards_keep_their_tooltips_and_real_changes():
    s = fresh()
    s.prev = dict(s.prev)
    s.prev['approval'] = s.approval - 5.0
    html = captured(theme.render_hud, [('x', CARDS_TOP)])
    assert 'sc-tip' in html and '+5' in html and 'sc-good' in html


def test_summary_chips_use_the_same_cards():
    html = captured(theme.render_chips, [dict(label='A', value='1', delta='+2', num=2.0), dict(label='B', value='3', inverse=True, num=1.0)])
    assert html.count('sc-card compact') == 2 and 'chip-row' in html and 'sc-bad' in html


def test_pledge_chips_show_kept_risky_and_broken():
    s = fresh(pledges=['income', 'nhs'])
    assert captured(politics.render_pledges, budget.read()).count('pl-ok') == 2
    s['bt_income'] = 25
    html = captured(politics.render_pledges, budget.read())
    assert 'pl-risk' in html and 'pl-ok' in html and 'breaks it' in html
    s.broken_pledges = ['income']
    assert 'pl-broken' in captured(politics.render_pledges, budget.read())
    fresh()
    assert captured(politics.render_pledges, budget.read()) == ''      # no pledges, no clutter


def test_no_flag_emoji_in_the_ui():
    # Windows draws regional-indicator flags as the letters "GB", which looked like a glitch in the tab bar
    for name in ('app.py', 'theme.py', 'budget.py', 'country.py', 'politics.py'):
        assert '\U0001F1EC\U0001F1E7' not in (_HERE / name).read_text(encoding='utf-8'), name


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

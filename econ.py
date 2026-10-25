"""Pure macro maths, shared by the engine's yearly tick and the Budget screen's OBR forecast.

Nothing in here touches Streamlit or the session, so the forecast on the Budget screen is guaranteed to
use exactly the same rules as the real spring tick (it just leaves out crises and political drags).
"""
import imf_outlook

# the global economic cycle nudges growth every year it lasts (the pull towards trend keeps this bounded)
CYCLES = {'Boom': 0.2, 'Stagnation': 0.0, 'Recession': -0.3}


def clip(val, lo, hi):
    return max(lo, min(hi, val))


def game_year(term, year):
    """Absolute year of the run: term 1 year 1 is 1, term 2 year 1 is 6, and so on."""
    return (int(term) - 1) * 5 + int(year)


def step(v, incoming_year=None):
    """Advance the macro economy by one year.

    ``v`` needs: inflation, interest_rate, gilt_yield, growth, debt, deficit, headroom, market_conf, approval;
    ``cycle`` (Boom / Stagnation / Recession) is optional. ``incoming_year`` is the absolute game year being
    entered (used for the IMF anchor). Returns a new dict with the updated values plus ``cred`` (the clipped
    headroom used for fiscal credibility).
    """
    o = dict(v)
    gap = 2.0 - o['inflation']
    o['inflation'] = round(clip(o['inflation'] + 0.25 * gap - 0.08 * (o['interest_rate'] - (o['inflation'] + 1.5)), 0, 12), 2)
    target_rate = o['inflation'] + 1.8
    o['interest_rate'] = round(clip(o['interest_rate'] + max(-0.5, min(0.5, 0.6 * (target_rate - o['interest_rate']))), 0.5, 9), 2)
    gilt_target = o['interest_rate'] - 0.3 + (65 - o['market_conf']) * 0.03 + (o['debt'] - 98.2) * 0.02
    o['gilt_yield'] = round(clip(o['gilt_yield'] + 0.5 * (gilt_target - o['gilt_yield']), 1, 9), 2)
    o['growth'] = round(o['growth'] + 0.2 * (1.2 - o['growth']) - 0.08 * (o['interest_rate'] - 4.5), 2)

    # IMF baseline anchor: player decisions still dominate, but the economy gently converges on the external forecast.
    # Only years the IMF actually covers are anchored (2027-28 for the first term).
    imf = imf_outlook.get(incoming_year) if incoming_year is not None else None
    if imf:
        o['growth'] = round(o['growth'] + 0.20 * (imf['gdp'] - o['growth']), 2)
        o['inflation'] = round(o['inflation'] + 0.15 * (imf['inflation'] - o['inflation']), 2)

    o['growth'] = round(o['growth'] + CYCLES.get(o.get('cycle'), 0.0), 2)

    # Debt as a share of GDP: new borrowing adds to it, nominal growth (real growth + inflation) shrinks it.
    o['debt'] = round(o['debt'] + 0.034 * (o['deficit'] + max(0.0, -o['headroom']) * 0.5)
                      - o['debt'] * (o['growth'] + o['inflation']) / 100.0, 1)
    o['headroom'] = round(o['headroom'] + 2.0 * (o['growth'] - 1.0), 1)
    o['deficit'] = round(o['deficit'] - 2.0 * (o['growth'] - 1.0), 1)   # a stronger economy narrows the deficit too

    cred = clip(o['headroom'], -30, 20)
    mkt_target = 55 + (cred if cred > 0 else 2.0 * cred) + (o['approval'] - 50) * 0.1
    o['market_conf'] = round(clip(o['market_conf'] + 0.25 * (mkt_target - o['market_conf']), 0, 100), 1)
    o['cred'] = cred
    return o

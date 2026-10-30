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
    # A sovereign risk premium makes gilt markets react to the whole fiscal picture,
    # not just the policy rate. The premium builds gradually and is capped to keep
    # the simulation playable rather than creating an instant debt spiral.
    nominal_gdp_bn = max(500.0, float(o.get('gdp_trillion', 3.0)) * 1000.0)
    deficit_ratio = max(0.0, float(o['deficit'])) / nominal_gdp_bn
    debt_pressure = max(0.0, float(o['debt']) - 90.0) * 0.012
    deficit_pressure = max(0.0, deficit_ratio - 0.035) * 18.0
    confidence_pressure = max(0.0, 50.0 - float(o['market_conf'])) * 0.025
    risk_premium = round(clip(debt_pressure + deficit_pressure + confidence_pressure, 0.0, 2.5), 2)
    gilt_target = (o['interest_rate'] - 0.3 + (65 - o['market_conf']) * 0.03
                   + (o['debt'] - 98.2) * 0.02 + risk_premium)
    o['gilt_yield'] = round(clip(o['gilt_yield'] + 0.5 * (gilt_target - o['gilt_yield']), 1, 10), 2)
    o['gilt_risk_premium'] = risk_premium
    o['debt_interest_bill'] = round(10.7 * (1 + 0.4 * (o['gilt_yield'] / 4.7 - 1)
                                              + (o['debt'] / 98.2 - 1)), 1)
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
    # The Treasury module applies the actual tax-receipt dividend from nominal GDP growth
    # at the annual spring update. Do not add a second abstract growth bonus here.

    cred = clip(o['headroom'], -30, 20)
    mkt_target = 55 + (cred if cred > 0 else 2.0 * cred) + (o['approval'] - 50) * 0.1
    o['market_conf'] = round(clip(o['market_conf'] + 0.25 * (mkt_target - o['market_conf']), 0, 100), 1)
    o['cred'] = cred
    return o

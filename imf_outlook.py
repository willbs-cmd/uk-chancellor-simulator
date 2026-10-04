"""IMF UK macroeconomic baseline used by the Chancellor Simulator.

Source: IMF, United Kingdom 2026 Article IV Consultation, July 2026.
These are IMF staff projections, not game outcomes.  Fiscal debt in the IMF
table is PSNFL, so the simulator deliberately does not map it directly onto
its own national-debt variable.
"""

IMF_SOURCE = "IMF 2026 Article IV Consultation (July 2026)"

OUTLOOK = {
    2026: dict(gdp=1.0, inflation=3.2, unemployment=5.6, deficit=-4.0, debt=83.9),
    2027: dict(gdp=1.3, inflation=2.4, unemployment=5.3, deficit=-3.3, debt=84.4),
    2028: dict(gdp=1.7, inflation=2.0, unemployment=4.8, deficit=-2.8, debt=84.7),
}

def year_for_game(game_year):
    """Map game year 1..5 onto calendar years starting in 2026."""
    return 2025 + int(game_year)

def get(game_year):
    return OUTLOOK.get(year_for_game(game_year))

def rows():
    return [
        {
            "Year": year,
            "Real GDP growth": f"{v['gdp']:.1f}%",
            "CPI inflation (avg)": f"{v['inflation']:.1f}%",
            "Unemployment": f"{v['unemployment']:.1f}%",
            "Public balance": f"{v['deficit']:.1f}% GDP",
            "PSNFL": f"{v['debt']:.1f}% GDP",
        }
        for year, v in OUTLOOK.items()
    ]

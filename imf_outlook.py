"""IMF UK macroeconomic baseline loaded from data/imf_uk_baseline.json.

To refresh the baseline, update the JSON file's vintage, publication date, source notes,
and year values. These are external baseline projections, not game outcomes.
"""
import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent / "data" / "imf_uk_baseline.json"
with _DATA_PATH.open(encoding="utf-8") as _handle:
    _DATA = json.load(_handle)

IMF_SOURCE = f"IMF { _DATA['vintage'] } WEO"
IMF_SOURCE_URL = _DATA["source_url"]
IMF_VINTAGE = _DATA["vintage"]
IMF_PUBLISHED = _DATA["published"]
OUTLOOK = {int(year): dict(values) for year, values in _DATA["years"].items()}


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
            "General government gross debt": f"{v['debt']:.1f}% GDP",
        }
        for year, v in OUTLOOK.items()
    ]

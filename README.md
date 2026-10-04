# 🏛️ UK Chancellor Simulator (Hardcore Mode)

A Streamlit game: run the Treasury for five years, survive crises, deliver Budgets, keep your party and the
Prime Minister on side, then face the electorate.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features
- **Seven parties, three difficulties** (Easy / Normal / Hardcore) and a **seed** so a run can be replayed or shared.
- **Hidden ideology tags**: options are shuffled and unlabelled (turn tags on in the setup screen). Your MPs still
  know what is in your party's tradition.
- **Delayed consequences**: some policies come back to bite (or pay off) a couple of actions later. See the
  *History* tab for what is on the horizon.
- **Living economy**: inflation, Bank Rate, gilt yields, growth and debt move by themselves each spring; breaching
  your fiscal rules costs approval and market confidence.
- **Dashboard**: stat cards with hover tooltips and sparklines, State of the Nation grade, party-coloured poll
  chart, event log, newspaper front pages, Sir Humphrey reacting to what you did.
- **Budget**: tax and spending sliders, revenue/spending pies; unapplied changes apply when you submit.
- **Endings, achievements and a scorecard** after every election, with copy-and-paste share text.
- **Save / load** as a JSON file.

## Project layout
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI only |
| `engine.py` | All game rules (no UI): decisions, crises, budget, economy tick, polls, elections |
| `state.py` | Session defaults, difficulty, dashboard card definitions, history log, save/load |
| `decisions.py` / `scenarios.py` | Policy decisions (+ delayed consequences) and crises |
| `country.py` / `budget.py` | State-of-the-Nation stats and the Budget screen |
| `achievements.py` | Endings and achievements |
| `theme.py` | CSS and HTML components |
| `sim.py` | Headless balance testing |

## Balance testing
```bash
python sim.py audit              # score every option, flag runaway dominant ones
python sim.py run 100 Hardcore   # play 100 full terms per strategy, print win/sack rates
python tests/test_engine.py      # engine tests
python tests/test_ui_smoke.py    # (via pytest) drives app.py end to end with a mocked Streamlit
```
Tuning knobs: `state.DIFFICULTY`, `engine.CRED_*`, `country.APPROVAL_FEEDBACK`, and the numbers in `decisions.py`.


## IMF economic outlook

The simulator includes a three-year IMF baseline based on the IMF's July 2026
United Kingdom Article IV consultation. The in-game **IMF Outlook** tab shows
real GDP growth, CPI inflation, unemployment, the public balance and PSNFL for
2026–2028. The annual macro tick gently anchors growth and inflation toward
that baseline while preserving player-driven divergence.

The IMF figures are an external baseline, not a forecast of an individual
playthrough.

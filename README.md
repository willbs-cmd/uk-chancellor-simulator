# UK Chancellor Simulator

A Streamlit political-economy game. Lead a government through policy decisions, crises, the Budget, Parliament and a general election.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Edit or mod game content

The game loads player-facing content from `data/` files. You can add or rebalance policies, crises and tax/spending choices without editing their Python modules:

- `data/decisions.json` — policy topics, five approaches per topic, effects, delayed consequences and Sir Humphrey's reactions.
- `data/crises.json` — crisis text and response options.
- `data/policies.json` — tax sliders, revenue schemes, spending departments, spending schemes and game-balance coefficients.
- `data/imf_uk_baseline.json` — fixed-vintage IMF UK baseline and source metadata.
- `data/balance_thresholds.json` — schema requirements and balance-regression guardrails.
- `data/README.md` — data structures, editing rules and instructions for updating the IMF baseline.

The JSON is loaded at application startup. Restart the local app after changing data files. When using Streamlit Cloud, commit the changed file to the repository so the app can redeploy.

## Headless balance checks

Run `python sim.py check` to validate the data contracts and simulate a set of games for each party against the broad expected win/sacking-rate thresholds. Increase the sample with `python sim.py check 50 Hardcore`.

Run `python sim.py audit` to score policy options for potential balance outliers. Run `python sim.py run 100 Hardcore` for a broader strategy comparison.

The GitHub Actions workflow runs the regression check whenever Python modules or files in `data/` change.

## Interpretation notes

The IMF WEO table is a fixed external baseline used to nudge the game's yearly growth and inflation path; it is not a forecast of the player's playthrough. Fiscal effects, political capital, gilt auctions, debt maturity and many policy costings are simplified game mechanics, not official Treasury or Office for Budget Responsibility estimates.

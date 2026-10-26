# UK Chancellor Simulator

A Streamlit political-economy game. Play the Chancellor's Office directly, or start as a backbench MP in Career Mode and work towards ministerial office, the Chancellorship or Prime Minister.

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
- `data/career_content.json` — Career Mode roles, action choices, promotion requirements and ambition bonuses.
- `data/README.md` — data structures, editing rules and instructions for updating the IMF baseline.

The JSON is loaded at application startup. Restart the local app after changing data files. When using Streamlit Cloud, commit the changed file to the repository so the app can redeploy.

## Headless balance checks

Run `python sim.py check` to validate the data contracts and simulate a set of games for each party against the broad expected win/sacking-rate thresholds. Increase the sample with `python sim.py check 50 Hardcore`.

Run `python sim.py audit` to score policy options for potential balance outliers.

## Career Mode

At game setup, choose **Political Career** to begin as a fictional backbench MP. You choose a name, a fictional constituency and a starting ambition. Each parliamentary session gives you two actions; three sessions make a year, and a general election occurs after five years. Actions develop constituency support, party trust, parliamentary influence, public profile, policy expertise and integrity. Promotions depend on experience and those attributes, so you can pursue the Parliamentary Private Secretary route or the select-committee route before moving into ministerial office. Later roles unlock different actions for junior ministers, Ministers of State, Secretaries of State, the Chancellor and Prime Minister. Losing your constituency seat ends that career save.

Career roles, actions and promotion thresholds are editable in `data/career_content.json`. Career Mode is an initial playable system with abstracted political outcomes; it does not yet simulate every real department or a full party leadership contest. Run `python sim.py run 100 Hardcore` for a broader strategy comparison.

The GitHub Actions workflow runs the regression check whenever Python modules or files in `data/` change.

## Interpretation notes

The IMF WEO table is a fixed external baseline used to nudge the game's yearly growth and inflation path; it is not a forecast of the player's playthrough. Fiscal effects, political capital, gilt auctions, debt maturity and many policy costings are simplified game mechanics, not official Treasury or Office for Budget Responsibility estimates.

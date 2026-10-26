# UK Chancellor Simulator

A pair of Streamlit political games sharing data and common mechanics: the Chancellor's Office simulator and a separate MP Political Career game.

## Run locally

```bash
python -m pip install -r requirements.txt

# Game 1: Chancellor's Office simulator
streamlit run app.py

# Game 2: separate MP Political Career simulator
streamlit run mp_career_app.py
```

## Deploying the two games separately

Streamlit Community Cloud can host these as two separate apps from the same repository. Create one app with **Main file path** set to `app.py`, then create another app pointing at `mp_career_app.py`. They will have separate app URLs, browser sessions and player saves. Each app has its own configured entry point.

## Edit or mod game content

The game loads player-facing content from `data/` files. You can add or rebalance policies, crises and tax/spending choices without editing their Python modules:

- `data/decisions.json` — policy topics, five approaches per topic, effects, delayed consequences and Sir Humphrey's reactions.
- `data/crises.json` — crisis text and response options.
- `data/policies.json` — tax sliders, revenue schemes, spending departments, spending schemes and game-balance coefficients.
- `data/imf_uk_baseline.json` — fixed-vintage IMF UK baseline and source metadata.
- `data/balance_thresholds.json` — schema requirements and balance-regression guardrails.
- `data/career_content.json` — Career Mode roles, action choices, promotion requirements and ambition bonuses.
- `data/constituencies_2024.json` — official names, nations and codes for all 650 Westminster constituencies.
- `data/career_divisions.json` — simulated Commons divisions, party-whip positions and local-priority categories.
- `data/README.md` — data structures, editing rules and instructions for updating the IMF baseline.

The JSON is loaded at application startup. Restart the local app after changing data files. When using Streamlit Cloud, commit the changed file to the repository so the app can redeploy.

## Headless balance checks

Run `python sim.py check` to validate the data contracts and simulate a set of games for each party against the broad expected win/sacking-rate thresholds. Increase the sample with `python sim.py check 50 Hardcore`.

Run `python sim.py audit` to score policy options for potential balance outliers.

## Career Mode

Open the separate **MP Political Career** app to begin as a fictional backbench MP. You choose a name, a real 2024 Westminster constituency, a local campaign priority and a starting ambition. Each parliamentary session gives you two actions; three sessions make a year, and a general election occurs after five years. Actions develop constituency support, party trust, parliamentary influence, public profile, policy expertise and integrity. Promotions depend on experience and those attributes, so you can pursue the Parliamentary Private Secretary route or the select-committee route before moving into ministerial office. Later roles unlock different actions for junior ministers, Ministers of State, Secretaries of State, the Chancellor and Prime Minister. Losing your constituency seat ends that career save.

Career roles, actions and promotion thresholds are editable in `data/career_content.json`. Career Mode is an initial playable system with abstracted political outcomes; it does not yet simulate every real department or a full party leadership contest. Run `python sim.py run 100 Hardcore` for a broader strategy comparison.

The GitHub Actions workflow runs the regression check whenever Python modules or files in `data/` change.

## Interpretation notes

The IMF WEO table is a fixed external baseline used to nudge the game's yearly growth and inflation path; it is not a forecast of the player's playthrough. Fiscal effects, political capital, gilt auctions, debt maturity and many policy costings are simplified game mechanics, not official Treasury or Office for Budget Responsibility estimates.

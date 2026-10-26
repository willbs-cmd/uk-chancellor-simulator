# Editable game data

The game reads these JSON files at startup. You can change game content and balance values without editing Python modules.

## Files

- `decisions.json`: policy topics, their five player-facing options, effects, ideology order, Sir Humphrey reactions, and delayed consequences.
- `crises.json`: crisis text and response options. Each response is a two-item array: `[label, effect_object]`.
- `policies.json`: tax controls, tax schemes, spending departments, spending schemes, department nudges, and baseline fiscal parameters.
- `imf_uk_baseline.json`: the external IMF World Economic Outlook vintage, source metadata and UK macroeconomic baseline values.
- `balance_thresholds.json`: required content counts and broad win/sacking-rate guardrails for regression checks.

## Editing a policy decision

Each entry in `decisions.json` has `year`, `block`, and `decision`. The game expects five option labels and five effect objects in the same order as the `ideologies` array. Effects are simplified deltas to game stats, e.g. `"approval": 2` or `"headroom": -1.5`. Use finite numbers and a `message` in each effect so the player gets feedback.

Delayed consequences are keyed by the same year/block and contain option indexes as strings (`"0"` through `"4"`). Each delayed entry uses `after`, `title`, `text`, `warn` and `fx`.

## Editing a crisis

The top-level `crises` object is keyed by a stable crisis ID. Each crisis needs `title`, `humphrey`, and an `opts` array. Each option's effect object uses the same stat keys as policy decisions. Keep at least two responses per crisis.

## Editing Budget controls

`policies.json` holds the numeric model parameters. The `base`, `per`, and `decay` fields in tax definitions are simplified game balance rules; they are not official Treasury costings. Spending and one-off schemes are similarly stylised. If you add a tax lever, preserve its stable key because saves and widget state use that key.

## Refreshing the IMF baseline

When a new IMF WEO edition is released, update `imf_uk_baseline.json`:
1. Update `vintage`, `published`, the official IMF `source_url`, and any notes.
2. Replace the values under `years` using one consistent WEO vintage.
3. Keep the series definitions clear: `deficit` is general government net lending/borrowing (% GDP); `debt` is general government gross debt (% GDP), not PSNFL and not the game's national-debt statistic.

The baseline is intentionally stored locally in the repository: the game does not silently fetch changing external numbers at runtime.

## Regression check

Run `python sim.py check` after changing content. It checks content shape and non-finite effects, then runs a deterministic sample of games against broad per-party win and sacking thresholds. Use `python sim.py check 50 Hardcore` to sample more seeds. A failure means investigate the balance change; it does not automatically mean the content is wrong.

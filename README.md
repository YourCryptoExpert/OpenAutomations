# OpenAutomations

Hourly automations. Current set:

| # | Job | Script | Output | Schedule |
|---|-----|--------|--------|----------|
| 1 | Robinhood trending crypto prices | `scripts/robinhood_trending_crypto.py` | `data/robinhood_trending_crypto/<UTC-stamp>.csv`, `latest.json`, `history.jsonl` | every hour |

## What it does
1. Pulls the live tradable list from Robinhood (`nummus.robinhood.com/currency_pairs`, `tradability == tradable`, ~90 coins).
2. Pulls live Robinhood prices (`api.robinhood.com/marketdata/forex/quotes`, bid/ask/mark/open/high/low).
3. Ranks "trending" = largest absolute % move (mark vs open). Saves a timestamped CSV + `latest.json` + appended `history.jsonl`.

Stdlib only — no pip install needed.

## Run manually
```powershell
python scripts/run_all.py
# or single job:
python scripts/robinhood_trending_crypto.py --top 15
```

## Schedule: GitHub Actions (runs even when PC is off)
1. `git add .; git commit -m "add hourly crypto automation"; git push`
2. Actions workflow `.github/workflows/hourly-automations.yml` runs at :05 UTC hourly and commits `data/`.

## Schedule: this PC only (Windows Task Scheduler, automations + push)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/Register-HourlyTask.ps1
```
This registers `scripts/Run-Hourly.ps1`, which runs the automations and then
pushes `data/` to GitHub — every hour, while this PC is on.

## Push script details
`scripts/Push-ToGitHub.ps1` commits `data/` only when it changed and pushes
the current branch — never force-pushes. Safe to run by hand any time:

One-time setup (not hourly):
```powershell
gh auth login
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git add -A; git commit -m "initial commit"
gh repo create OpenAutomations --public --source=. --push
```

Manual push test (safe: does nothing when there is nothing new):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/Push-ToGitHub.ps1
# to also push script/workflow changes: add -AddAll
```

## Add a new hourly automation
1. Add `scripts/<name>.py` (exit 0/1, writes under `data/<name>/`).
2. Register it in `scripts/run_all.py` `JOBS`.
3. Both schedulers pick it up automatically.

---
name: unity-headless-sim
description: Add a headless, seeded, batch Monte Carlo simulation mode to a Unity game, so thousands of full runs play out with no rendering and the results come back as win rates with 95% confidence intervals. Covers auditing whether the project can be stepped deterministically, adding an external fixed-step driver, a bot runner that plays many runs per process, parallel batch launch with disjoint seeds, aggregation, determinism checks, and an optional decision-replay model. Use when the user wants to measure balance, win rate, difficulty, or build strength in a Unity project by running many games instead of playtesting; mentions Imaginary Space, 虛數空間, 虚数空间, headless, batchmode, nographics, Monte Carlo, mass simulation, bot runs, seeds, or "run 10,000 games".
---

# Imaginary Space (虛數空間): Unity headless simulation

Run the game's own code thousands of times with no rendering, a bot at the controls, and a fixed random seed per run. Collect one line per run, then aggregate into win rates with confidence intervals.

The rule that makes this work: **use the game's real simulation code; never write a second copy of the rules** (in Python or anywhere else). A copy drifts from the game silently, and every content change has to be made twice.

Measured on the project this came from (a 2D survivor-like, all logic in C#, no physics): a 15-minute run takes 2 to 3 seconds headless; 10 parallel processes finish about 1,000 runs in under 6 minutes.

## Files in this skill

| Path | What it is |
|---|---|
| `templates/HeadlessRunner.cs` | MonoBehaviour that parses command-line flags, steps the sim inside a per-frame time budget, plays many runs per process, writes `runs.txt` |
| `templates/IHeadlessSim.cs` | The small interface the game implements for the runner |
| `templates/GameLoopPatch.cs` | Before/after example of splitting `Update` so the sim can be stepped from outside |
| `scripts/audit_unity.py` | Scans a Unity project for things that break headless stepping or determinism |
| `scripts/sim_batch.py` | Launches the built player in parallel with disjoint seeds, aggregates `runs.txt`, checks determinism |
| `references/pitfalls.md` | Silent failures found in practice, and how each one showed up |
| `references/decision-model.md` | Optional layer: replay recorded decision timelines thousands of times per second to test pick/draft rules |

Copy templates into the user's project and adapt them; do not reference them from the skill folder.

## Workflow

Do the steps in order. Each step ends with a check; do not move on until it passes.

### 1. Audit fitness

Run `python scripts/audit_unity.py <UnityProjectRoot>/Assets` and read the report with the user. Headless stepping works when gameplay state advances only through code you call with an explicit `dt`. These need work first, or rule the approach out:

- **Physics** (`Rigidbody`, `Physics2D`, `OnCollisionEnter`, `FixedUpdate`): physics advances with Unity's clock, not your step. Workable only with `Physics.simulationMode = SimulationMode.Script` and calling `Physics.Simulate(dt)` inside the step.
- **Animator, Timeline, coroutines, `WaitForSeconds`, `Invoke`, DOTween** driving gameplay: they follow Unity time. Move gameplay timing into your own timers. Pure visuals can stay.
- **`Time.time`, `Time.deltaTime` read inside gameplay code**: replace with the sim's own clock and the `dt` passed in.
- **Gameplay in many `Update` methods across objects**: needs a single entry point that ticks everything in a known order.
- **More than one RNG** (`System.Random` instances, `UnityEngine.Random`, `Guid`, hash of object IDs): pick one and seed it per run.

Tell the user plainly if the project does not fit. A partial port gives numbers that look real and are not.

### 2. Split the game loop

Find where gameplay advances each frame. Make it callable from outside with a fixed `dt`, and add a flag that stops the normal frame loop from stepping it. See `templates/GameLoopPatch.cs`:

- `Sim(float dt)` advances everything gameplay-related by `dt` seconds.
- Normal play slices the frame time into steps of at most `MaxStep` and calls `Sim` for each. Headless mode calls `SimStep(MaxStep)` directly. **Both modes must use the same `MaxStep`**, or their results will not match.
- Anything that affects gameplay and currently lives in `Update` outside `Sim` must move into `Sim`. A common one: the camera. If abilities target "enemies on screen", the camera position is gameplay state; follow the player inside `SimStep`.

Check: normal play still feels identical.

### 3. Add the runner

Copy `templates/IHeadlessSim.cs` and `templates/HeadlessRunner.cs`. Implement `IHeadlessSim` on the game (or a thin adapter):

- `BeginRun(seed)`: restore persistent data to the snapshot, reset every per-run field, seed the RNG, start a run.
- `NeedsDecision` / `Decide()`: menus that pause the sim (level-up picks, shops, card drafts) are answered immediately by the bot.
- `Think()`: the bot's steering, called once before every step.
- `Step(dt)`, `IsOver`, `WriteResult(StringBuilder)`.

Result lines are space-separated `key=value`, starting with `RUN`. Keep values free of spaces. Always include `won=0|1` and `t=<seconds survived>`; add whatever the user wants to compare (level, kills, damage taken, cause of death, time of key milestones, final build).

Launch command (Windows example):

```
Game.exe -batchmode -nographics -headless -runs 20 -seed 1000 -out C:\sim\p00 -logFile C:\sim\p00\player.log [game flags]
```

Check: one process with `-runs 3` writes three `RUN` lines and exits by itself.

### 4. Prove determinism

`python scripts/sim_batch.py determinism --exe <player> --seed 42 [-- game flags]` runs the same seed three times and runs a 3-run batch, then compares lines with the timing fields removed. Both must hold:

- the same seed gives the same line every time;
- run N of a multi-run process equals a fresh process started at that seed.

If the first fails, something draws random numbers outside the sim step or reads wall-clock time. If only the second fails, some state survives between runs; fix `BeginRun`. See `references/pitfalls.md`.

### 5. Validate against normal play

Run the same scenario both ways: headless, and the existing sped-up autoplay or human-paced build if there is one. Compare win rate and a few mid-run numbers (level and kills at 5 and 10 minutes). Differences inside two standard errors count as a match. A headless bot that re-plans every step reacts faster than a bot that thinks once per rendered frame; give both the same think interval before comparing.

### 6. Batch and aggregate

```
python scripts/sim_batch.py run --exe <player> --grid map=0,1,2 diff=0,1,2 --runs 100 --per-proc 20 --jobs 10 --out sim_out -- -meta max
```

- Every `--grid` cell runs `--runs` games, split across processes of `--per-proc` games each, with non-overlapping seed ranges.
- `--jobs` defaults to CPU threads minus 4, capped at 10, so the machine stays usable.
- No `--seed` means a random start seed, printed in the summary. Pass it back to reproduce the batch exactly. Fixed seeds hide luck: a batch that happens to be easy is easy every rerun.
- Output: a table per cell (runs, win rate, Wilson 95% interval, median time, median of any numeric field you pass with `--fields`) and `summary.csv`.

`python scripts/sim_batch.py summarize sim_out --by map,diff` re-aggregates an existing folder.

### 7. Report honestly

- Give intervals, not single numbers. With 100 runs a 50% win rate is roughly 40% to 60%.
- **The bot is not a player.** On the source project, switching between three bot policies moved the win rate by 36 to 58 points for six of eight characters. Absolute rates need calibration against real players. Comparisons (before vs after a change, character A vs B) are trustworthy only with the same bot policy and settings.
- State the build and settings the numbers came from. A stale player binary is the most common wrong result.

## Optional: decision-replay model

When the question is "what if the pick rules changed" (card weights, slot limits, offer counts), a full sim is overkill. Record, per run, when each decision happened; then replay those timelines in a small script that reimplements only the offer-and-pick rules. It runs thousands of runs per second. Read `references/decision-model.md` before building one; it has the accuracy limits.

## Pitfalls

Read `references/pitfalls.md` before step 3. The short list:

- Random draws in per-frame code (screen shake, particles, UI) break determinism silently.
- Per-run fields not reset in `BeginRun` leak into the next run. One case: a bot think-timer left at 900 s made the bot stand still for 15 minutes from the second run on, and the win rate still looked plausible.
- Persistent data (unlocks, upgrades, save file) changed by run 1 affects run 2. Snapshot it before the first run and restore before each.
- `-nographics` may ignore `-screen-width`/`-screen-height`. If gameplay depends on screen aspect, set it in code.
- `Update`-only logic runs once per rendered frame, which in headless mode can be tens of seconds of game time.

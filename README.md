# unity-headless-sim

**Play your Unity game thousands of times with no rendering, and get win rates you can trust.**

English ｜ [繁體中文](README.zh-TW.md) ｜ [简体中文](README.zh-CN.md)

A Claude Code skill. It walks Claude through adding a headless simulation mode to your Unity project: a bot plays, every run has its own fixed seed, many processes run in parallel, and the results come back as win rates with 95% confidence intervals. The simulation is your game's own C# code, not a second copy of the rules.

> Needs Claude Code, a Unity project and Python 3.8+. Claude edits your project's code, so review the changes like any other pull request. Tested with Unity 6 on Windows only.

[Quick start](#quick-start) · [Example](#example) · [Results from the source project](#results-from-the-source-project) · [Limits](#limits)

## Why use it

- **Thousands of runs instead of a handful.** On the source project a 15-minute run takes 2 to 3 seconds headless.
- **No second rulebook.** Writing the rules again in Python drifts from the game silently. Here the game itself runs, so a balance change needs no second edit.
- **Reproducible.** The same seed replays the same run, so a strange result can be opened and watched.
- **Numbers with error bars.** Every win rate comes with a Wilson 95% interval, so you can tell a real change from luck.
- **Says when it won't fit.** Claude audits the project first. Physics, coroutines or Animator driving gameplay are reported before any code changes.

## Quick start

Inside Claude Code:

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

Or copy `skills/unity-headless-sim/` into `~/.claude/skills/` (all projects) or `<project>/.claude/skills/` (one project).

Then open your Unity project in Claude Code and ask, for example: "Add a headless simulation mode so I can measure win rates per difficulty."

## Example

1. **Audit.** Claude runs `audit_unity.py` over `Assets/` and lists what blocks fixed-step play: `Time.deltaTime` in gameplay, unseeded `Random`, logic spread across `Update` methods.
2. **Patch.** It splits your game loop so the simulation can be stepped from outside, then adds `HeadlessRunner.cs` and a small adapter that lets the bot play and answer level-up menus.
3. **Prove determinism.** `sim_batch.py determinism` runs one seed three times, plus a 3-run process. All results must match.
4. **Batch.** `sim_batch.py run --grid map=0,1,2 diff=0,1,2 --runs 100` launches the player in parallel and prints win rate, interval and median survival time per map and difficulty, plus `summary.csv`.

## What's inside

```
skills/unity-headless-sim/
  SKILL.md                    the workflow Claude follows
  templates/
    IHeadlessSim.cs           interface your game implements
    HeadlessRunner.cs         runner: -headless -runs -seed -out -maxtime -think
    GameLoopPatch.cs          before/after example of the game loop split
  scripts/
    audit_unity.py            scans Assets/ for blockers
    sim_batch.py              run / summarize / determinism
  references/
    pitfalls.md               silent failures seen in practice
    decision-model.md         optional replay model for card and draft rules
```

The scripts use only the Python standard library and work without Claude:

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## Results from the source project

The skill was extracted from a 2D survivor-like built in Unity 6, where all gameplay is plain C#. Measured on an i7-14700 (28 threads) in November 2026:

- One 15-minute run: 2 to 3 seconds headless, plus about 5 seconds of process start and exit.
- 1,008 runs with 10 processes at once: 5 minutes 38 seconds.

How much the bot matters: eight characters, three bot policies, 360 runs per cell, same seeds (2026-11-16). Characters are anonymized.

| Character | Re-plans every step | Reacts every 0.25 s | Random card picks |
|---|---|---|---|
| A | 99.2% | 96.7% | 81.1% |
| B | 96.9% | 58.9% | 68.3% |
| C | 95.3% | 81.4% | 55.0% |
| D | 86.7% | 68.9% | 28.9% |
| E | 83.1% | 54.2% | 46.9% |
| F | 77.2% | 65.0% | 34.4% |
| G | 52.2% | 12.2% | 48.1% |
| H | 32.8% | 6.4% | 26.9% |

- For six of the eight characters, the bot policy alone moved the win rate by 36 to 58 points.
- The two ends held: A was strongest and H weakest under all three policies. The middle reordered.
- A slower bot hurt B and G most; random picks hurt D and F most. Each policy exposes a different weakness.

## Limits

- Best fit: gameplay in plain C#, ticked from one place. Gameplay driven by Unity physics, Animator, Timeline, coroutines or tweens has to move onto your own step first.
- The bot is not a player. Use the numbers to compare (before and after a change, A against B) under one bot policy, and calibrate absolute rates against real players.
- The batch script is cross-platform, but macOS and Linux players have not been tried.
- Determinism holds only if nothing outside the simulation step draws from the gameplay random generator. `references/pitfalls.md` lists the cases that broke it on the source project.

## Docs

- [SKILL.md](skills/unity-headless-sim/SKILL.md): the full workflow, step by step
- [pitfalls.md](skills/unity-headless-sim/references/pitfalls.md): silent failures and how each one showed up
- [decision-model.md](skills/unity-headless-sim/references/decision-model.md): replaying decision timelines thousands of times per second, and its accuracy limits

## License

[MIT](LICENSE)

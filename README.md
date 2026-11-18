# unity-headless-sim

**A Claude Code skill that adds a headless Monte Carlo mode to a Unity game.**

English ｜ [繁體中文](README.zh-TW.md) ｜ [简体中文](README.zh-CN.md)

Playtesting gives you a handful of runs. This skill helps Claude turn your game into something that plays thousands of runs with no rendering, a bot at the controls and a fixed seed per run, then reports win rates with 95% confidence intervals. It runs your game's own code, not a rewrite of the rules.

It came out of a code-driven 2D survivor-like built in Unity 6. There, a 15-minute run takes 2 to 3 seconds headless, and 10 parallel players finish about 1,000 runs in under 6 minutes.

## What Claude does with it

1. **Audits the project** for things that break fixed-step, deterministic play: physics, coroutines and Animator driving gameplay, `Time.deltaTime` in game logic, unseeded RNGs, logic spread across many `Update` methods.
2. **Splits the game loop** so the simulation can be stepped from outside with a fixed `dt`, sharing one step size with normal play.
3. **Adds a runner** (`HeadlessRunner.cs`) that plays many runs per process, answers menus with the bot, restores the save between runs and writes one `RUN key=value ...` line per run.
4. **Proves determinism**: the same seed gives the same run, and run N of a batch matches a fresh process at that seed.
5. **Runs batches** in parallel with disjoint seed ranges and aggregates them into a table and `summary.csv`.
6. **Optionally builds a decision-replay model** that answers "what if the card rules changed" thousands of runs per second.

## Install

As a plugin, inside Claude Code:

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

Or copy `skills/unity-headless-sim/` into `~/.claude/skills/` (all projects) or `<project>/.claude/skills/` (one project).

Then ask Claude something like "add a headless simulation mode so I can measure win rates" in your Unity project.

## What's inside

```
skills/unity-headless-sim/
  SKILL.md                    workflow Claude follows
  templates/
    IHeadlessSim.cs           interface your game implements
    HeadlessRunner.cs         command-line runner (-headless -runs -seed -out -maxtime -think)
    GameLoopPatch.cs          before/after example of the game loop split
  scripts/
    audit_unity.py            scans Assets/ for blockers
    sim_batch.py              run / summarize / determinism
  references/
    pitfalls.md               silent failures seen in practice
    decision-model.md         the optional replay model and its accuracy limits
```

The scripts need Python 3.8+ and nothing else. You can use them without Claude:

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## Limits

- Best fit: games whose gameplay is plain C# ticked from one place. Gameplay driven by Unity physics, Animator, Timeline, coroutines or tweens needs to be moved onto your own step first; Claude will say so after the audit instead of producing numbers that only look right.
- The bot is not a player. On the source project, three bot policies gave the same character win rates 30 to 60 points apart. Use the numbers to compare (before vs after a change, A vs B) under one bot policy, and calibrate absolute rates against real players.
- Tested on Windows with Unity 6. The batch script is cross-platform, but macOS and Linux players have not been tried.

## License

MIT

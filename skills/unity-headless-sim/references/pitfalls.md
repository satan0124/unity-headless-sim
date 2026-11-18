# Pitfalls

Every item here produced numbers that looked normal. None of them threw an error. Check each one when adding headless mode, and again when results surprise you.

## Determinism

**Random draws outside the sim step.** Screen shake, particle jitter, idle animations and UI effects often call `UnityEngine.Random` every rendered frame. Headless mode renders a different number of frames per run depending on machine load, so the gameplay RNG sequence shifts and the same seed gives a different run. Fix: skip those effects when stepping externally, or give them their own `System.Random` that gameplay never touches.

How it showed up: the determinism check passed on an idle machine and failed while another batch was running.

**Reading wall-clock or Unity time in gameplay.** `Time.time`, `Time.deltaTime`, `DateTime.Now` and `Stopwatch` inside gameplay make results depend on how fast the machine runs. Use the step's `dt` and the sim's own clock.

**Iteration order that depends on memory.** `HashSet` and `Dictionary` enumeration order over objects that use default hash codes, or sorting with an unstable comparer on equal keys, can differ between processes. Use lists, or sort by a stable ID.

## State leaking between runs

**Runner fields not reset.** Anything the bot or runner keeps across frames must be reset at the start of each run. Real case: the bot's "next think time" stayed at about 900 seconds from the previous run, so with a think interval on, the bot did not move for the first 15 minutes of every run after the first. Win rate dropped to 5%, which looked like a hard difficulty, not a bug. The determinism check (run 3 of a multi-run process vs a fresh process) catches this.

**Game state not reset by the game's own "start run".** Statics, caches, pooled objects with leftover fields, and singletons set during a run. Same check catches it.

**Persistent data.** Unlocks, currency, meta upgrades and best scores written when run 1 ends change run 2. Snapshot the save before the first run (`JsonUtility.ToJson`), restore it at the start of every run (`JsonUtility.FromJsonOverwrite`), and never write the save to disk in headless mode.

## Mismatch with normal play

**Different step sizes.** If normal play slices frames into 1/30 s steps and headless mode steps 1/60 s, collision and timing differ. Share one constant.

**Logic left in `Update`.** In headless mode one rendered frame can cover tens of seconds of game time. Anything in `Update` outside the step (camera follow, spawn timers, buff expiry checked per frame) runs once for all of it. The camera is the usual one: if abilities pick "random enemy on screen", the camera must follow the player inside the step, at the same speed as normal play.

**Screen size under `-nographics`.** The player may ignore `-screen-width` and `-screen-height` and report a fixed resolution. If gameplay reads the view size (on-screen targeting, spawn rings at the screen edge), set the aspect in code for headless runs to match the resolution you balance at.

**Bot reaction speed.** A headless bot that re-plans every step reacts faster than the same bot in a rendered build that plans once per frame at 8x speed. Use a think interval (`-think 0.25`) for both before comparing them, and when you want something closer to human reaction time.

## Reading the numbers

**Bot policy dominates.** On the source project, three bot policies (re-plan every step; 0.25 s reaction; random card picks) gave the same character win rates 30 to 60 points apart. The ranking of the strongest and weakest characters held across all three; the middle shuffled. Absolute win rates say little about players; comparisons under one fixed policy are what the tool is good for.

**Fixed seed hides luck.** Rerunning a batch with the same start seed replays the same runs. If that batch happens to be easy, every rerun is easy. Use a random start seed by default and print it; fix the seed only to reproduce a result or to compare before and after a change on the same runs.

**Small samples.** 100 runs at 50% is roughly 40% to 60% at 95% confidence. Report the Wilson interval with every rate. 1,000 runs narrow it to about plus or minus 3 points.

**Stale build.** The batch runs the built player, not the editor. Check the player's build time against the last source change before trusting a result.

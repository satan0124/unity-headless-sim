# Decision-replay model

A second, much faster layer for one kind of question: **how do the offer-and-pick rules shape a build?** Card weights, number of slots, how many choices are offered, unlock conditions for upgrades. It does not simulate combat.

On the source project it ran several thousand runs per second, against about 5 per second for the full headless sim.

## How it works

1. **Record timelines in the full sim.** Each time the game pauses for a choice, the runner appends `game time : kind : relevant state` (for example `183.4:L:2` for a level-up at 183.4 s while at tier 2). One line per run goes to `choices.txt`. This captures how fast a real run earns choices.
2. **Export the rules data.** A `-cardexport <file>` flag makes the player write the weights, caps, slot counts and content lists to JSON and quit. Run it from the same build as the batch so the data matches.
3. **Replay.** A small script reimplements only two functions from the game: "which cards can be offered now" and "which one does the bot pick". It walks each recorded timeline many times with different random draws and tallies outcomes (when a key upgrade is reached, how many items reach max level, final build).
4. **Ask what-ifs.** Flags like `--slots 6`, `--weight NewItem=3` or `--no-evolutions` change the rules in the script only. No rebuild, answers in seconds.

## Accuracy

Check the model against the full sim before trusting it: replay the recorded timelines with unchanged rules and compare a milestone the sim also logged. On the source project, over 240 runs, the model said 97.0% of runs reached the first ability upgrade (sim: 94.2%) and 83.5% reached the second (sim: 79.6%), with median times within 0 to 5 seconds.

The model runs a few points high for a structural reason: it has no feedback loop. In the real game, bad picks make the player weaker, which slows leveling or ends the run early. The model replays a timeline that was earned with the original picks.

So it answers "if the rules change, how do builds change" well, and "if the player gets stronger, do they level faster" not at all. Use the full sim for the second.

## Keeping it honest

- The offer and pick logic is a copy. When the game's rules change and the script does not, it quietly computes the wrong thing. Comment the game's functions with "update the replay script too", and keep a `--check` mode that compares against the latest sim batch. A gap above about 10 points means the copy has drifted.
- Read weights and caps from the exported JSON instead of hard-coding them, so tuning numbers needs no script change. Only rule changes (new card kinds, new conditions) need the script edited.
- When a new switch is added to the game (a flag that disables a card kind), export it too, and give it a default in the script for older exports.

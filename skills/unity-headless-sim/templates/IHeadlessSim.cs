using System.Text;

namespace HeadlessSim
{
    /// <summary>
    /// What the game exposes to <see cref="HeadlessRunner"/>. Implement it on the game manager or on a thin adapter.
    /// </summary>
    /// <remarks>
    /// The runner calls these in a fixed order every step: check <see cref="IsOver"/>, answer <see cref="NeedsDecision"/>,
    /// call <see cref="Think"/>, then <see cref="Step"/>. Nothing here may depend on frame rate or wall-clock time.
    /// </remarks>
    public interface IHeadlessSim
    {
        /// <summary>Copies persistent data (save file, unlocks, meta upgrades) so it can be restored before every run.</summary>
        /// <remarks>Called once, before the first run. Serializing to JSON with <c>JsonUtility</c> is usually enough.</remarks>
        void SnapshotPersistent();

        /// <summary>Starts a fresh run: restore persistent data, reset every per-run field, seed the RNG, begin play.</summary>
        /// <param name="runIndex">0-based index of this run inside the process.</param>
        /// <param name="seed">Seed for this run, or <c>-1</c> for unseeded.</param>
        /// <remarks>
        /// Seed every RNG the simulation uses, for example <c>UnityEngine.Random.InitState(seed)</c>.
        /// Anything not reset here carries over from the previous run; see <c>references/pitfalls.md</c>.
        /// </remarks>
        void BeginRun(int runIndex, int seed);

        /// <summary>True once the run has ended (win, death, or time limit).</summary>
        bool IsOver { get; }

        /// <summary>True while the sim is paused waiting for a player choice (level-up pick, shop, draft).</summary>
        bool NeedsDecision { get; }

        /// <summary>Lets the bot answer the pending choice immediately.</summary>
        void Decide();

        /// <summary>Lets the bot steer (move, aim, use abilities) before the next step.</summary>
        void Think();

        /// <summary>Advances the simulation by exactly <paramref name="dt"/> seconds of game time.</summary>
        /// <param name="dt">Step length in seconds. Use the same value the normal frame loop slices into.</param>
        void Step(float dt);

        /// <summary>Appends this run's result as space-separated <c>key=value</c> pairs, without the leading <c>RUN</c>.</summary>
        /// <param name="sb">Builder that already holds <c>RUN i=… seed=…</c>.</param>
        /// <remarks>Always write <c>won=0|1</c> and <c>t=&lt;seconds&gt;</c>. Values must not contain spaces.</remarks>
        void WriteResult(StringBuilder sb);
    }
}

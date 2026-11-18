using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace HeadlessSim
{
    /// <summary>
    /// Plays many seeded runs in one process with no rendering and writes one result line per run to <c>runs.txt</c>.
    /// </summary>
    /// <remarks>
    /// Activates only when the command line contains <c>-headless</c>. Flags:
    /// <c>-runs N</c> (default 1), <c>-seed S</c> (run i uses S+i; omit for unseeded), <c>-out DIR</c> (default: current folder),
    /// <c>-maxtime SEC</c> (game-time limit per run; 0 = none), <c>-think SEC</c> (bot re-plans at most this often; 0 = every step).
    /// Launch with <c>-batchmode -nographics</c>. The process quits by itself after the last run.
    /// Add it to a bootstrap object or create it from code; <see cref="Sim"/> must be assigned before the first frame.
    /// </remarks>
    public class HeadlessRunner : MonoBehaviour
    {
        /// <summary>Game-time length of one step in seconds. Must equal the step the normal frame loop uses.</summary>
        public float maxStep = 1f / 30f;

        /// <summary>Wall-clock budget per Unity frame in milliseconds; leftover work continues next frame so Unity can pump its own events.</summary>
        public int frameBudgetMs = 200;

        /// <summary>The game being driven. Assign before the first <c>Update</c>.</summary>
        public IHeadlessSim Sim;

        /// <summary>Number of runs this process plays.</summary>
        int _runs = 1;

        /// <summary>Seed of run 0, or <c>-1</c> for unseeded.</summary>
        int _seed = -1;

        /// <summary>Folder that receives <c>runs.txt</c>.</summary>
        string _out = ".";

        /// <summary>Game-time limit per run in seconds; 0 means no limit.</summary>
        float _maxTime;

        /// <summary>Minimum game time between two bot <see cref="IHeadlessSim.Think"/> calls in seconds; 0 means every step.</summary>
        float _think;

        /// <summary>Index of the run in progress.</summary>
        int _runIdx;

        /// <summary>Game time elapsed in the current run, counted by the runner in seconds.</summary>
        float _t;

        /// <summary>Game time at which the bot may think again.</summary>
        float _nextThink;

        /// <summary>Steps taken in the current run.</summary>
        long _steps;

        /// <summary>True when the current run ended because <see cref="_maxTime"/> was reached.</summary>
        bool _timeUp;

        /// <summary>Wall-clock time of the current run.</summary>
        readonly Stopwatch _runWall = new Stopwatch();

        /// <summary>Wall-clock time of the current frame, checked against <see cref="frameBudgetMs"/>.</summary>
        readonly Stopwatch _frameWall = new Stopwatch();

        /// <summary>True when <c>-headless</c> is on the command line.</summary>
        public static bool Requested => Array.IndexOf(Environment.GetCommandLineArgs(), "-headless") >= 0;

        /// <summary>Reads the flags, takes the persistent-data snapshot, and starts run 0.</summary>
        void Start()
        {
            if (!Requested || Sim == null) { enabled = false; return; }
            _runs = Math.Max(1, ArgInt("-runs", 1));
            _seed = ArgInt("-seed", -1);
            _out = Arg("-out") ?? ".";
            _maxTime = ArgFloat("-maxtime", 0f);
            _think = ArgFloat("-think", 0f);
            Directory.CreateDirectory(_out);
            // Rendering is off, so nothing gains from frame pacing; let Update run as often as possible.
            Application.targetFrameRate = -1;
            QualitySettings.vSyncCount = 0;
            Sim.SnapshotPersistent();
            BeginRun();
        }

        /// <summary>Resets the runner's own per-run fields and asks the game to start a run.</summary>
        /// <remarks>Every field that changes during a run must be reset here; a leftover think-timer once froze the bot for a whole run.</remarks>
        void BeginRun()
        {
            _t = 0f;
            _nextThink = 0f;
            _steps = 0;
            _timeUp = false;
            Sim.BeginRun(_runIdx, _seed >= 0 ? _seed + _runIdx : -1);
            _runWall.Restart();
        }

        /// <summary>Steps the simulation until the frame budget runs out, finishing and starting runs as needed.</summary>
        void Update()
        {
            _frameWall.Restart();
            while (_frameWall.ElapsedMilliseconds < frameBudgetMs)
            {
                if (_maxTime > 0f && _t >= _maxTime && !Sim.IsOver) _timeUp = true;
                if (Sim.IsOver || _timeUp)
                {
                    WriteRun();
                    if (++_runIdx < _runs) { BeginRun(); continue; }
                    enabled = false;
                    Application.Quit(0);
                    return;
                }
                if (Sim.NeedsDecision) { Sim.Decide(); continue; }
                if (_t >= _nextThink)
                {
                    Sim.Think();
                    _nextThink = _think > 0f ? _nextThink + _think : _t;
                }
                Sim.Step(maxStep);
                _t += maxStep;
                _steps++;
            }
        }

        /// <summary>Appends the finished run to <c>runs.txt</c> as one <c>RUN key=value …</c> line.</summary>
        /// <remarks>Appends immediately so runs already finished survive if the process is killed.</remarks>
        void WriteRun()
        {
            var sb = new StringBuilder("RUN");
            sb.Append(" i=").Append(_runIdx).Append(" seed=").Append(_seed >= 0 ? _seed + _runIdx : -1);
            if (_timeUp) sb.Append(" timeup=1");
            Sim.WriteResult(sb);
            sb.Append(" steps=").Append(_steps);
            sb.Append(" wall=").Append(_runWall.Elapsed.TotalSeconds.ToString("0.00", CultureInfo.InvariantCulture));
            File.AppendAllText(Path.Combine(_out, "runs.txt"), sb.Append('\n').ToString(), new UTF8Encoding(false));
        }

        /// <summary>Returns the value after <paramref name="name"/> on the command line.</summary>
        /// <param name="name">Flag including the dash, e.g. <c>-runs</c>.</param>
        /// <returns>The next argument, or <c>null</c> when the flag is missing or last.</returns>
        static string Arg(string name)
        {
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, name);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        /// <summary>Reads an integer flag.</summary>
        /// <param name="name">Flag including the dash.</param>
        /// <param name="def">Value used when the flag is missing or not a number.</param>
        /// <returns>The parsed value or <paramref name="def"/>.</returns>
        static int ArgInt(string name, int def) =>
            int.TryParse(Arg(name), NumberStyles.Integer, CultureInfo.InvariantCulture, out int v) ? v : def;

        /// <summary>Reads a float flag with invariant culture.</summary>
        /// <param name="name">Flag including the dash.</param>
        /// <param name="def">Value used when the flag is missing or not a number.</param>
        /// <returns>The parsed value or <paramref name="def"/>.</returns>
        static float ArgFloat(string name, float def) =>
            float.TryParse(Arg(name), NumberStyles.Float, CultureInfo.InvariantCulture, out float v) ? v : def;
    }
}

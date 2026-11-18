// Example only: shows how to split a typical game manager so HeadlessRunner can step it.
// Adapt names to the project; do not add this file as-is.
using UnityEngine;

namespace HeadlessSim.Example
{
    /// <summary>Sketch of a game manager whose simulation can be stepped by the frame loop or from outside.</summary>
    public class Game : MonoBehaviour
    {
        /// <summary>Longest step in seconds. Shared by normal play and headless mode so both produce the same results.</summary>
        /// <remarks>Small enough that fast objects do not pass through targets in one step.</remarks>
        public const float MaxStep = 1f / 30f;

        /// <summary>When true, <see cref="Update"/> stops advancing the simulation; the caller uses <see cref="SimStep"/>.</summary>
        public bool externalStep;

        /// <summary>True while gameplay is running (not paused, not in a menu, not over).</summary>
        public bool playing;

        /// <summary>Camera position in world units. Gameplay reads it when abilities target "enemies on screen".</summary>
        public Vector2 camPos;

        /// <summary>Player position in world units.</summary>
        public Vector2 playerPos;

        // BEFORE: gameplay advanced inside Update with Time.deltaTime, mixed with camera and UI.
        //
        // void Update()
        // {
        //     player.Tick(Time.deltaTime);
        //     spawner.Tick(Time.deltaTime);
        //     camPos = Vector2.Lerp(camPos, playerPos, 0.2f);
        //     camPos += Random.insideUnitCircle * shake;   // per-frame random draw: breaks determinism
        //     ui.Tick();
        // }

        /// <summary>Per frame: advances the simulation unless it is driven externally, then updates presentation.</summary>
        void Update()
        {
            if (playing && !externalStep)
            {
                // Slice the frame into steps of at most MaxStep; the cap of 10 avoids a spiral after a long hitch.
                float rem = Time.deltaTime;
                int n = 0;
                while (rem > 0.0001f && n < 10 && playing) { float d = Mathf.Min(rem, MaxStep); Sim(d); rem -= d; n++; }
                camPos = Vector2.Lerp(camPos, playerPos, 1f - Mathf.Exp(-12f * Time.deltaTime));
            }
            // Presentation only from here on. No gameplay reads, no draws from the gameplay RNG.
            // If shake must be random, skip it when externalStep is on, or give it its own System.Random.
        }

        /// <summary>Advances every gameplay system by <paramref name="dt"/> in a fixed order.</summary>
        /// <param name="dt">Step length in seconds of game time.</param>
        void Sim(float dt)
        {
            // player.Tick(dt); spawner.Tick(dt); enemies.Tick(dt); projectiles.Tick(dt); pickups.Tick(dt);
            // Open level-up menus here (set playing = false), never from Update.
        }

        /// <summary>External entry point: one step of simulation plus anything else gameplay depends on.</summary>
        /// <param name="dt">Step length in seconds; pass <see cref="MaxStep"/>.</param>
        /// <remarks>
        /// The camera follows here because targeting reads it. Thousands of steps run per rendered frame in headless mode,
        /// so a camera updated only in <see cref="Update"/> would lag tens of seconds behind.
        /// </remarks>
        public void SimStep(float dt)
        {
            if (!playing) return;
            Sim(dt);
            camPos = Vector2.Lerp(camPos, playerPos, 1f - Mathf.Exp(-12f * dt));
        }
    }
}

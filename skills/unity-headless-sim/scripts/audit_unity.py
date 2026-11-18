#!/usr/bin/env python3
"""Scan Unity C# scripts for things that break headless stepping or determinism.

Usage:
  python audit_unity.py <path/to/Assets> [--all]

Prints each finding with file:line, grouped by category, then a count per category.
By default skips folders named Editor, Plugins, ThirdParty, Packages, TextMesh Pro and Samples; --all scans everything.
It is a text search, not a compiler: treat hits as places to look, not verdicts.
Standard library only.
"""
import os
import re
import sys

CHECKS = [
    ("physics", "Physics advances with Unity's clock, not your step. Needs SimulationMode.Script + Physics.Simulate(dt), or removal from gameplay.",
     r"\b(Rigidbody2?D?|Physics2?D\.|OnCollision(Enter|Stay|Exit)2?D?|OnTrigger(Enter|Stay|Exit)2?D?|FixedUpdate)\b"),
    ("unity-time", "Gameplay must use the dt passed to the step and the sim's own clock.",
     r"\bTime\.(time|deltaTime|fixedDeltaTime|timeSinceLevelLoad|frameCount|unscaledDeltaTime|unscaledTime|realtimeSinceStartup)\b"),
    ("timescale", "Speed-up through timeScale is not needed headless; check nothing depends on it.",
     r"\bTime\.timeScale\b"),
    ("coroutines", "Coroutines and Invoke follow Unity time. Fine for visuals; gameplay timing must move into your own timers.",
     r"\b(StartCoroutine|WaitForSeconds|WaitForSecondsRealtime|WaitForFixedUpdate|Invoke(Repeating)?\s*\()"),
    ("animation", "Animator/Timeline/tweens follow Unity time. Fine for visuals; not for hitboxes, cooldowns or spawn timing.",
     r"\b(Animator|Animation|PlayableDirector|DOTween|DOMove|LeanTween|iTween)\b"),
    ("rng", "Every RNG the sim uses must be seeded per run. Draws outside the sim step (shake, particles, UI) break determinism.",
     r"\b(UnityEngine\.)?Random\.(Range|value|insideUnitCircle|insideUnitSphere|onUnitSphere|rotation|ColorHSV|InitState)\b|new\s+System\.Random\b|new\s+Random\s*\(|Guid\.NewGuid"),
    ("wall-clock", "Wall-clock time differs between runs.",
     r"\b(DateTime\.(Now|UtcNow)|Stopwatch|Environment\.TickCount)\b"),
    ("update-methods", "Each MonoBehaviour Update is a place gameplay might run outside the sim step. Gameplay should be ticked from one entry point.",
     r"\bvoid\s+(Update|LateUpdate)\s*\("),
    ("screen", "With -nographics the screen size may be fixed; gameplay that reads it (on-screen targeting) must set it explicitly.",
     r"\b(Screen\.(width|height)|Camera\.main\.(WorldToViewportPoint|ViewportToWorldPoint|orthographicSize|aspect)|GeometryUtility\.TestPlanesAABB|OnBecame(In)?[Vv]isible)\b"),
    ("async", "Async/threads can reorder work between runs.",
     r"\b(async\s+(void|Task)|Task\.Run|new\s+Thread|Parallel\.For|ThreadPool)\b"),
]

SKIP_DIRS = {"Editor", "Plugins", "ThirdParty", "Packages", "TextMesh Pro", "Samples"}


def main():
    # Windows consoles default to a legacy code page; never crash on a non-ASCII file name or comment.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scan_all = "--all" in sys.argv
    if not args:
        print(__doc__)
        return 2
    root = args[0]
    compiled = [(name, why, re.compile(rx)) for name, why, rx in CHECKS]
    hits = {name: [] for name, _, _ in CHECKS}
    files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if not scan_all:
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".cs"):
                continue
            files += 1
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                code = line.split("//", 1)[0]
                if not code.strip():
                    continue
                for name, _, rx in compiled:
                    if rx.search(code):
                        hits[name].append((os.path.relpath(path, root), i, line.strip()[:120]))

    print(f"Scanned {files} C# files under {root}\n")
    for name, why, _ in CHECKS:
        h = hits[name]
        if not h:
            continue
        print(f"== {name} ({len(h)}) ==")
        print(f"   {why}")
        for path, ln, text in h[:40]:
            print(f"   {path}:{ln}  {text}")
        if len(h) > 40:
            print(f"   ... {len(h) - 40} more")
        print()
    print("Summary:")
    for name, _, _ in CHECKS:
        print(f"  {name:15s} {len(hits[name])}")
    blockers = len(hits["physics"]) + len(hits["async"])
    if blockers:
        print("\nPhysics or async code found: confirm it is not gameplay before going further.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

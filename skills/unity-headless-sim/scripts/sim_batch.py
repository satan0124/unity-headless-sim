#!/usr/bin/env python3
"""Batch launcher and aggregator for a Unity player built with HeadlessRunner.

Subcommands:
  run          launch the player in parallel over a grid of game flags, then summarize
  summarize    aggregate an existing output folder
  determinism  check that a seed always gives the same run, and that multi-run processes match fresh ones

Everything after a lone `--` is passed to the player unchanged.

Examples:
  python sim_batch.py run --exe Build/Game.exe --grid map=0,1 diff=0,1,2 --runs 100 --per-proc 20 --out sim_out -- -meta max
  python sim_batch.py summarize sim_out --by map,diff --fields lv,kills
  python sim_batch.py determinism --exe Build/Game.exe --seed 42 -- -map 0

Standard library only. Python 3.8+.
"""
import argparse
import csv
import itertools
import math
import os
import random
import shlex
import statistics
import subprocess
import sys
import time

# Fields that change between identical runs (timing) and are ignored by the determinism check.
TIMING_FIELDS = {"wall", "i"}


def parse_line(line):
    """Parse `RUN k=v k=v ...` into a dict; returns None for other lines."""
    parts = line.split()
    if not parts or parts[0] != "RUN":
        return None
    out = {}
    for tok in parts[1:]:
        k, sep, v = tok.partition("=")
        if sep and k:
            out[k] = v
    return out


def wilson(wins, n, z=1.96):
    """95% Wilson score interval for a proportion; returns (low, high) in 0..1."""
    if n <= 0:
        return 0.0, 0.0
    p = wins / n
    z2 = z * z
    den = 1 + z2 / n
    center = (p + z2 / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n) / den
    return max(0.0, center - half), min(1.0, center + half)


def to_num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def read_runs(root):
    """Collect every RUN line under root, tagging each with the cell flags from its process folder's cell.txt."""
    rows = []
    for dirpath, _, files in os.walk(root):
        if "runs.txt" not in files:
            continue
        cell = {}
        cell_file = os.path.join(dirpath, "cell.txt")
        if os.path.exists(cell_file):
            with open(cell_file, encoding="utf-8") as f:
                for line in f:
                    k, sep, v = line.strip().partition("=")
                    if sep:
                        cell[k] = v
        with open(os.path.join(dirpath, "runs.txt"), encoding="utf-8") as f:
            for line in f:
                r = parse_line(line)
                if r is not None:
                    merged = dict(cell)
                    merged.update(r)
                    rows.append(merged)
    return rows


def summarize(root, by, fields, expected=None, elapsed=None, seed=None):
    rows = read_runs(root)
    if not rows:
        print(f"No RUN lines under {root}.")
        return False
    groups = {}
    for r in rows:
        key = tuple(r.get(k, "-") for k in by)
        groups.setdefault(key, []).append(r)

    header = list(by) + ["runs", "win%", "95% CI", "med t"] + [f"med {f}" for f in fields]
    table = []
    tot_n = tot_w = 0
    for key in sorted(groups, key=lambda k: tuple((to_num(x) if to_num(x) is not None else math.inf, x) for x in k)):
        g = groups[key]
        n = len(g)
        w = sum(1 for r in g if r.get("won") == "1")
        tot_n += n
        tot_w += w
        lo, hi = wilson(w, n)
        row = list(key) + [str(n), f"{100 * w / n:.1f}", f"{100 * lo:.1f}-{100 * hi:.1f}", med(g, "t")]
        row += [med(g, f) for f in fields]
        table.append(row)

    widths = [max(len(header[i]), *(len(r[i]) for r in table)) for i in range(len(header))]
    print("  ".join(h.rjust(widths[i]) for i, h in enumerate(header)))
    for r in table:
        print("  ".join(c.rjust(widths[i]) for i, c in enumerate(r)))
    lo, hi = wilson(tot_w, tot_n)
    print(f"\nTotal: {tot_n} runs, win {100 * tot_w / tot_n:.1f}% (95% CI {100 * lo:.1f}-{100 * hi:.1f})")
    if seed is not None:
        print(f"Start seed: {seed}  (pass --seed {seed} to reproduce)")
    if elapsed:
        print(f"Elapsed: {elapsed:.0f} s, {tot_n / elapsed:.2f} runs/s")

    with open(os.path.join(root, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(table)
    print(f"Wrote {os.path.join(root, 'summary.csv')}")

    if expected is not None and tot_n < expected:
        print(f"WARNING: expected {expected} runs, got {tot_n}. Check player.log in the process folders.")
        return False
    return True


def med(rows, field):
    vals = [to_num(r.get(field)) for r in rows]
    vals = [v for v in vals if v is not None and v >= 0]
    if not vals:
        return "-"
    m = statistics.median(vals)
    return f"{m:.0f}" if m == int(m) else f"{m:.2f}"


def default_jobs():
    # Leave 4 threads for the rest of the machine; more than 10 players at once made the source machine sluggish.
    return max(1, min(10, (os.cpu_count() or 4) - 4))


def parse_grid(items):
    """['map=0,1', 'diff=0,1,2'] -> [{'map':'0','diff':'0'}, ...]"""
    axes = []
    for it in items or []:
        k, sep, v = it.partition("=")
        if not sep or not k:
            sys.exit(f"Bad --grid item: {it!r} (expected name=v1,v2)")
        axes.append((k, [x for x in v.split(",") if x != ""]))
    if not axes:
        return [{}]
    names = [a[0] for a in axes]
    return [dict(zip(names, combo)) for combo in itertools.product(*(a[1] for a in axes))]


def launch(cmd_prefix, args, log_dir):
    """Start one player process; returns the Popen."""
    full = cmd_prefix + ["-batchmode", "-nographics", "-headless"] + args + [
        "-out", log_dir, "-logFile", os.path.join(log_dir, "player.log")]
    return subprocess.Popen(full, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_pool(tasks, jobs, timeout_per_run, show=True):
    """tasks: list of (cmd_prefix, args, dir, runs). Runs at most `jobs` at once, kills overdue ones."""
    waiting = list(tasks)
    running = []
    done = 0
    total = len(tasks)
    try:
        while waiting or running:
            now = time.time()
            for item in running[:]:
                p, start, limit = item
                if p.poll() is not None:
                    running.remove(item)
                    done += 1
                elif now - start > limit:
                    p.kill()
                    running.remove(item)
                    done += 1
                    print(f"\nKilled a process after {limit:.0f} s (timeout).")
            while waiting and len(running) < jobs:
                prefix, args, d, runs = waiting.pop(0)
                running.append((launch(prefix, args, d), time.time(), 60 + runs * timeout_per_run))
            if show:
                print(f"\r  processes done {done}/{total}  running {len(running)}   ", end="", flush=True)
            time.sleep(0.3)
    finally:
        for p, _, _ in running:
            p.kill()
    if show:
        print()


def cmd_run(a, passthru):
    prefix = shlex.split(a.exe, posix=(os.name != "nt")) if " " in a.exe and not os.path.exists(a.exe) else [a.exe]
    seed = a.seed if a.seed is not None else random.randint(1, 1_000_000_000)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = os.path.join(a.out, stamp)
    os.makedirs(root, exist_ok=True)
    cells = parse_grid(a.grid)
    tasks = []
    next_seed = seed
    for ci, cell in enumerate(cells):
        left = a.runs
        p = 0
        while left > 0:
            k = min(a.per_proc, left)
            d = os.path.join(root, f"c{ci:03d}_p{p:02d}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "cell.txt"), "w", encoding="utf-8") as f:
                for name, val in cell.items():
                    f.write(f"{name}={val}\n")
            args = []
            for name, val in cell.items():
                args += [f"-{name}", val]
            args += ["-runs", str(k), "-seed", str(next_seed)] + passthru
            tasks.append((prefix, args, d, k))
            next_seed += k
            left -= k
            p += 1
    jobs = a.jobs or default_jobs()
    print(f"{len(cells)} cells x {a.runs} runs, {len(tasks)} processes, {jobs} at once, start seed {seed}")
    t0 = time.time()
    run_pool(tasks, jobs, a.timeout)
    ok = summarize(root, list(cells[0].keys()), a.fields, expected=len(cells) * a.runs,
                   elapsed=time.time() - t0, seed=seed)
    return 0 if ok else 1


def strip(r):
    return {k: v for k, v in r.items() if k not in TIMING_FIELDS}


def cmd_determinism(a, passthru):
    prefix = shlex.split(a.exe, posix=(os.name != "nt")) if " " in a.exe and not os.path.exists(a.exe) else [a.exe]
    root = os.path.join(a.out, "determinism-" + time.strftime("%Y%m%d-%H%M%S"))
    tasks = []
    for i in range(3):
        d = os.path.join(root, f"single{i}")
        os.makedirs(d, exist_ok=True)
        tasks.append((prefix, ["-runs", "1", "-seed", str(a.seed)] + passthru, d, 1))
    d = os.path.join(root, "multi")
    os.makedirs(d, exist_ok=True)
    tasks.append((prefix, ["-runs", "3", "-seed", str(a.seed - 2)] + passthru, d, 3))
    run_pool(tasks, a.jobs or default_jobs(), a.timeout)

    def lines(sub):
        path = os.path.join(root, sub, "runs.txt")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [r for r in (parse_line(x) for x in f) if r]

    singles = [lines(f"single{i}") for i in range(3)]
    multi = lines("multi")
    ok = True
    if any(len(s) != 1 for s in singles) or len(multi) != 3:
        print("FAIL: missing runs; check player.log under", root)
        return 1
    base = strip(singles[0][0])
    for i in (1, 2):
        if strip(singles[i][0]) != base:
            ok = False
            print(f"FAIL: same seed, different result (run 0 vs run {i}):")
            print("  ", diff(base, strip(singles[i][0])))
    if strip(multi[2]) != base:
        ok = False
        print("FAIL: third run of a 3-run process differs from a fresh process at the same seed:")
        print("  ", diff(base, strip(multi[2])))
    print("PASS: deterministic" if ok else f"See {root}")
    return 0 if ok else 1


def diff(x, y):
    keys = sorted(set(x) | set(y))
    return ", ".join(f"{k}: {x.get(k)} vs {y.get(k)}" for k in keys if x.get(k) != y.get(k))


def main():
    # Windows consoles default to a legacy code page; never crash on a non-ASCII file name or comment.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    argv = sys.argv[1:]
    passthru = []
    if "--" in argv:
        i = argv.index("--")
        argv, passthru = argv[:i], argv[i + 1:]

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="launch a batch and summarize")
    r.add_argument("--exe", required=True, help="player executable (or a quoted command line)")
    r.add_argument("--grid", nargs="*", default=[], help="name=v1,v2 ... ; each becomes -name v on the player command line")
    r.add_argument("--runs", type=int, default=100, help="runs per grid cell (default 100)")
    r.add_argument("--per-proc", type=int, default=20, help="runs per process (default 20)")
    r.add_argument("--jobs", type=int, default=0, help="processes at once (default: CPU threads - 4, max 10)")
    r.add_argument("--seed", type=int, help="start seed (default: random, printed)")
    r.add_argument("--timeout", type=float, default=60, help="seconds allowed per run before a process is killed")
    r.add_argument("--fields", type=lambda s: [x for x in s.split(",") if x], default=[], help="extra numeric fields to report medians for")
    r.add_argument("--out", default="sim_out")

    s = sub.add_parser("summarize", help="aggregate an existing folder")
    s.add_argument("root")
    s.add_argument("--by", type=lambda x: [k for k in x.split(",") if k], default=[], help="group-by fields, e.g. map,diff")
    s.add_argument("--fields", type=lambda x: [k for k in x.split(",") if k], default=[])

    d = sub.add_parser("determinism", help="same seed three times, plus a 3-run process")
    d.add_argument("--exe", required=True)
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--jobs", type=int, default=0)
    d.add_argument("--timeout", type=float, default=60)
    d.add_argument("--out", default="sim_out")

    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a, passthru)
    if a.cmd == "summarize":
        return 0 if summarize(a.root, a.by, a.fields) else 1
    return cmd_determinism(a, passthru)


if __name__ == "__main__":
    sys.exit(main())

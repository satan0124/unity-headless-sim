# unity-headless-sim

**让 Unity 游戏不渲染画面连跑几千局，拿到靠得住的通关率。**

[English](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ 简体中文

这是一个 Claude Code skill，引导 Claude 为你的 Unity 项目加上无画面模拟模式：由 bot 操作，每局有自己固定的随机种子，多个进程并行，结果汇总成通关率和 95% 置信区间。模拟跑的是游戏本身的 C# 代码，不是另写一套规则。

> 需要 Claude Code、一个 Unity 项目和 Python 3.8 以上。Claude 会修改项目代码，请像审 pull request 一样看过再合入。只在 Windows＋Unity 6 上测过。

[快速开始](#快速开始) · [示例](#示例) · [原项目的实测](#原项目的实测) · [限制](#限制)

## 为什么用

- **几千局，而不是几局。** 在原来的项目里，一局 15 分钟无画面跑完约 2～3 秒。
- **不用另写一套规则。** 用 Python 再写一遍规则，会在没人察觉的情况下和游戏越差越远。这里跑的就是游戏本身，改平衡不用改两遍。
- **可以复现。** 同一个种子一定跑出同一局，结果有异常可以单独拿出来看。
- **数字带误差范围。** 每个通关率都附 Wilson 95% 置信区间，分得清是真的变了还是运气。
- **不适合会直接说。** Claude 会先检查项目；物理、协程或 Animator 在驱动游戏逻辑的，改代码之前就先告诉你。

## 快速开始

在 Claude Code 里输入：

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

或者把 `skills/unity-headless-sim/` 复制到 `~/.claude/skills/`（所有项目）或 `<项目>/.claude/skills/`（单个项目）。

然后用 Claude Code 打开你的 Unity 项目，对它说：“加一个无画面模拟模式，我要测每个难度的通关率。”

## 示例

1. **检查**：Claude 用 `audit_unity.py` 扫描 `Assets/`，列出会卡住固定步长的地方，比如游戏逻辑读 `Time.deltaTime`、没设种子的 `Random`、逻辑分散在好几个 `Update` 里。
2. **改代码**：拆开游戏循环，让模拟可以从外部推进；加上 `HeadlessRunner.cs`，再写一层小小的适配，让 bot 能操作、能选升级选项。
3. **确认可复现**：`sim_batch.py determinism` 用同一个种子跑三次，再开一个连跑 3 局的进程，结果必须全部相同。
4. **批量跑**：`sim_batch.py run --grid map=0,1,2 diff=0,1,2 --runs 100` 并行启动游戏，按地图和难度打印通关率、置信区间和存活时间中位数，并写出 `summary.csv`。

## 内容

```
skills/unity-headless-sim/
  SKILL.md                    Claude 照着执行的流程
  templates/
    IHeadlessSim.cs           游戏要实现的接口
    HeadlessRunner.cs         运行器：-headless -runs -seed -out -maxtime -think
    GameLoopPatch.cs          拆游戏循环的改前／改后示例
  scripts/
    audit_unity.py            扫描 Assets/ 找会卡住的地方
    sim_batch.py              run（批量）／summarize（汇总）／determinism（可复现检查）
  references/
    pitfalls.md               实际踩过、不会报错的坑
    decision-model.md         选卡规则用的回放模型（可选）
```

脚本只用 Python 标准库，不通过 Claude 也能用：

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## 原项目的实测

这个 skill 是从一款 Unity 6 的 2D 割草游戏里抽出来的，游戏逻辑全是纯 C#。2026 年 11 月在 i7-14700（28 线程）上测的：

- 一局 15 分钟：无画面约 2～3 秒，另加约 5 秒的程序启动和退出。
- 1,008 局、同时 10 个进程：5 分 38 秒。

下表说明 bot 的影响有多大：八个角色、三种 bot 打法，每格 360 局，同一组种子（2026-11-16）。角色名称已匿名。

| 角色 | 每一步都重新判断 | 每 0.25 秒反应一次 | 升级卡随机选 |
|---|---|---|---|
| A | 99.2% | 96.7% | 81.1% |
| B | 96.9% | 58.9% | 68.3% |
| C | 95.3% | 81.4% | 55.0% |
| D | 86.7% | 68.9% | 28.9% |
| E | 83.1% | 54.2% | 46.9% |
| F | 77.2% | 65.0% | 34.4% |
| G | 52.2% | 12.2% | 48.1% |
| H | 32.8% | 6.4% | 26.9% |

- 八个角色里有六个，光是换 bot 打法，通关率就差 36～58 个百分点。
- 两端很稳：三种打法下 A 都最强、H 都最弱，中间的顺序会变。
- bot 反应变慢时掉得最多的是 B 和 G；升级卡随机选时掉得最多的是 D 和 F。不同打法会暴露不同的弱点。

## 限制

- 最适合游戏逻辑是纯 C#、从同一个地方推进的游戏。用 Unity 物理、Animator、Timeline、协程或补间动画驱动游戏逻辑的，要先搬到自己的步进里。
- bot 不等于玩家。这些数字适合在同一种 bot 打法下做比较（改动前后、A 对 B）；通关率本身的高低要拿真人试玩校准。
- 批量脚本本身跨平台，但 macOS、Linux 的可执行文件还没试过。
- 模拟步以外的代码只要从游戏用的随机数里抽过一次，同一个种子就跑不出同一局。原项目踩过的情况列在 `references/pitfalls.md`。

## 文档

- [SKILL.md](skills/unity-headless-sim/SKILL.md)：完整流程，一步一步（英文）
- [pitfalls.md](skills/unity-headless-sim/references/pitfalls.md)：不会报错的坑，以及每个坑当时是怎么发现的（英文）
- [decision-model.md](skills/unity-headless-sim/references/decision-model.md)：把选卡时间轴一秒回放几千次的模型，以及它的准确度限制（英文）

## 许可证

[MIT](LICENSE)

# unity-headless-sim

**为 Unity 游戏加上无画面批量模拟的 Claude Code skill。**

[English](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ 简体中文

人工试玩一次只能玩几局。这个 skill 让 Claude 把你的游戏改成可以不渲染画面、由 bot 操作、每局固定随机种子连跑几千局，最后报告通关率和 95% 置信区间。跑的是游戏本身的代码，不是另写一套规则。

它是从一款用 Unity 6、全代码驱动的 2D 割草游戏里抽出来的。在那个项目里，一局 15 分钟无画面跑完约 2～3 秒，同时开 10 个进程跑约 1,000 局不到 6 分钟。

## Claude 会做什么

1. **检查项目**：找出会让固定步长、可复现的模拟失效的东西，比如物理、协程和 Animator 驱动游戏逻辑、游戏逻辑里读 `Time.deltaTime`、没设种子的随机数、逻辑分散在很多个 `Update` 里。
2. **拆开游戏循环**：让模拟可以从外部用固定的 `dt` 推进，和正常游玩共用同一个步长。
3. **加上运行器**（`HeadlessRunner.cs`）：一个进程连跑多局，菜单由 bot 当场选，每局之间还原存档，每局写一行 `RUN key=value ...`。
4. **确认可复现**：同一个种子一定跑出同一局；连跑时的第 N 局，和用那个种子单独开一个进程跑的结果相同。
5. **批量跑**：多个进程并行、种子范围互不重叠，汇总成表格和 `summary.csv`。
6. **（可选）选卡回放模型**：回答“选卡规则改了会怎样”，一秒几千局。

## 安装

作为插件安装，在 Claude Code 里输入：

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

或者把 `skills/unity-headless-sim/` 复制到 `~/.claude/skills/`（所有项目可用）或 `<项目>/.claude/skills/`（只给单个项目）。

装好后在 Unity 项目里对 Claude 说“加一个无画面模拟模式，我要测通关率”之类的话就会用到。

## 内容

```
skills/unity-headless-sim/
  SKILL.md                    Claude 照着执行的流程
  templates/
    IHeadlessSim.cs           游戏要实现的接口
    HeadlessRunner.cs         命令行运行器（-headless -runs -seed -out -maxtime -think）
    GameLoopPatch.cs          拆游戏循环的改前／改后示例
  scripts/
    audit_unity.py            扫描 Assets/ 找会卡住的地方
    sim_batch.py              run（批量）／summarize（汇总）／determinism（可复现检查）
  references/
    pitfalls.md               实际踩过、不会报错的坑
    decision-model.md         选卡回放模型及其准确度限制
```

脚本只需要 Python 3.8 以上，不用装其他包，不通过 Claude 也能直接用：

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## 限制

- 最适合游戏逻辑是纯 C#、从同一个地方推进的游戏。用 Unity 物理、Animator、Timeline、协程或补间动画驱动游戏逻辑的，要先把它们搬到自己的步进里；检查后如果不适合，Claude 会直接说明，不会硬跑出看起来对、其实不对的数字。
- bot 不等于玩家。在原来的项目里，三种 bot 打法让同一个角色的通关率差了 30～60 个百分点。这些数字适合在同一种 bot 下做比较（改动前后、角色 A 对 B）；绝对的通关率要拿真人试玩校准。
- 只在 Windows＋Unity 6 上测过。批量脚本本身跨平台，但 macOS、Linux 的可执行文件还没试过。

## 许可证

MIT

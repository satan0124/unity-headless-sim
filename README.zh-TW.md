# 虛數空間（Imaginary Space）

**讓 Unity 遊戲不開畫面連跑幾千局，拿到信得過的通關率。**

[English](README.md) ｜ 繁體中文 ｜ [简体中文](README.zh-CN.md)

虛數空間是一個 Claude Code skill，安裝名稱是 `unity-headless-sim`。它帶著 Claude 替你的 Unity 專案加上無畫面模擬模式：由 bot 操作，每局有自己固定的亂數種子，多個行程平行跑，結果整理成通關率和 95% 信賴區間。模擬跑的是遊戲本身的 C# 程式，不是另寫一份規則。

> 需要 Claude Code、一個 Unity 專案和 Python 3.8 以上。Claude 會改專案的程式，請像審 pull request 一樣看過再收。只在 Windows＋Unity 6 上測過。

[快速開始](#快速開始) · [範例](#範例) · [原專案的實測](#原專案的實測) · [限制](#限制)

## 為什麼用

- **幾千局，不是幾局。** 在原本的專案裡，一局 15 分鐘無畫面跑完約 2～3 秒。
- **不用另寫一份規則。** 用 Python 再寫一次規則，會在沒人發現的情況下和遊戲越差越遠。這裡跑的就是遊戲本身，改平衡不用改兩次。
- **可以重現。** 同一個種子一定跑出同一局，結果怪怪的可以單獨拿出來看。
- **數字帶誤差範圍。** 每個通關率都附 Wilson 95% 信賴區間，分得出是真的變了還是運氣。
- **不適合會直接說。** Claude 會先檢查專案；物理、協程或 Animator 在驅動遊戲邏輯的，改程式之前就先告訴你。

## 快速開始

在 Claude Code 裡輸入：

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

或把 `skills/unity-headless-sim/` 複製到 `~/.claude/skills/`（所有專案）或 `<專案>/.claude/skills/`（單一專案）。

接著用 Claude Code 開你的 Unity 專案，跟它說：「加一個無畫面模擬模式，我要量每個難度的通關率。」

## 範例

1. **檢查**：Claude 用 `audit_unity.py` 掃 `Assets/`，列出會卡住固定步長的地方，例如遊戲邏輯讀 `Time.deltaTime`、沒設種子的 `Random`、邏輯分散在好幾個 `Update`。
2. **改程式**：拆開遊戲迴圈，讓模擬可以從外部推進；加上 `HeadlessRunner.cs`，再寫一層小小的轉接，讓 bot 能操作、能選升級選項。
3. **確認可重現**：`sim_batch.py determinism` 用同一個種子跑三次，再開一個連跑 3 局的行程，結果必須全部相同。
4. **批次跑**：`sim_batch.py run --grid map=0,1,2 diff=0,1,2 --runs 100` 平行啟動遊戲，依地圖與難度印出通關率、信賴區間和存活時間中位數，並寫出 `summary.csv`。

## 內容

```
skills/unity-headless-sim/
  SKILL.md                    Claude 照著做的流程
  templates/
    IHeadlessSim.cs           遊戲要實作的介面
    HeadlessRunner.cs         執行器：-headless -runs -seed -out -maxtime -think
    GameLoopPatch.cs          拆遊戲迴圈的改前／改後範例
  scripts/
    audit_unity.py            掃 Assets/ 找會卡住的地方
    sim_batch.py              run（批次）／summarize（彙整）／determinism（可重現檢查）
  references/
    pitfalls.md               實際踩過、不會報錯的坑
    decision-model.md         選卡規則用的重播模型（選用）
```

腳本只用 Python 標準函式庫，不透過 Claude 也能用：

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## 原專案的實測

這個 skill 是從一款 Unity 6 的 2D 割草遊戲抽出來的，遊戲邏輯全是純 C#。2026 年 11 月在 i7-14700（28 執行緒）上量的：

- 一局 15 分鐘：無畫面約 2～3 秒，另加約 5 秒的程式啟動與結束。
- 1,008 局、同時 10 個行程：5 分 38 秒。

下表說明 bot 的影響有多大：八名角色、三種 bot 打法，每格 360 局，同一組種子（2026-11-16）。角色名稱已匿名。

| 角色 | 每一步都重新判斷 | 每 0.25 秒反應一次 | 升級卡隨機選 |
|---|---|---|---|
| A | 99.2% | 96.7% | 81.1% |
| B | 96.9% | 58.9% | 68.3% |
| C | 95.3% | 81.4% | 55.0% |
| D | 86.7% | 68.9% | 28.9% |
| E | 83.1% | 54.2% | 46.9% |
| F | 77.2% | 65.0% | 34.4% |
| G | 52.2% | 12.2% | 48.1% |
| H | 32.8% | 6.4% | 26.9% |

- 八名裡有六名，光是換 bot 打法，通關率就差 36～58 個百分點。
- 兩端很穩：三種打法下 A 都最強、H 都最弱，中段的順序會變。
- bot 反應變慢時掉最多的是 B 和 G；升級卡隨機選時掉最多的是 D 和 F。不同打法會暴露不同的弱點。

## 限制

- 最適合遊戲邏輯是純 C#、從同一個地方推進的遊戲。用 Unity 物理、Animator、Timeline、協程或補間動畫驅動遊戲邏輯的，要先搬到自己的步進裡。
- bot 不等於玩家。這些數字適合在同一種 bot 打法下做比較（改動前後、A 對 B）；通關率本身的高低要拿真人試玩校準。
- 批次腳本本身跨平台，但 macOS、Linux 的執行檔還沒試過。
- 模擬步以外的程式只要從遊戲用的亂數抽過一次，同一個種子就跑不出同一局。原專案踩過的情況列在 `references/pitfalls.md`。

## 文件

- [SKILL.md](skills/unity-headless-sim/SKILL.md)：完整流程，一步一步（英文）
- [pitfalls.md](skills/unity-headless-sim/references/pitfalls.md)：不會報錯的坑，以及每個坑當時怎麼被發現（英文）
- [decision-model.md](skills/unity-headless-sim/references/decision-model.md)：把選卡時間軸一秒重播幾千次的模型，以及它的準確度限制（英文）

## 授權

[MIT](LICENSE)

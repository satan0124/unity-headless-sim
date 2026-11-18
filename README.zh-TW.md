# unity-headless-sim

**替 Unity 遊戲加上無畫面大量模擬的 Claude Code skill。**

[English](README.md) ｜ 繁體中文 ｜ [简体中文](README.zh-CN.md)

人工試玩一次只能玩幾局。這個 skill 讓 Claude 把你的遊戲改成可以不畫畫面、由 bot 操作、每局固定亂數種子連跑幾千局，最後回報通關率與 95% 信賴區間。跑的是遊戲本身的程式，不是另寫一份規則。

它是從一款用 Unity 6、全程式碼驅動的 2D 割草遊戲抽出來的。在那個專案裡，一局 15 分鐘無畫面跑完約 2～3 秒，同時開 10 個行程跑約 1,000 局不到 6 分鐘。

## Claude 會做什麼

1. **檢查專案**：找出會讓固定步長、可重現的模擬失效的東西，例如物理、協程與 Animator 驅動遊戲邏輯、遊戲邏輯裡讀 `Time.deltaTime`、沒設種子的亂數、邏輯分散在很多個 `Update`。
2. **拆開遊戲迴圈**：讓模擬可以從外部用固定的 `dt` 推進，和一般遊玩共用同一個步長。
3. **加上執行器**（`HeadlessRunner.cs`）：一個行程連跑多局，選單由 bot 當場選，每局之間還原存檔，每局寫一行 `RUN key=value ...`。
4. **確認可重現**：同一個種子一定跑出同一局；連跑時的第 N 局，和用那個種子單獨開一個行程跑的結果相同。
5. **批次跑**：多個行程平行跑、種子範圍互不重疊，彙整成表格和 `summary.csv`。
6. **（選用）選卡重播模型**：回答「選卡規則改了會怎樣」，一秒幾千局。

## 安裝

當外掛裝，在 Claude Code 裡輸入：

```
/plugin marketplace add satan0124/unity-headless-sim
/plugin install unity-headless-sim@unity-headless-sim
```

或把 `skills/unity-headless-sim/` 複製到 `~/.claude/skills/`（所有專案都能用）或 `<專案>/.claude/skills/`（只給單一專案）。

裝好後在 Unity 專案裡跟 Claude 說「加一個無畫面模擬模式，我要量通關率」之類的話就會用到。

## 內容

```
skills/unity-headless-sim/
  SKILL.md                    Claude 照著做的流程
  templates/
    IHeadlessSim.cs           遊戲要實作的介面
    HeadlessRunner.cs         命令列執行器（-headless -runs -seed -out -maxtime -think）
    GameLoopPatch.cs          拆遊戲迴圈的改前／改後範例
  scripts/
    audit_unity.py            掃 Assets/ 找會卡住的地方
    sim_batch.py              run（批次）／summarize（彙整）／determinism（可重現檢查）
  references/
    pitfalls.md               實際踩過、不會報錯的坑
    decision-model.md         選卡重播模型與它的準確度限制
```

腳本只需要 Python 3.8 以上，不用裝其他套件，不透過 Claude 也能直接用：

```
python scripts/audit_unity.py MyGame/Assets
python scripts/sim_batch.py run --exe Build/MyGame.exe --grid map=0,1,2 diff=0,1 --runs 100 --out sim_out
python scripts/sim_batch.py determinism --exe Build/MyGame.exe --seed 42
```

## 限制

- 最適合遊戲邏輯是純 C#、從同一個地方推進的遊戲。用 Unity 物理、Animator、Timeline、協程或補間動畫驅動遊戲邏輯的，要先把它們搬到自己的步進裡；檢查完如果不適合，Claude 會直接說，不會硬跑出看起來對、其實不對的數字。
- bot 不等於玩家。在原本的專案裡，三種 bot 打法讓同一名角色的通關率差了 30～60 個百分點。這些數字適合在同一種 bot 下做比較（改動前後、角色 A 對 B）；絕對的通關率要拿真人試玩校準。
- 只在 Windows＋Unity 6 上測過。批次腳本本身跨平台，但 macOS、Linux 的執行檔還沒試過。

## 授權

MIT

# Gesture Player Initial

手勢工作坊學員包：用自己的手勢控制競技場遊戲。

你會依序完成：設定環境 → 確認鏡頭 → 收集資料 → 實作辨識 → 訓練與驗證 → 連線遊玩。

本包已提供鏡頭讀取、手部關節偵測、資料錄製與競技場連線。你需要完成特徵正規化、KNN 分類、未知手勢拒絕、時間濾波，以及手勢到遊戲指令的對應。

這是實作起點，目前沒有訓練好的自訂手勢分類模型。 MediaPipe 提供的是已訓練好的「手部關節偵測模型」，用途是找出關節座標，不會替你完成遊戲手勢分類。尚未實作時，`train` 和 `run` 會提示未完成。

下方環境設定與操作指令可以直接使用；演算法部分提供工作項目與驗收標準，請自行設計並實作。

## 1. 設定環境

需要 Python 3.13、攝影機，以及首次下載依賴與關節模型所需的網路。建議使用 VS Code 編輯程式。遊戲網址：[https://ga-game.codpy.org/](https://ga-game.codpy.org/)。

先完整解壓縮學員包，在 VS Code 選「檔案 → 開啟資料夾」，開啟內含 `main.py` 的專案資料夾，再選「終端機 → 新增終端機」。接下來的指令都在這個資料夾執行。

### 建立環境與安裝套件

依自己的系統選一組指令。`.venv` 是專案自己的 Python 環境；`requirements-lock.txt` 列出所需套件與固定版本。這一段只需在第一次使用或重建環境時執行。

Windows：使用 PowerShell。

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe main.py prepare
.\.venv\Scripts\python.exe main.py check
```

macOS：使用 Terminal 的 zsh 或 bash。M 系列晶片請使用原生 Apple Silicon 的 Python 與終端機環境。

```bash
python3.13 --version
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements-lock.txt
./.venv/bin/python main.py prepare
./.venv/bin/python main.py check
```

Linux：使用本機桌面環境的 bash 或 zsh，並先安裝 Python 3.13。

```bash
python3.13 --version
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements-lock.txt
./.venv/bin/python main.py prepare
./.venv/bin/python main.py check
```

若 Linux 在建立 `.venv` 時提示缺少 `venv` 或 `ensurepip`，請安裝與 Python 3.13 對應的 venv 套件。以套件來源有提供該版本的 Ubuntu／Debian 系統為例：

```bash
sudo apt update
sudo apt install python3.13-venv
```

安裝後重新執行建立環境與安裝套件的指令。本包沒有使用 Tk 視窗，不需要另外安裝 Tk 套件。

各系統第一行應顯示 `Python 3.13.x`。`prepare` 下載並驗證關節模型；`check` 成功時會顯示 `Dependencies and landmark model OK`。這只代表依賴與關節模型可用，尚未測試鏡頭或你的辨識程式。

### 後續操作使用同一個環境

後面的範例統一使用 `python main.py ...`。每次重新開啟終端機，先回到專案資料夾並啟用環境。

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS／Linux：

```bash
source .venv/bin/activate
```

若 PowerShell 不允許執行啟用腳本，可以不啟用，將後續指令開頭的 `python` 換成 `.\.venv\Scripts\python.exe`。macOS／Linux 也可直接使用 `./.venv/bin/python`。

在 VS Code 按 `Ctrl+Shift+P`（Mac 為 `Cmd+Shift+P`），搜尋 `Python: Select Interpreter`，選本專案 `.venv` 的 Python，讓編輯器也使用相同環境。

## 2. 確認鏡頭與左右手

```powershell
python main.py camera --seconds 10
```

把左手、右手分別放到鏡頭前，觀察終端機的 `left=True`、`right=True` 是否對應正確。這裡的左右是使用者本人的左右手，不是畫面的左右。

本包沒有即時影像視窗，狀態會顯示在終端機；錄製完成後可自行開啟影片檢查。未指定 `--seconds` 時，按 `Ctrl+C` 停止。

若開到錯誤鏡頭，可試其他索引：

```powershell
python main.py camera --camera 1 --seconds 10
```

若左右手判定顛倒，可測試：

```powershell
python main.py camera --swap-hands --seconds 10
```

確認需要 `--camera` 或 `--swap-hands` 後，錄製與遊玩時也要使用相同設定。這些參數都能用在 `camera`、`record`、`run`。

鏡頭權限：Windows 請允許桌面應用程式使用攝影機；macOS 請在「系統設定 → 隱私權與安全性 → 攝影機」允許 VS Code／Terminal，必要時重啟應用程式；Linux 請確認目前帳號可存取攝影機裝置。請在可使用本機攝影機的桌面環境操作。

完成標準：鏡頭持續提供影格，左、右手能正確偵測，手移開後相應欄位會變成 `False`。

## 3. 設計並收集手勢資料

先用少量、容易區分的靜態手勢跑通流程，再增加類別或雙手組合。先決定每個手勢的名稱、使用哪隻手，以及要對應哪個遊戲動作。

以下只是設計範例，請依自己的手勢調整：

| 通道 | 自訂標籤 | 預計對應的指令 |
| --- | --- | --- |
| left | point_left | MOVE_LEFT |
| left | point_right | MOVE_RIGHT |
| right | fist | NORMAL_ATTACK |

`--label` 是你自行定義的分類標籤；`--channel` 表示這段資料要用於 `left`、`right` 或 `both` 的辨識。工具不會自動把標籤轉成遊戲指令，也不會替你判斷錄製時是否做對手勢。

擺好對應手勢後逐次錄製，例如：

```powershell
python main.py record --label point_left --channel left --seconds 10
python main.py record --label point_right --channel left --seconds 10
python main.py record --label fist --channel right --seconds 10
```

每次會在 `data/` 產生一組新的檔案，不覆寫舊檔：

| 檔案 | 用途 |
| --- | --- |
| `.mp4` | 檢查手勢、構圖與錄製品質；不含聲音 |
| `.jsonl` | 逐幀的標籤、通道、關節座標等資料，供訓練與分析使用 |

每個手勢分多次錄製，適度改變位置、距離與角度。錄完先看影片，避免把切換姿勢、做錯動作的影格當成正確範例。未偵測到手的影格也會保留，訓練時需自行處理。

另外錄一批獨立測試資料，可用 `--output` 放到其他資料夾。例如擺好 `fist` 後：

```powershell
python main.py record --label fist --channel right --seconds 10 --output data-test
```

其他類別也要收集測試資料。不要把這批資料拿去訓練，也不要只將同一段影片相鄰影格隨機拆成訓練與測試，否則容易高估效果。可另錄日常姿勢與手勢切換過程，檢查是否誤觸。

完成標準：每類都有多段可用資料與獨立測試資料，標籤、通道和實際手勢一致。

## 4. 完成自己的辨識流程

主要修改入口是 [`student/pipeline.py`](student/pipeline.py)。先閱讀 [`core/types.py`](core/types.py) 的輸入格式與 [`network/commands.py`](network/commands.py) 的回傳格式。

| 實作位置 | 需要完成的行為 |
| --- | --- |
| `train(data_dir, model_path)` | 讀取錄製資料，處理無效樣本、建立特徵，儲存 KNN 所需資料及必要設定 |
| `Pipeline.__init__(model_path)` | 載入模型與設定，初始化辨識所需狀態 |
| `Pipeline.predict(sample)` | 正規化與特徵擷取、KNN 分類、拒絕不確定結果、時間濾波、映射遊戲指令，回傳 `Commands` |
| `Pipeline.reset()` | 清除濾波與其他歷史狀態，避免上一回合結果影響下一回合 |

建議按以下順序實作，每完成一階段就用自己的資料驗證：

1. 特徵與正規化：決定如何減少手的位置、大小等差異。訓練與預測必須使用同一套轉換。
2. KNN：決定距離、鄰居數與投票方式。KNN 的訓練通常是準備並保存特徵與標籤，不一定有長時間的反覆學習。
3. 未知手勢拒絕：決定何時不應硬分到已知類別；缺手、低信心或未知姿勢應回到 `NONE`。
4. 時間濾波：讓結果穩定，同時控制延遲；缺手時需清除相應歷史，避免舊結果繼續輸出。
5. 指令映射：將自己的類別轉成競技場接受的指令，決定左右手與雙手的組合方式。

### 輸入資料

`sample.left`、`sample.right` 各為 `21 × 3` 的關節座標，未偵測到時是 `None`。另有 `width`、`height` 與 `timestamp`。

影像已鏡像；座標是 MediaPipe 的影像正規化座標，不是世界座標，也不代表已完成分類所需的特徵正規化。若換算像素尺度，x、z 對應影像寬度，y 對應影像高度。

JSONL 每行包含時間戳、標籤、通道、左右手原始座標、影像尺寸與鏡頭資訊。MP4 以固定 30 FPS 寫入，辨識速度較慢時影片長度可能與實際時間不同；資料分析以 JSONL 時間戳為準。

### 輸出指令

`Commands` 每次包含完整的 `left`、`right`、`both` 三欄，預設皆為 `NONE`，不是只回傳本次改變的欄位。

| 欄位 | 使用方式 |
| --- | --- |
| `left` | 左手辨識結果 |
| `right` | 右手辨識結果，可與左手同時輸出 |
| `both` | 雙手合成結果；使用時 `left`、`right` 必須都是 `NONE` |

可用指令：`MOVE_LEFT`、`MOVE_RIGHT`、`JUMP`、`CROUCH`、`BLOCK`、`NORMAL_ATTACK`、`ATTACK_SKILL`、`DEFENSE_SKILL`、`CONTROL_SKILL`、`ULTIMATE`、`NONE`。

工具會清空缺失手的輸出，但信心門檻、未知姿勢拒絕與濾波仍需自行實作。

## 5. 訓練與驗證

先完成 `train()`，再執行：

```powershell
python main.py train --data data --model models/model.npz
```

這個指令只是呼叫你的訓練入口。模型檔的儲存與載入方式由你實作；預設路徑是 `models/model.npz`，副檔名不會替你完成儲存。請自行建立需要的輸出資料夾。重新收集資料後，需要重新訓練才會更新模型。

目前沒有內建獨立的辨識測試指令。請自行撰寫測試程式或加入終端機辨識輸出，用第 3 步保留的資料驗證，不需先連競技場。

連線前應確認：

- 每個類別在獨立測試資料上都能辨識，並記錄正確率與容易混淆的類別。
- 缺手、陌生姿勢與切換手勢時，不會持續誤送遊戲指令。
- 結果夠穩定，反應延遲也能接受。
- `predict()` 回傳合法的 `Commands`，雙手合成不會混用單手指令。
- `reset()` 能清除歷史，模型能在重新啟動程式後載入。

完成並驗證各階段後，更新 `Pipeline.algorithms`：`normalization` 與 `knn` 應為 `True`；若 `filterEnabled` 為 `True`，`filter` 也必須為 `True`。這是實作狀態宣告，單純修改旗標不會產生辨識能力。工具與競技場都會檢查這些狀態。

## 6. 配對競技場並開始遊戲

開啟[遊戲網站](https://ga-game.codpy.org/)，確認能進入後：

1. 在競技場建立或加入房間。
2. 選擇辨識器輸入，取得六位數配對碼。
3. 執行 `run`，提供網址與配對碼；房間代碼可另外指定。

下方已使用遊戲網址；房間代碼 `ABCD` 與配對碼 `012345` 是範例，請換成網站顯示的實際值：

```powershell
python main.py run --server "https://ga-game.codpy.org" --room "ABCD" --pair-code "012345" --model models/model.npz
```

使用上述遊戲網址，不需加 `/controller`。配對碼保留開頭的零。若先前有指定鏡頭或修正左右手，也要在此加上相同參數。

看到 `Paired: room=...; ready/start in arena` 後，回到競技場網站準備並開始。`run` 會持續讀取鏡頭、呼叫你的辨識流程並傳送指令。按 `Ctrl+C` 停止；斷線後重新取得配對碼，再啟動一次。

### 遊戲操作時要知道的事

- 移動、蹲下、防禦是持續狀態；維持對應手勢即可持續輸出。
- 跳躍、攻擊與技能是在進入指令狀態時觸發，維持同一手勢不會連發。必須離開該指令至少 6 個遊戲 tick 才能再次觸發；遊戲為 60 tick/s。
- 左右手可同時維持兩個指令；相同指令合併一次，相反移動方向抵銷。
- 同時送出不代表兩個動作必定成功，冷卻、資源、硬直與空中限制仍由競技場判斷。兩個一次性指令按左手、右手順序嘗試。

完成標準：配對成功後，能用手勢控制遊戲；放下手或回到中立姿勢能停止持續動作，重新開始回合也不會沿用舊辨識結果。

## 常見問題

| 狀況 | 檢查方式 |
| --- | --- |
| 找不到 Python 3.13 | 確認已安裝該版本，且 Windows Python Launcher 能透過 `py -3.13` 找到它 |
| 缺少套件 | 確認使用專案的虛擬環境，並以同一個 Python 安裝 `requirements-lock.txt` |
| 缺少關節模型或雜湊不符 | 執行 `prepare`；若既有檔案損壞，移除 `assets/models/hand_landmarker.task` 後重新下載 |
| 鏡頭無法開啟 | 檢查系統攝影機權限、其他程式是否占用，並嘗試 `--camera 1` |
| `train` 顯示 `NotImplementedError` 或 `Implement student.pipeline.train` | 訓練入口仍未完成，請回到第 4 步 |
| `run` 顯示 `Student pipeline is unfinished` | 檢查演算法實作與 `Pipeline.algorithms` 的狀態宣告 |
| `predict` 顯示尚未實作 | 完成 `Pipeline.predict()`；只更新演算法旗標仍無法辨識 |
| 配對失敗或無法連線 | 確認網站可開啟、網址與埠號正確、配對碼仍有效 |
| 已配對但人物沒反應 | 確認網站已準備並開始，再檢查辨識輸出、指令映射，以及遊戲的冷卻／資源限制 |
| 攻擊只觸發一次 | 先離開攻擊指令再做一次手勢；維持手勢不會自動連打 |

## 指令速查

所有指令都在專案資料夾執行。可用 `python main.py --help` 或 `python main.py record --help` 等方式查看完整參數。

| 子命令 | 用途 |
| --- | --- |
| `prepare` | 下載並驗證關節模型，需要網路 |
| `check` | 檢查依賴與關節模型，不開鏡頭 |
| `camera` | 開鏡頭，在終端機顯示左右手偵測狀態 |
| `record` | 錄製 MP4 與逐幀 JSONL，需要 `--label`、`--channel` |
| `train` | 呼叫你的訓練入口，可指定 `--data`、`--model` |
| `run` | 呼叫你的辨識入口並連線，需要 `--server`、`--pair-code`；可指定 `--room`、`--model` |

`data/`、`models/` 與下載的 `assets/models/` 不納入版本控制，備份或交付時請另外確認。錄製與辨識過程中的影像、關節資料不會由本包上傳競技場。

## 附錄：連線與協定參考

一般實作可直接使用內附的 `network/arena_client.py`，它已處理配對、輸入封包、序號、心跳與狀態切換。辨識每幀執行，網路輸出上限約每秒 10 次；停止時送出中立狀態並關閉連線。比賽／階段／世代變更時，主流程呼叫 `reset()`，傳輸層短暫送出中立狀態，以解除競技場安全鎖。

若自行實作傳輸，協定如下：

| 項目 | 規格 |
| --- | --- |
| 傳輸 | Socket.IO，path 為 `socket.io`，namespace 為 `/controller`，不是原生 WebSocket |
| 配對 | `controller:pair`：`requestId`、`protocolVersion: 1`、`roomCode`（可空字串）、`pairCode`（保留前導零的字串）、`source: recognizer`、`algorithms` |
| 演算法狀態 | `algorithms` 中 `normalization`、`knn` 需為 true；`filterEnabled` 為 true 時 `filter` 也需為 true |
| 配對回覆 | 檢查 `ok`；保留 `sessionId`、`matchId`、`generation`，後續以 `controller:context` 更新 |
| 輸入事件 | `input:state`，每份封包含 `protocolVersion: 1`、`sessionId`、`matchId`（可 null）、`generation`、遞增非負整數 `seq`、`commands` |
| 三通道內容 | `commands` 必須完整包含 `left`、`right`、`both`，值為上列指令 |
| 回覆 | `ok`、成功時的 `seq`；失敗時的 `errorCode`。例如 `INVALID_INPUT`、`STALE_SEQ`、`STALE_GENERATION`、`STALE_MATCH`、`ALGORITHMS_REQUIRED` |
| 心跳 | `client:heartbeat`，建議每 0.5 秒；持續輸入也更新連線時間 |
| 安全狀態 | 啟動／恢復遊戲先送三欄皆 `NONE`；超過 30 tick 無新輸入，核心清除持續動作 |

欄位驗證見 `protocol/schemas/input-state.schema.json`。

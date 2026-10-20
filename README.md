# Gesture Player Initial

手勢工作坊學員包：用自己的手勢控制競技場遊戲。

你會依序完成：設定環境 → 確認鏡頭 → 收集資料 → 實作辨識 → 訓練與驗證 → 連線遊玩。

本包提供鏡頭讀取、MediaPipe 初始化與推論、原始關節預覽與錄製，以及競技場連線。從 MediaPipe 原始結果到遊戲指令的決策流程，由你完成：左右手整理、可靠度判斷、座標選擇、資料清理、特徵正規化、KNN 分類、未知手勢拒絕、時間濾波與指令映射。

這是實作起點，目前沒有訓練好的自訂手勢分類模型。 MediaPipe 提供的是已訓練好的「手部關節偵測模型」，用途是找出關節座標，不會替你完成遊戲手勢分類。尚未實作時，`train` 和 `run` 會提示未完成。

閱讀時先掌握下方的專案架構，再依第 1～6 節操作。指令範例會說明用途與需要調整的參數；演算法部分提供工作項目與驗收標準，請自行設計並實作。

學員實作入口 `student/pipeline.py` 保留原始 TODO 與未完成旗標；本包不包含 Demo 的辨識實作、訓練資料或自訂手勢模型。鏡頭、網路傳送與介面相容性更新屬於共用工具維護，辨識演算法仍需由學員自行完成。

## 專案架構與資料流程

這個專案分成三部分：`core/` 取得影像與原始手部資料，`student/` 將資料轉成遊戲指令，`network/` 負責與競技場通訊。`main.py` 是操作入口，將這些部分串起來。

```text
main.py                    命令列入口：環境檢查、鏡頭、錄製、訓練、連線
core/
  camera.py                讀取攝影機，提供鏡像影像
  landmarks.py             呼叫 MediaPipe，取得原始手部資料
  types.py                 定義 RawHand 與 RawHandSample
  preview.py               顯示影像與原始關節疊圖
  resources.py             下載與驗證 MediaPipe 關節模型
student/
  pipeline.py              學員實作：訓練、辨識、狀態重設
network/
  commands.py              定義合法的 Commands 輸出
  arena_client.py          處理配對、傳送指令與連線狀態
  preview.py               將現有鏡頭影像與骨架轉成網站預覽
protocol/                  競技場通訊規格與範例封包
tests/                     工具與介面契約的測試
requirements-lock.txt      套件與固定版本
```

錄製、訓練與遊玩是三個不同階段：

```text
錄製 record
  鏡頭 → MediaPipe → 原始關節資料 + 手動提供的標籤／通道 → data/*.jsonl
  鏡頭 → 鏡像影像 → data/*.mp4（供人工檢查）

訓練 train（由學員實作）
  data/*.jsonl → 清理與取樣 → 特徵轉換 → 儲存 KNN 資料與設定 → models/

遊玩 run
  鏡頭 → MediaPipe → RawHandSample → Pipeline.predict() → Commands → 競技場
                                         ↑
                                  載入訓練時保存的模型與設定
```

`camera` 與 `record` 可以在辨識流程尚未完成時使用。`train` 與 `run` 則會呼叫 `student/pipeline.py`，需要先完成相應入口。訓練與遊玩時的特徵轉換必須一致。

兩種模型也要分清楚：`assets/models/hand_landmarker.task` 是工具下載的 MediaPipe 關節模型；`models/model.npz` 是預設的自訂手勢模型路徑，內容與儲存方式由你實作。`data/`、`models/` 等輸出資料夾會在使用工具或實作儲存流程後產生，不一定出現在剛解壓縮的專案裡。

閱讀程式時，建議從 `core/types.py` 看輸入、`network/commands.py` 看輸出，再到 `student/pipeline.py` 完成兩者之間的辨識流程。需要理解工具如何呼叫它們時，再看 `main.py`。

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

安裝後重新執行建立環境與安裝套件的指令。關節預覽使用 OpenCV 視窗，不需要另外安裝 Tk 套件。

各系統第一行應顯示 `Python 3.13.x`。`prepare` 下載並驗證關節模型；`check` 成功時會顯示 `Dependencies and landmark model OK`。這只代表依賴與關節模型可用，尚未測試鏡頭或你的辨識程式。

上面各行分別負責不同的事，若某一步失敗，先處理該步的錯誤：

| 指令部分 | 用途 |
| --- | --- |
| `--version` | 確認使用的 Python 版本 |
| `-m venv .venv` | 建立這個專案專用的 Python 環境 |
| `-m pip install -r requirements-lock.txt` | 用該環境的 Python 安裝指定套件 |
| `main.py prepare` | 執行專案工具，準備關節模型 |
| `main.py check` | 檢查套件與關節模型是否可用 |

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

## 2. 確認鏡頭與 MediaPipe 關節

```powershell
python main.py camera --preview --seconds 10
```

視窗會顯示鏡頭影像、每隻手的 21 個關鍵點與連線，以及 MediaPipe 原始左右手分類與分數。這只用來確認模型能抓到手，沒有套用學員的分類或可靠度判斷。分數是左右手分類分數，不是手勢辨識正確率，也不是關節座標精準度。

預覽影像已鏡像。`hand[0]`、`hand[1]` 是該幀的模型輸出順序，不代表固定左右手，也不是跨影格的追蹤 ID。

預覽視窗取得焦點時，按 `Q`、`Esc` 或關閉視窗可停止；終端機也可按 `Ctrl+C`。未指定 `--seconds` 時會持續執行。不加 `--preview` 則只在終端機顯示 `hands=...`，不開視窗。

若開到錯誤鏡頭，可試其他索引：

```powershell
python main.py camera --camera 1 --preview --seconds 10
```

`--camera`、`--seconds`、`--preview` 都可用在 `camera`、`record`、`run`。錄製與遊玩時，請使用確認過的鏡頭索引。工具不替你修正左右手，如何解讀分類、處理鏡像與分配左右手，由你實作。

鏡頭權限：Windows 請允許桌面應用程式使用攝影機；macOS 請在「系統設定 → 隱私權與安全性 → 攝影機」允許 VS Code／Terminal，必要時重啟應用程式；Linux 請確認目前帳號可存取攝影機裝置。預覽需要可開啟視窗的本機桌面環境。

完成標準：鏡頭持續提供影格，手放入鏡頭時能看見關鍵點；手移開時偵測數量回到零。

## 3. 設計並收集手勢資料

先決定每個手勢的名稱、使用哪隻手，以及要對應哪個遊戲動作。

### 十個動作的錄製清單

需要錄製的十個遊戲動作如下：

| 序號 | 遊戲動作 | 對應指令 |
| --- | --- | --- |
| 1 | 向左移動 | `MOVE_LEFT` |
| 2 | 向右移動 | `MOVE_RIGHT` |
| 3 | 跳躍 | `JUMP` |
| 4 | 蹲下 | `CROUCH` |
| 5 | 防禦 | `BLOCK` |
| 6 | 普通攻擊 | `NORMAL_ATTACK` |
| 7 | 攻擊技能 | `ATTACK_SKILL` |
| 8 | 防禦技能 | `DEFENSE_SKILL` |
| 9 | 控制技能 | `CONTROL_SKILL` |
| 10 | 終極技能 | `ULTIMATE` |

### 標籤、通道與錄製範例

以下只是設計範例，請依自己的手勢調整：

| 通道 | 自訂標籤 | 預計對應的指令 |
| --- | --- | --- |
| left | point_left | MOVE_LEFT |
| left | point_right | MOVE_RIGHT |
| right | fist | NORMAL_ATTACK |

`--label` 是你自行定義的分類標籤；`--channel` 表示這段資料預計用於 `left`、`right` 或 `both`，是你提供的標註，不是工具判定的左右手。錄製時仍會保存所有偵測到的手，不依通道篩選。工具不會自動把標籤轉成遊戲指令，也不會替你判斷錄製時是否做對手勢。

擺好對應手勢後逐次錄製，例如：

```powershell
python main.py record --label point_left --channel left --seconds 10
python main.py record --label point_right --channel left --seconds 10
python main.py record --label fist --channel right --seconds 10 --preview
```

每次會在 `data/` 產生一組新的檔案，不覆寫舊檔：

| 檔案 | 用途 |
| --- | --- |
| `.mp4` | 檢查手勢、構圖與錄製品質；不含聲音 |
| `.jsonl` | 逐幀的標籤、通道、關節座標等資料，供訓練與分析使用 |

每個手勢分多次錄製，適度改變位置、距離與角度。錄完先看影片，避免把切換姿勢、做錯動作的影格當成正確範例。未偵測到手、低左右手分類分數，或左右手分類衝突的影格都會保留，訓練時需自行清理、取樣與決定可靠度標準。

另外錄一批獨立測試資料，可用 `--output` 放到其他資料夾。例如擺好 `fist` 後：

```powershell
python main.py record --label fist --channel right --seconds 10 --output data-test
```

其他類別也要收集測試資料。不要把這批資料拿去訓練，也不要只將同一段影片相鄰影格隨機拆成訓練與測試，否則容易高估效果。可另錄日常姿勢與手勢切換過程，檢查是否誤觸。

完成標準：上述十個動作各有多段可用訓練資料與另行錄製的獨立測試資料，標籤、通道和實際手勢一致，且已記下每個標籤對應的遊戲指令。

## 4. 完成自己的辨識流程

主要修改入口是 [`student/pipeline.py`](student/pipeline.py)。先閱讀 [`core/types.py`](core/types.py) 的輸入格式與 [`network/commands.py`](network/commands.py) 的回傳格式。

| 實作位置 | 需要完成的行為 |
| --- | --- |
| `train(data_dir, model_path)` | 讀取錄製資料，處理無效樣本、建立特徵，儲存 KNN 所需資料及必要設定 |
| `Pipeline.__init__(model_path)` | 載入模型與設定，初始化辨識所需狀態 |
| `Pipeline.predict(sample)` | 解讀原始手部資料、分配左右手、判斷可靠度，再做特徵擷取、KNN、拒絕、濾波與指令映射，回傳 `Commands` |
| `Pipeline.reset()` | 清除濾波與其他歷史狀態，避免上一回合結果影響下一回合 |

建議按以下順序實作，每完成一階段就用自己的資料驗證：

1. 原始結果整理：理解 `sample.hands`，自行分配左右手。決定如何使用分類分數、處理同側衝突、缺手與鏡像；不要把陣列索引當成左右手或固定追蹤 ID。
2. 資料清理與取樣：處理無效影格、類別數量不平衡與相鄰影格重複；保留獨立錄製的測試資料。
3. 特徵與正規化：選擇影像座標或三維座標，決定如何減少位置、大小等差異。訓練與預測必須使用同一套轉換。
4. KNN：決定距離、鄰居數與投票方式。訓練通常是準備並保存特徵與標籤，不一定有長時間的反覆學習。
5. 未知手勢拒絕：決定何時不應硬分到已知類別；缺手、低信心或未知姿勢應回到 `NONE`。
6. 時間濾波：讓結果穩定，同時控制延遲；缺少某隻手時，清除相應歷史，避免舊結果繼續輸出。
7. 指令映射與評估：轉成合法遊戲指令，處理左右手與雙手組合，並用獨立資料檢查效果。

### 輸入資料

`Pipeline.predict(sample)` 收到 `RawHandSample`。`sample.hands` 保留本幀所有偵測到的手，沒有手時是空清單 `[]`，不提供預先整理好的左右手欄位。

每個 `sample.hands[i]` 包含：

| 欄位 | 內容 |
| --- | --- |
| `landmarks` | 21 個 `[x, y, z]` 的清單，使用影像正規化座標 |
| `world_landmarks` | 同樣 21 個 `[x, y, z]`，單位為公尺，以該隻手的幾何中心為原點 |
| `handedness` | 模型回傳的分類清單，每筆保留 `index`、`category_name`、`display_name`、`score` |

不同手的三維座標各有自己的原點，不能直接當成同一個場景座標系來計算雙手間距。影像座標也不代表已完成分類所需的特徵正規化；若換算像素尺度，x、z 對應影像寬度，y 對應影像高度。

樣本另有 `width`、`height`、`timestamp`、`camera`、`image_mirrored` 與 `capture_version`。輸入影像已鏡像，`image_mirrored` 為 `True`，目前資料格式標記為 `mediapipe-raw-v1`。

JSONL 每行保存以上欄位與 `label`、`channel`；其中 `hands` 的每一項包含上述三組原始資訊。工具不額外依左右手分類分數過濾，MediaPipe 自身的偵測與追蹤仍使用模型設定。沒有手的影格也會保存為 `hands: []`。

MP4 保存未畫關節的鏡像影像、不含聲音，以固定 30 FPS 寫入。辨識速度較慢時影片長度可能與實際時間不同；資料分析以 JSONL 時間戳為準。

### 輸出指令

`Commands` 每次包含完整的 `left`、`right`、`both` 三欄，預設皆為 `NONE`，不是只回傳本次改變的欄位。

| 欄位 | 使用方式 |
| --- | --- |
| `left` | 左手辨識結果 |
| `right` | 右手辨識結果，可與左手同時輸出 |
| `both` | 雙手合成結果；使用時 `left`、`right` 必須都是 `NONE` |

可用指令：`MOVE_LEFT`、`MOVE_RIGHT`、`JUMP`、`CROUCH`、`BLOCK`、`NORMAL_ATTACK`、`ATTACK_SKILL`、`DEFENSE_SKILL`、`CONTROL_SKILL`、`ULTIMATE`、`NONE`。

`predict()` 每幀都會被呼叫，包含 `hands: []` 的情況。左右手是否缺失、何時清除輸出與濾波歷史，都由你判斷；主流程不會代為清空某一側的指令。比賽狀態變更時，主流程仍會呼叫 `reset()`。

## 5. 訓練與驗證

先完成 `train()`，再執行：

```powershell
python main.py train --data data --model models/model.npz
```

這個指令只是呼叫你的訓練入口。模型檔的儲存與載入方式由你實作；預設路徑是 `models/model.npz`，副檔名不會替你完成儲存。請自行建立需要的輸出資料夾。重新收集資料後，需要重新訓練才會更新模型。

目前沒有內建獨立的辨識測試指令。請自行撰寫測試程式或加入終端機辨識輸出，用第 3 步保留的資料驗證，不需先連競技場。

連線前應確認：

- 每個類別在獨立測試資料上都能辨識，並記錄正確率與容易混淆的類別。
- 左右手分配正確，能處理低分數、同側衝突與輸出順序改變。
- 缺少一隻或全部的手、陌生姿勢與切換手勢時，不會持續誤送遊戲指令。
- 結果夠穩定，反應延遲也能接受。
- `predict()` 回傳合法的 `Commands`，雙手合成不會混用單手指令。
- `reset()` 能清除歷史，模型能在重新啟動程式後載入。

完成並驗證各階段後，更新 `Pipeline.algorithms`：`normalization` 與 `knn` 應為 `True`；若 `filterEnabled` 為 `True`，`filter` 也必須為 `True`。這是實作狀態宣告，單純修改旗標不會產生辨識能力。工具與競技場都會檢查這些狀態。

## 6. 配對競技場並開始遊戲

### PVP 連線（雙人對戰）

房號為六位純數字，例如 `123456`；下方指令的房號是示範，請以網站實際產生的房號為準。

1. 開啟[遊戲網站](https://ga-game.codpy.org/)，由一位玩家選擇 PVP「雙人對決」建立房間，將網站顯示的房號提供給另一位玩家。
2. 另一位玩家在網站輸入相同房號，按「加入房間」。紅、藍兩席各一位玩家；第三人可觀戰，觀戰席不必啟動辨識器。
3. 使用手勢的玩家各自在自己的網頁選擇控制來源「手勢辨識器」，按「產生配對碼」，並在自己的電腦執行下方指令。兩位玩家使用相同房號，但必須使用各自的六位數配對碼：

```powershell
.\.venv\Scripts\python.exe main.py run --server "https://ga-game.codpy.org" --room "123456" --pair-code "012345" --model models/model.npz
```

4. 將 `123456` 換成網站顯示的實際房號、`012345` 換成自己網頁產生的配對碼，保留配對碼開頭的零。看到 `Paired` 後回網站按「確認準備」；雙方就緒後自動倒數進入選技，選完後開戰。

房號供朋友加入同一場對戰；配對碼用來連接自己席位的 Python 辨識器，請勿共用對方的配對碼。Python 的 `--room` 可選填，省略時也能透過自己的配對碼找到席位。選擇「網站鍵盤」的玩家不需要啟動 Python 或取得配對碼，仍須按「確認準備」。雙方可以分別使用手勢或鍵盤。

macOS／Linux 將指令開頭換成 `./.venv/bin/python`；已啟用虛擬環境時可使用 `python`。網址不用加 `/controller`；配對碼過期或斷線後，請重新產生配對碼並啟動辨識器。離開房間後若要再玩，請重新加入或建立房間並配對。

### PVE 連線（不需要房號）

1. 開啟[遊戲網站](https://ga-game.codpy.org/)，選擇 PVE「一命連戰」。
2. 控制來源選擇「手勢辨識器」，按「產生配對碼」。
3. 在含有 `main.py` 的 Demo 或 initial 專案資料夾啟動辨識，將下方 `012345` 換成網站當下顯示的六位數配對碼：

```powershell
.\.venv\Scripts\python.exe main.py run --server "https://ga-game.codpy.org" --pair-code "012345" --model models/model.npz
```

4. 看到 `Paired` 後回到網站確認準備、選擇技能，倒數後開始挑戰。按「結束挑戰」會保存進行中挑戰的未完成紀錄、離開房間並回到首頁；再次遊玩需重新產生配對碼並啟動辨識器。

配對碼用來連接自己的 Python 辨識器，並非雙人邀請碼；保留開頭的零，PVE 不必加 `--room`。配對碼過期或斷線後，請重新產生。網址不用加 `/controller`。macOS／Linux 將指令開頭換成 `./.venv/bin/python`；已啟用虛擬環境時可使用 `python`。initial 需先完成自己的辨識實作並訓練模型，Demo 可使用隨附的模型。

`run` 會自動將鏡頭影像與手部骨架送到網站，無須加 `--preview`；加上 `--preview` 會另外開啟本機關節視窗。若有多支鏡頭，加上 `--camera 1` 選擇另一支。

### 指令反應與技能冷卻

辨識每幀更新；指令改變（包含回到 `NONE`）會立即傳送，相同狀態約每秒補送 10 次。傳送不會等待伺服器回覆後才繼續辨識；終端機的 `fps` 顯示目前實際處理影格數。

戰鬥畫面在氣條下方橫排顯示攻擊、防禦、控制及大招四個技能，以小型時鐘圓環和剩餘秒數顯示冷卻，鏡頭位於技能列下方。冷卻依伺服器遊戲時間顯示，暫停時不會繼續倒數；對手尚未公開的大招維持隱藏。

畫面下方的「收到」顯示伺服器接收的指令；「上次動作」顯示執行結果。未開戰、需要先回中立、硬直、冷卻、氣量不足或大招尚未解鎖時，會顯示對應原因。跳躍、普攻與技能仍需離開該手勢至少 0.1 秒才能再次觸發；持續保持同一手勢不會連發。

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
| 預覽無法開啟 | 確認在可開視窗的桌面環境操作，且安裝的是專案指定的 OpenCV 套件；不加 `--preview` 可只顯示終端機狀態 |
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
| `camera` | 開鏡頭，顯示手的偵測數量；加 `--preview` 顯示關節疊圖 |
| `record` | 錄製 MP4 與逐幀 JSONL，需要 `--label`、`--channel` |
| `train` | 呼叫你的訓練入口，可指定 `--data`、`--model` |
| `run` | 呼叫你的辨識入口並連線，需要 `--server`、`--pair-code`；可指定 `--room`、`--model` |

`data/`、`data-test/`、`models/` 與下載的 `assets/models/` 不納入版本控制，備份或交付時請另外確認。`run` 會將縮小的鏡頭影像與二維手部骨架經遊戲伺服器轉送到同場網頁；原始錄影與完整關節資料留在本機。

## 附錄：連線與協定參考

一般實作可直接使用內附的 `network/arena_client.py`，它已處理配對、輸入封包、序號、心跳與狀態切換。辨識每幀執行，相同狀態約每秒補送 10 次，指令變化立即傳送；停止時送出中立狀態並關閉連線。比賽／階段／世代變更時，主流程呼叫 `reset()`，傳輸層短暫送出中立狀態，以解除競技場安全鎖。

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

# Gesture Player Initial

手勢工作坊的最小學員包。從 terminal 開鏡頭、錄影、收集關節資料與連接競技場；沒有操作面板、預先訓練模型或辨識演算法答案。

## 你要完成的部分

從鏡頭取得手部關節，設計特徵與正規化，以 KNN 辨識自訂手勢，再用時間濾波降低抖動，將結果映射到競技場指令。訓練資料、距離定義、未知手勢拒絕、左右手與雙手的組合方式，由你決定。

實作入口是 `student/pipeline.py`：`train(data_dir, model_path)` 負責訓練與儲存；`Pipeline.predict(sample)` 負責辨識並回傳 `Commands`；`reset()` 清除濾波歷史。完成並驗證各階段後，更新 `Pipeline.algorithms` 的可用狀態。空白包的 `train` 和 `run` 會明確提示尚未實作，不會假裝完成辨識。

## 執行環境與工具

使用 Python 3.13，建立自己的虛擬環境，透過 pip 的 `-r requirements-lock.txt` 安裝依賴。從本資料夾執行 `python main.py`，各子命令的完整參數可用 `--help` 查詢。

| 子命令 | 用途與必要參數 |
| --- | --- |
| `prepare` | 下載並驗證 MediaPipe 關節模型，需要網路；這不是手勢分類模型 |
| `check` | 檢查依賴與關節模型，不開鏡頭 |
| `camera` | 開鏡頭並在 terminal 顯示左右手偵測狀態 |
| `record` | `--label` 自訂類別名稱、`--channel left/right/both`；寫入 MP4 與逐幀 JSONL |
| `train` | 呼叫你的訓練入口；可指定 `--data`、`--model` |
| `run` | 呼叫你的辨識入口並送入競技場；需要 `--server`、`--pair-code`，可指定 `--room`、`--model` |

鏡頭相關命令支援 `--camera` 選擇裝置、`--seconds` 限制時間、`--swap-hands` 修正裝置的左右手判定。未設定時間時以 Ctrl+C 停止。沒有影像視窗，影片可在錄製完成後自行開啟檢查。`run` 使用的伺服器網址是主機提供的 HTTP(S) 網址，包含埠號（若有），不需附加 `/controller`。

## 資料約定

`sample.left`、`sample.right` 各為 21 × 3 的關節座標，未偵測到時是 `None`。左右是使用者的解剖左右手，不是畫面左右；輸入影像已鏡像。座標是 MediaPipe 的影像正規化座標，並非已完成你需要的特徵正規化，也不是世界座標。`width`、`height` 與 `timestamp` 一起提供。

每次 `record` 產生一組新檔案，不覆寫舊資料。JSONL 每行包含時間戳、類別、通道、左右手原始座標、影像尺寸與鏡頭資訊；即使未找到手，也保留該幀。MP4 不含聲音，以固定 30 FPS 寫入，辨識速度較慢時影片長度可能與實際時間不同；資料分析以 JSONL 時間戳為準。分類資料與模型預設放在 `data/`、`models/`，不納入版本控制。

## 三個指令接口

`network.commands.Commands` 提供 `left`、`right`、`both` 三個欄位，預設皆為 `NONE`。每次回傳的是完整狀態，不是增量事件。

| 欄位 | 意義 |
| --- | --- |
| `left` | 左手辨識結果 |
| `right` | 右手辨識結果，可與左手同時輸出 |
| `both` | 雙手合成結果；使用時左右欄位必須都是 `NONE` |

可送指令：`MOVE_LEFT`、`MOVE_RIGHT`、`JUMP`、`CROUCH`、`BLOCK`、`NORMAL_ATTACK`、`ATTACK_SKILL`、`DEFENSE_SKILL`、`CONTROL_SKILL`、`ULTIMATE`、`NONE`。自訂手勢名稱不直接送給競技場，請自行映射。

左右手可同時維持兩個指令；相同指令合併為一次，相反移動方向抵銷。雙手合成算一個指令，不能同時混用單手指令。移動、蹲下、防禦是持續狀態；跳躍與攻擊／技能為進入狀態時觸發，持續維持不會連發，必須離開該指令至少 6 個遊戲 tick 才能重新觸發。遊戲為 60 tick/s。

同時送出不代表兩個動作必定成功：冷卻、資源、硬直與空中限制仍由競技場判斷。兩個一次性指令按左手、右手順序嘗試。缺手、低信心或未知手勢應回到 `NONE`；不要把舊辨識結果永久保留。工具會清空缺失手的輸出，但信心門檻與濾波仍是你的工作。

## 與競技場串接

先在競技場建立／加入房間，選擇辨識器輸入，取得六位數配對碼，再以 `run` 的參數提供網址及配對碼；房間代碼可另外指定。配對成功後，在競技場網站準備並開始。連線中斷後工具停止，重新取得配對碼再啟動。

內附 `network/arena_client.py` 處理配對、輸入封包、序號、心跳與狀態切換。辨識流程每幀執行，網路輸出上限約每秒 10 次；停止時送出中立狀態並關閉連線。比賽／階段／世代變更時清除辨識歷史並短暫送出中立狀態，以解除競技場的安全鎖。影像與關節資料不會由此學員包上傳競技場。

若自行實作傳輸，協定如下：

| 項目 | 規格 |
| --- | --- |
| 傳輸 | Socket.IO，path 為 `socket.io`，namespace 為 `/controller`，不是原生 WebSocket |
| 配對 | `controller:pair`：`requestId`、`protocolVersion: 1`、`roomCode`（可空字串）、`pairCode`（保留前導零的字串）、`source: recognizer`、`algorithms` |
| 演算法狀態 | `algorithms` 中 `normalization`、`knn` 需為 true；`filterEnabled` 為 true 時 `filter` 也需為 true |
| 配對回覆 | 檢查 `ok`；保留 `sessionId`、`matchId`、`generation`，後續以 `controller:context` 更新 |
| 輸入事件 | `input:state`，每份封包含 `protocolVersion: 1`、`sessionId`、`matchId`（可 null）、`generation`、遞增非負整數 `seq`、`commands` |
| 三通道內容 | `commands` 必須完整包含 `left`、`right`、`both`，值為上列指令；不能同時包含舊欄位 `gesture` |
| 回覆 | `ok`、成功時的 `seq`；失敗時的 `errorCode`。例如 `INVALID_INPUT`、`STALE_SEQ`、`STALE_GENERATION`、`STALE_MATCH`、`ALGORITHMS_REQUIRED` |
| 心跳 | `client:heartbeat`，建議每 0.5 秒；持續輸入也更新連線時間 |
| 安全狀態 | 啟動／恢復遊戲先送三欄皆 `NONE`；超過 30 tick 無新輸入，核心清除持續動作 |

欄位驗證見 `protocol/schemas/input-state.schema.json`。競技場需使用支援 `commands` 的版本；舊版單一 `gesture` 伺服器無法接收本包。競技場仍接受舊單指令客戶端，但新學員包使用三通道。

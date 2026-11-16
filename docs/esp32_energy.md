# ESP32 能量罐

ESP32 是外接的「能量罐」：辨識出技能手勢後，Python 端必須先詢問能量罐，獲准才把技能送到競技場；被拒絕時該通道改送 `NONE`。競技場本身的氣量、冷卻與硬直規則不變，兩者都通過才會施放。

```text
鏡頭 → MediaPipe → Pipeline.predict() → EnergyGate.filter() → ArenaClient.send() → 競技場
                                              │  ▲                                   │
                                     REQ/REFUND│  │OK/NO                 input:result │
                                              ▼  │                                   │
                                          ESP32 能量罐 ◀──── 競技場拒絕時 REFUND ─────┘
```

## 判斷流程

- 預設需要能量的指令：`ATTACK_SKILL`、`DEFENSE_SKILL`、`CONTROL_SKILL`、`ULTIMATE`。可用 `--energy-labels` 調整，例如加入 `NORMAL_ATTACK`。
- 每次「按下」只詢問一次。手勢維持期間沿用同一個結果；離開至少 0.12 秒才算放開，對應競技場離開 6 tick 才能再觸發的規則，辨識閃爍不會重複扣能量。
- 獲准後若競技場回報施放失敗（`input:result` 的 `reason` 不是 `OK`，例如 `COOLDOWN`、`INSUFFICIENT_QI`），或 1.5 秒內都沒有施放結果（例如準備區、倒數或中立期），Python 會送 `REFUND` 退回能量。
- ESP32 沒有回應（逾時 0.15 秒、斷線）時預設擋下技能；加 `--energy-fail-open` 則改為放行。
- 比賽／階段／世代變更時，與 `Pipeline.reset()` 一起清除按壓狀態。

## 序列協定

USB 序列埠，115200 baud，ASCII 文字，每行以 `\n` 結尾（`\r` 會被忽略）。`<id>` 是 Python 端遞增的整數，回覆以 id 對應請求；不認得的行（開機訊息、逾時請求的遲到回覆）一律忽略。

| PC → ESP32 | ESP32 → PC | 說明 |
| --- | --- | --- |
| `PING` | `PONG <energy> <capacity>` | 連線握手；開埠後 ESP32 可能重開機，Python 會在 3 秒內重試 |
| `REQ <id> <LABEL>` | `OK <id> <energy>` 或 `NO <id> <energy>` | 申請施放；`OK` 時已扣除該指令的能量 |
| `REFUND <id>` | `REFUNDED <id> <energy>` 或 `NO <id> <energy>` | 退回某次已獲准的能量；同一 id 只會退一次 |
| `FILL` | `PONG <energy> <capacity>` | 補滿能量（測試用） |

開機時 ESP32 會送出 `READY <energy> <capacity>`，Python 不依賴此行。

## 韌體

`firmware/esp32_energy_can/esp32_energy_can.ino`，使用 Arduino IDE 或 PlatformIO 搭配 ESP32 Arduino core 燒錄。檔案開頭可調整：

| 設定 | 預設 | 說明 |
| --- | --- | --- |
| `CAPACITY` | 6 | 滿罐能量 |
| `RECHARGE_MS` | 2000 | 每 2 秒回復 1 點 |
| `COSTS` | 攻擊 1、防禦 1、控制 2、大招 3；普攻、跳躍 0 | 每個指令消耗；未列出的指令一律拒絕 |
| `LED_PIN` | 2 | 獲准時閃 150ms，滿罐時常亮 |
| `BUTTON_PIN` | 0（BOOT 鍵） | 按下立即補滿，模擬換罐 |

ESP32-S3／C3 使用原生 USB 時，請在 Arduino IDE 啟用 **USB CDC On Boot**，`Serial` 才會走 USB 埠。

## 使用

```powershell
.\.venv\Scripts\python.exe main.py run --server "https://ga-game.codpy.org" --pair-code "012345" --energy-port COM5
```

Linux／macOS 的序列埠類似 `/dev/ttyUSB0`、`/dev/ttyACM0` 或 `/dev/cu.usbserial-*`；WSL 需先用 `usbipd` 轉接 USB 裝置。`--energy-port` 也接受 pyserial URL，例如 `socket://192.168.1.50:3333`，可接到自行加上 Wi-Fi TCP 轉接的 ESP32。

不加 `--energy-port` 時完全不使用能量罐，行為與原本相同。

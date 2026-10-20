# MediaPipe Hand Landmarker

本專案隨附未修改的 `hand_landmarker.task`，供手部關節偵測使用。下載或完整解壓縮專案後即可使用，不需另外向 Google 下載模型。這不是學員需要自行訓練的手勢分類模型。

- 提供者：Google / MediaPipe
- 版本：Hand Landmarker Full，float16，version 1
- 官方說明：https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
- 原始檔案：https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
- 官方模型卡：https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20%28Lite_Full%29%20with%20Fairness%20Oct%202021.pdf
- 授權：Apache License, Version 2.0，完整條款見 [LICENSE](LICENSE)。官方模型卡第 2 頁載明此授權。
- 檔案大小：7,819,105 bytes
- SHA-256：`fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`

執行 `python main.py check` 可檢查依賴與模型。若模型遺失，可執行 `python main.py prepare` 從原始來源補下載；若檔案損壞，先移除損壞檔案再執行 `prepare`。

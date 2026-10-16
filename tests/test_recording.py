import json
import sys
import types
import numpy as np
from main import capture, parser
from core.types import RawHandSample


def test_recording_without_windows_saves_samples_and_releases_on_interrupt(monkeypatch, tmp_path):
    closed = []
    class Camera:
        actual = {"index": 0}
        def __init__(self, index): self.count = 0
        def latest(self):
            self.count += 1
            if self.count > 2: raise KeyboardInterrupt
            return np.zeros((48, 64, 3), dtype=np.uint8), float(self.count)
        def close(self): closed.append("camera")
    class Detector:
        def __init__(self, **kwargs): pass
        def detect(self, frame, timestamp, camera):
            return RawHandSample(np.zeros((21, 3)), None, 64, 48, timestamp, camera=camera)
        def close(self): closed.append("detector")
    class Writer:
        def __init__(self, *args): self.count = 0
        def isOpened(self): return True
        def write(self, frame): self.count += 1
        def release(self): closed.append(f"video:{self.count}")
    import cv2
    monkeypatch.setitem(sys.modules, "core.camera", types.SimpleNamespace(Camera=Camera))
    monkeypatch.setitem(sys.modules, "core.landmarks", types.SimpleNamespace(Landmarks=Detector))
    monkeypatch.setattr(cv2, "VideoWriter", Writer)
    args = parser().parse_args(["record", "--label", "wave", "--channel", "left", "--output", str(tmp_path)])
    capture(args)
    rows = [json.loads(line) for line in next(tmp_path.glob("*.jsonl")).read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["channel"] == "left"
    assert rows[0]["right"] is None and len(rows[0]["left"]) == 21
    assert rows[1]["timestamp"] > rows[0]["timestamp"]
    assert closed == ["video:2", "camera", "detector"]

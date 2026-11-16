import argparse
from contextlib import ExitStack
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent


def positive(value):
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def labels(value):
    from network.commands import LABELS
    names = tuple(v.strip().upper() for v in value.split(",") if v.strip())
    if not names or any(v not in LABELS or v == "NONE" for v in names):
        raise argparse.ArgumentTypeError("must be arena labels other than NONE")
    return names


def parser():
    p = argparse.ArgumentParser(description="Gesture Player Initial — terminal tools")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="download and verify the landmark model")
    sub.add_parser("check", help="check dependencies and landmark model; no camera access")
    for name in ("camera", "record", "run"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--camera", type=int, default=0)
        cmd.add_argument("--seconds", type=positive, help="otherwise stop with Ctrl+C")
        cmd.add_argument("--preview", action="store_true",
                         help="show camera and raw landmarks; Q/Esc stops")
        if name == "record":
            cmd.add_argument("--label", required=True, help="your own gesture class name")
            cmd.add_argument("--channel", choices=("left", "right", "both"), required=True)
            cmd.add_argument("--output", type=Path, default=ROOT / "data")
        if name == "run":
            cmd.add_argument("--server", required=True)
            cmd.add_argument("--room", default="")
            cmd.add_argument("--pair-code", required=True)
            cmd.add_argument("--model", type=Path, default=ROOT / "models/model.npz")
            cmd.add_argument("--energy-port",
                             help="ESP32 energy can serial port (e.g. COM5, /dev/ttyUSB0); "
                                  "skills need its grant before release")
            cmd.add_argument("--energy-baud", type=int, default=115200)
            cmd.add_argument("--energy-labels", type=labels,
                             default="ATTACK_SKILL,DEFENSE_SKILL,CONTROL_SKILL,ULTIMATE",
                             help="comma-separated labels that need energy")
            cmd.add_argument("--energy-fail-open", action="store_true",
                             help="allow skills when the ESP32 does not answer (default: block)")
    train = sub.add_parser("train")
    train.add_argument("--data", type=Path, default=ROOT / "data")
    train.add_argument("--model", type=Path, default=ROOT / "models/model.npz")
    return p


def capture(args):
    import cv2
    from core.camera import Camera
    from core.landmarks import Landmarks
    from network.commands import Commands

    pipeline = client = gate = None
    if args.command == "run":
        from student.pipeline import Pipeline
        from network.arena_client import ArenaClient
        pipeline = Pipeline(args.model)
        flags = pipeline.algorithms
        if not (flags.get("normalization") and flags.get("classifier") and
                (not flags.get("filterEnabled") or flags.get("filter"))):
            raise RuntimeError("Student pipeline is unfinished; implement it and set algorithms availability")

    with ExitStack() as stack:
        detector = Landmarks()
        stack.callback(detector.close)
        camera = Camera(args.camera)
        stack.callback(camera.close)
        if pipeline and args.energy_port:
            from network.energy import EnergyGate, EnergyLink
            link = EnergyLink(args.energy_port, args.energy_baud)
            stack.callback(link.close)
            gate = EnergyGate(link, args.energy_labels, fail_open=args.energy_fail_open)
            print(f"Energy can ready: {link.energy}/{link.capacity} on {args.energy_port}", flush=True)
        if pipeline:
            client = ArenaClient()
            stack.callback(client.close)
            if gate:
                client.result_listener = gate.on_result
            result = client.connect(args.server, args.room, args.pair_code, pipeline.algorithms)
            print(f"Paired: room={result['roomCode']}; ready/start in arena", flush=True)
        if args.preview:
            from core.preview import show_preview
            stack.callback(cv2.destroyAllWindows)
        video = samples = None
        if args.command == "record":
            import uuid
            args.output.mkdir(parents=True, exist_ok=True)
            stem = args.output / f"capture-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
            samples = stack.enter_context(stem.with_suffix(".jsonl").open("x", encoding="utf-8"))
            print(f"Recording: {stem}.mp4 + .jsonl", flush=True)
        start = last_frame = last_report = time.monotonic()
        previous_timestamp = None
        revision = -1
        count = 0
        last_report_count = 0
        print("Camera running. Ctrl+C stops and closes files.", flush=True)
        try:
            while args.seconds is None or time.monotonic() - start < args.seconds:
                frame, timestamp = camera.latest()
                now = time.monotonic()
                if frame is None or timestamp == previous_timestamp:
                    if now - last_frame > 2:
                        raise RuntimeError("Camera stopped delivering frames")
                    time.sleep(.01)
                    continue
                previous_timestamp = timestamp
                last_frame = now
                sample = detector.detect(frame, timestamp, camera.actual)
                count += 1
                if samples is not None:
                    if video is None:
                        video = cv2.VideoWriter(str(stem.with_suffix(".mp4")),
                                                cv2.VideoWriter_fourcc(*"mp4v"), 30,
                                                (frame.shape[1], frame.shape[0]))
                        stack.callback(video.release)
                        if not video.isOpened():
                            raise RuntimeError("Cannot open MP4 writer")
                    video.write(frame)
                    samples.write(json.dumps({**asdict(sample), "label": args.label,
                                              "channel": args.channel}) + "\n")
                if pipeline:
                    current = client.revision
                    if current != revision:
                        pipeline.reset()
                        if gate:
                            gate.reset()
                        revision = current
                    # Students own handedness, missing-hand behavior and filtering.
                    commands = pipeline.predict(sample)
                    if not isinstance(commands, Commands):
                        raise TypeError("Pipeline.predict must return Commands")
                    if gate:
                        # Skills reach the arena only after the energy can grants them.
                        commands = gate.filter(commands)
                    client.send(commands, revision)
                    client.send_preview(frame, sample, revision)
                if args.preview and not show_preview(frame, sample):
                    break
                if now - last_report >= 1:
                    energy = f" energy={gate.link.energy}/{gate.link.capacity}" if gate else ""
                    print(f"fps={(count - last_report_count) / (now - last_report):.1f} frames={count} hands={len(sample.hands)}{energy}", flush=True)
                    last_report_count = count
                    last_report = now
        except KeyboardInterrupt:
            print("Stopped.")
        finally:
            print(f"Captured {count} frames.", flush=True)


def main():
    args = parser().parse_args()
    if args.command == "prepare":
        from core.resources import prepare
        print(json.dumps(prepare()))
    elif args.command == "check":
        import cv2, numpy, mediapipe, socketio
        from core.landmarks import Landmarks
        detector = Landmarks()
        detector.close()
        print("Dependencies and landmark model OK. Camera and student pipeline not tested.")
    elif args.command == "train":
        from student.pipeline import train
        train(args.data, args.model)
    else:
        capture(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

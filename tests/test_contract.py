import pytest
from main import parser
from network.commands import Commands
from student.pipeline import Pipeline, train


def test_channels():
    assert Commands("MOVE_LEFT", "BLOCK").payload() == {
        "left": "MOVE_LEFT", "right": "BLOCK", "both": "NONE"}
    assert Commands(both="JUMP").both == "JUMP"
    with pytest.raises(ValueError):
        Commands(left="BLOCK", both="JUMP")
    with pytest.raises(ValueError):
        Commands(right="custom gesture")


def test_starter_does_not_supply_answers():
    pipeline = Pipeline()
    assert not pipeline.algorithms["classifier"]
    assert "knn" not in pipeline.algorithms
    with pytest.raises(NotImplementedError):
        pipeline.predict(None)
    with pytest.raises(NotImplementedError):
        train(None, None)


def test_run_rejects_unfinished_classifier_even_with_legacy_knn(monkeypatch):
    import main

    monkeypatch.setattr(Pipeline, "algorithms", {
        "normalization": True, "classifier": False,
        "knn": True, "filterEnabled": False})
    args = parser().parse_args([
        "run", "--server", "https://example.test", "--pair-code", "000012"])
    with pytest.raises(RuntimeError, match="Student pipeline is unfinished"):
        main.capture(args)


def test_terminal_contract():
    args = parser().parse_args(["record", "--label", "wave", "--channel", "left", "--seconds", "2"])
    assert args.channel == "left" and args.seconds == 2
    assert parser().parse_args(["camera", "--preview"]).preview
    args = parser().parse_args(["run", "--server", "http://localhost:3000", "--pair-code", "000012"])
    assert args.pair_code == "000012"
    for value in ("0", "-1", "nan", "inf"):
        with pytest.raises(SystemExit):
            parser().parse_args(["camera", "--seconds", value])

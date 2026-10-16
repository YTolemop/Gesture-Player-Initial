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
    assert not pipeline.algorithms["knn"]
    with pytest.raises(NotImplementedError):
        pipeline.predict(None)
    with pytest.raises(NotImplementedError):
        train(None, None)


def test_terminal_contract():
    args = parser().parse_args(["record", "--label", "wave", "--channel", "left", "--seconds", "2"])
    assert args.channel == "left" and args.seconds == 2
    assert parser().parse_args(["camera", "--preview"]).preview
    args = parser().parse_args(["run", "--server", "http://localhost:3000", "--pair-code", "000012"])
    assert args.pair_code == "000012"
    for value in ("0", "-1", "nan", "inf"):
        with pytest.raises(SystemExit):
            parser().parse_args(["camera", "--seconds", value])

"""Implement your recognition pipeline here. No trained model is bundled."""
from network.commands import Commands


class Pipeline:
    # Declare availability only after implementing and verifying these stages.
    # normalization: preprocessing is ready (including a justified no-op).
    # classifier: your chosen classifier is ready; no specific method is required.
    algorithms = {"normalization": False, "classifier": False,
                  "filterEnabled": True, "filter": False}

    def __init__(self, model_path=None):
        self.model_path = model_path

    def reset(self):
        """Clear temporal history when the arena changes match/phase or disconnects."""
        pass

    def predict(self, sample) -> Commands:
        """sample.hands: raw detections (see core/types.py); return Commands.

        TODO: interpret handedness/scores, handle missing/conflicting hands,
        choose image/world coordinates, preprocessing, a classifier, rejection, filtering,
        and mapping left/right/both gestures to arena commands.
        An empty hands list is also passed here. Missing/uncertain hands must
        produce NONE and clear stale history; the runner does not do this for you.
        """
        raise NotImplementedError("Implement student.pipeline.Pipeline.predict")


def train(data_dir, model_path):
    """TODO: prepare and persist your chosen classifier/model or rule settings."""
    raise NotImplementedError("Implement student.pipeline.train")

"""Implement your recognition pipeline here. No trained model is bundled."""
from network.commands import Commands


class Pipeline:
    # Declare availability only after implementing and verifying these stages.
    algorithms = {"normalization": False, "knn": False,
                  "filterEnabled": True, "filter": False}

    def __init__(self, model_path=None):
        self.model_path = model_path

    def reset(self):
        """Clear temporal history when the arena changes match/phase or disconnects."""
        pass

    def predict(self, sample) -> Commands:
        """sample.left/right: (21,3) arrays or None; return all three channels.

        TODO: normalization, KNN prediction, rejection, temporal filtering,
        and mapping left/right/both gestures to arena commands.
        Missing or uncertain hands should produce NONE.
        """
        raise NotImplementedError("Implement student.pipeline.Pipeline.predict")


def train(data_dir, model_path):
    """TODO: build and persist your model from recorded samples."""
    raise NotImplementedError("Implement student.pipeline.train")

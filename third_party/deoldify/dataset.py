from .fastai_compat import *

# Training data loading logic is currently disabled due to FastAI 1.x deprecation.
# To restore training support, this module needs to be rewritten using pure PyTorch Datasets/DataLoaders.


def get_colorize_data(
    sz: int,
    bs: int,
    crappy_path: Path,
    good_path: Path,
    random_seed: int = None,
    keep_pct: float = 1.0,
    num_workers: int = 8,
    stats: tuple = None,
    xtra_tfms=[],
):
    raise NotImplementedError("Training data loading not supported in this version.")


def get_dummy_databunch():
    return DataBunch()

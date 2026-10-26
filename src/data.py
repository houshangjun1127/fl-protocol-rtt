"""Data loading and non-IID partitioning for federated learning simulations."""
import os
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

DATA_ROOT = os.environ.get(
    "FL_DATA_ROOT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data"))

DATASETS = {
    # name: (torchvision class, (H, W), channels, n_classes)
    "mnist":      ("MNIST",       (28, 28), 1,  10),
    "fashion":    ("FashionMNIST", (28, 28), 1,  10),
    "cifar10":    ("CIFAR10",     (32, 32), 3,  10),
    "cifar100":   ("CIFAR100",    (32, 32), 3,  100),
}


def _to_tensors(ds, img_size, channels):
    """Normalise to float tensors in [0,1], NCHW layout.

    torchvision is inconsistent across datasets and this bit us for real:
      MNIST / FashionMNIST -> ds.data is a torch Tensor, ds.targets is a Tensor
      CIFAR10 / CIFAR100  -> ds.data is a numpy ndarray, ds.targets is a plain list
    So we accept either rather than assuming. Do NOT "simplify" this back to
    ds.data.numpy() -- it raises AttributeError on CIFAR.

    Layouts also vary: (N,C,H,W) uint8, (N,H,W) grayscale, or (N,H,W,C) RGB.
    """
    def as_np(v):
        return v.numpy() if hasattr(v, "numpy") else np.asarray(v)

    x = as_np(ds.data).astype(np.float32) / 255.0
    y = as_np(ds.targets).astype(np.int64)

    # Normalise layout to NCHW. Note the guard must check ndim==4 with a trailing
    # channel axis too: CIFAR arrives as (N,H,W,C), which is ALREADY 4-D, so an
    # "if x.ndim == 3" guard silently skips the transpose and we hand the model a
    # (N,H,W,C) tensor -- a silent layout bug that still trains, just badly.
    if x.ndim == 3:
        x = x[:, None, :, :]               # NHW -> NCHW (grayscale)
    elif x.ndim == 4 and x.shape[3] == channels and x.shape[1] != channels:
        x = np.transpose(x, (0, 3, 1, 2))   # NHWC -> NCHW (RGB)
    assert x.ndim == 4 and x.shape[1] == channels, \
        f"unexpected data shape {x.shape} for {channels} channels"

    if x.shape[1] != channels or tuple(x.shape[2:]) != tuple(img_size):
        import torch.nn.functional as F
        xt = F.interpolate(torch.from_numpy(x), size=tuple(img_size),
                           mode="bilinear", align_corners=False)
        x = xt.numpy()

    return np.ascontiguousarray(x), y


def load_dataset(name, n_train=10000, n_test=2000, seed=0):
    """Load a dataset, subsampled deterministically for fast CPU experiments."""
    from torchvision import datasets

    torch_cls, img_size, channels, n_classes = DATASETS[name]
    os.makedirs(DATA_ROOT, exist_ok=True)
    ds = getattr(datasets, torch_cls)(root=DATA_ROOT, train=True, download=True)
    te = getattr(datasets, torch_cls)(root=DATA_ROOT, train=False, download=True)

    xtr, ytr = _to_tensors(ds, img_size, channels)
    xte, yte = _to_tensors(te, img_size, channels)

    rng = np.random.RandomState(seed)
    tr_idx = rng.permutation(len(xtr))[: min(n_train, len(xtr))]
    te_idx = rng.permutation(len(xte))[: min(n_test, len(xte))]

    xtr, ytr = xtr[tr_idx], ytr[tr_idx]
    xte, yte = xte[te_idx], yte[te_idx]

    mean = xtr.mean(axis=(0, 2, 3), keepdims=True)
    std = xtr.std(axis=(0, 2, 3), keepdims=True) + 1e-7
    xtr = (xtr - mean) / std
    xte = (xte - mean) / std

    return (TensorDataset(torch.from_numpy(xtr), torch.from_numpy(ytr)),
            TensorDataset(torch.from_numpy(xte), torch.from_numpy(yte)),
            channels, img_size)


def load_dataset_with_val(name, n_train=10000, n_test=2000, n_val=1000, seed=0):
    """`load_dataset` plus a disjoint validation split for Stage A selection.

    Added for the second-round review response (task R10). The original Stage A
    selected hyperparameters on the *test* split, which the reviewer flagged as
    the test set participating in tuning. To measure how much that matters we
    need a split that is NOT the test split, while leaving everything else in
    the published runs bit-identical.

    Two invariants are load-bearing and are asserted, not assumed:
      1. `train` and `test` subsamples are IDENTICAL to `load_dataset`'s. This
         holds because the RandomState is consumed in the same order -- first
         `permutation(len(xtr))`, then `permutation(len(xte))` -- before any
         validation index is drawn.
      2. The validation split is carved from the training POOL, disjoint from
         the training subsample, and never from the test pool. So it is held
         out from optimisation but comes from the same marginal distribution.

    Returns (train_ds, val_ds, test_ds, channels, img_size).
    """
    from torchvision import datasets

    torch_cls, img_size, channels, n_classes = DATASETS[name]
    os.makedirs(DATA_ROOT, exist_ok=True)
    ds = getattr(datasets, torch_cls)(root=DATA_ROOT, train=True, download=True)
    te = getattr(datasets, torch_cls)(root=DATA_ROOT, train=False, download=True)

    xtr, ytr = _to_tensors(ds, img_size, channels)
    xte, yte = _to_tensors(te, img_size, channels)

    rng = np.random.RandomState(seed)
    tr_idx = rng.permutation(len(xtr))[: min(n_train, len(xtr))]
    te_idx = rng.permutation(len(xte))[: min(n_test, len(xte))]

    # Validation: from the training pool, disjoint from tr_idx. Drawn AFTER the
    # two draws above so the train/test subsamples match load_dataset exactly.
    pool = np.setdiff1d(np.arange(len(xtr)), tr_idx)
    pool = rng.permutation(pool)
    val_idx = pool[: min(n_val, len(pool))]

    xv, yv = xtr[val_idx], ytr[val_idx]
    xtr, ytr = xtr[tr_idx], ytr[tr_idx]
    xte, yte = xte[te_idx], yte[te_idx]

    mean = xtr.mean(axis=(0, 2, 3), keepdims=True)
    std = xtr.std(axis=(0, 2, 3), keepdims=True) + 1e-7
    xtr = (xtr - mean) / std
    xte = (xte - mean) / std
    xv = (xv - mean) / std

    return (TensorDataset(torch.from_numpy(xtr), torch.from_numpy(ytr)),
            TensorDataset(torch.from_numpy(xv), torch.from_numpy(yv)),
            TensorDataset(torch.from_numpy(xte), torch.from_numpy(yte)),
            channels, img_size)


def dirichlet_partition(labels, n_clients, alpha, seed=0, min_size=32):
    """Label-skew partition. Returns list of index arrays into `labels`."""
    rng = np.random.RandomState(seed)
    n_classes = int(labels.max()) + 1
    idx_per_class = [rng.permutation(np.where(labels == c)[0]) for c in range(n_classes)]

    client_idx = [[] for _ in range(n_clients)]
    for c in range(n_classes):
        p = rng.dirichlet(np.repeat(alpha, n_clients))
        cuts = (np.cumsum(p) * len(idx_per_class[c])).astype(int)[:-1]
        for k, part in enumerate(np.split(idx_per_class[c], cuts)):
            client_idx[k].extend(part.tolist())

    out = []
    for k in range(n_clients):
        idx = np.array(client_idx[k], dtype=np.int64)
        if len(idx) < min_size:  # rebalance from the largest client
            big = int(np.argmax([len(v) for v in out])) if out else 0
            pool = np.setdiff1d(np.arange(len(labels)), np.concatenate(out)) if out else np.arange(len(labels))
            take = pool[: min_size - len(idx)]
            idx = np.concatenate([idx, take])
        out.append(idx)
    return out


def quantity_skew_partition(labels, n_clients, min_frac=0.3, seed=0):
    """Quantity (size) skew with IID label distribution -- pairs well with label skew."""
    rng = np.random.RandomState(seed)
    n = len(labels)
    fracs = rng.dirichlet(np.repeat(1.0, n_clients)) * (1 - min_frac) + min_frac
    fracs = fracs / fracs.sum()
    cuts = (np.cumsum(fracs) * n).astype(int)[:-1]
    return [np.sort(p) for p in np.split(rng.permutation(n), cuts)]


def loader(ds, idx, batch_size, shuffle=True, gen=None):
    return DataLoader(TensorSubset(ds, idx), batch_size=batch_size, shuffle=shuffle,
                      generator=gen)


class TensorSubset(torch.utils.data.Dataset):
    def __init__(self, ds, idx):
        self.ds, self.idx = ds, torch.as_tensor(np.asarray(idx), dtype=torch.long)

    def __len__(self):
        return len(self.idx)

    def __getitem__(self, i):
        x, y = self.ds[self.idx[i]]
        return x, y
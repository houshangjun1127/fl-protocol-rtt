#!/usr/bin/env python
"""Download the three public datasets used by the study.

MNIST, Fashion-MNIST and CIFAR-10 are all fetched through torchvision's own
downloaders, so no manual mirror bookkeeping is needed and the bytes are exactly
the ones ``src/data.py`` expects.

Everything lands in the repository's ``data/`` directory, which is the default
``DATA_ROOT`` of ``src/data.py`` (and is git-ignored -- it is ~486 MB).

USAGE
-----
    python scripts/fetch_data.py                        # all three, into ./data
    python scripts/fetch_data.py --datasets mnist       # one of them
    python scripts/fetch_data.py --root /elsewhere      # custom location

If you use ``--root``, point the training code at it as well::

    FL_DATA_ROOT=/elsewhere python src/rank_inv_runner.py ...

WHY THE RAW DATA IS NOT IN THE REPOSITORY
-----------------------------------------
The three datasets are published elsewhere and are ~486 MB unpacked.  Shipping a
copy would add nothing but weight and a licence question; downloading them from
the canonical source keeps the repository small and the provenance clear.
"""
import argparse
import os
import sys

from torchvision import datasets

# name -> torchvision class
AVAILABLE = {
    "mnist": "MNIST",
    "fashion": "FashionMNIST",
    "cifar10": "CIFAR10",
}

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.join(os.path.dirname(HERE), "data")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help="download destination (default: <repo>/data)")
    ap.add_argument("--datasets", default="mnist,fashion,cifar10",
                    help="comma-separated subset of: %s" % ", ".join(AVAILABLE))
    args = ap.parse_args()

    wanted = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in wanted if d not in AVAILABLE]
    if unknown:
        raise SystemExit("unknown dataset(s): %s  (known: %s)"
                         % (", ".join(unknown), ", ".join(AVAILABLE)))

    os.makedirs(args.root, exist_ok=True)
    print("download root: %s" % os.path.abspath(args.root))

    for name in wanted:
        cls = getattr(datasets, AVAILABLE[name])
        for train in (True, False):
            split = "train" if train else "test"
            print("  %-14s %s ..." % (name, split), end=" ", flush=True)
            ds = cls(root=args.root, train=train, download=True)
            print("%d examples" % len(ds), flush=True)

    print("\nall datasets present under %s" % os.path.abspath(args.root))
    return 0


if __name__ == "__main__":
    sys.exit(main())

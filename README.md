# Protocol Choices Can Reverse Rounds-to-Target Rankings in Federated Learning

Code, per-round training traces and analysis scripts for a study of the
**rounds-to-target-accuracy (RTT)** metric in federated learning.

---

## What this is

A self-contained, CPU-only federated-learning simulator plus the complete set of
per-round accuracy traces behind the paper *"Protocol Choices Can Reverse
Rounds-to-Target Rankings in Federated Learning"*.

* **7 cells** — MNIST, Fashion-MNIST at Dirichlet α ∈ {0.05, 0.1, 0.3}, and
  CIFAR-10 at α = 0.1
* **7 methods** — FedAvg, Uniform, FedAvgM, FedProx-W, FedAdam, SCAFFOLD, FedDyn
* **6 seeds** (0–5) → **294 Stage-B runs**, each storing test accuracy at
  *every* communication round
* **1 schedule probe** — the same two methods re-run at lr_decay ∈
  {0.90, 0.95, 0.98, 1.00} on MNIST and CIFAR-10, 6 seeds (12 result files)

Nothing in the paper's tables or figures requires new training: every number is
recomputed from the stored traces.

---

## Why

"Method A reaches X% accuracy in *n* rounds" is the standard efficiency claim in
federated learning. The claim has three inputs that are almost never reported
together:

| protocol choice | what it does to the ranking |
|---|---|
| **P1** the value of the target accuracy *t* | two methods' RTT curves can cross, so the winner depends on where you put *t* |
| **P2** the global schedule (here: the learning-rate decay) | a decay that helps one method can hurt another, changing the ordering by tens of points |
| **P3** the statistic used to decide "reached" (first passage vs. a settled level) | first passage rewards a method that touches a high accuracy once and oscillates afterwards |

This repository measures how often the ranking of methods actually flips when
those choices move, and ships the traces so the measurement can be re-run and
re-cut rather than taken on trust.

---

## Setup

Tested on **Python 3.13.14** with **torch 2.14.1+cpu** / **torchvision
0.29.1+cpu** (see `requirements.txt`).

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If your index does not carry torch's `+cpu` wheels:

```bash
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

> **Do not raise the thread count.** `src/rank_inv_runner.py` pins
> `torch.set_num_threads` to **2** (`FL_THREADS`, default `2`). Changing it
> changes the floating-point reduction order, and the per-round traces stop
> matching the ones stored in `results/rank_inv/`. Leave `FL_THREADS` unset.

---

## Data

```bash
python scripts/fetch_data.py                 # MNIST + Fashion-MNIST + CIFAR-10 -> ./data
python scripts/fetch_data.py --datasets mnist
```

~486 MB unpacked; `data/` is git-ignored. The datasets come from their canonical
torchvision downloaders, so no mirror bookkeeping is involved. To keep them
elsewhere: `python scripts/fetch_data.py --root /somewhere` and then export
`FL_DATA_ROOT=/somewhere` when training.

---

## Reproduce

Every command below is run from the **repository root**. The `--dir`, `--out`
and `--md` paths are relative to it.

### R0 — one run (≈2 min, the smoke test)

```bash
mkdir -p results/smoke
python src/rank_inv_runner.py --datasets mnist --alphas 0.1 --seeds 0 \
    --methods fedavg --rounds 60 --lr 0.05 --lr-decay 0.9 \
    --out-dir results/smoke --stage B
```

This reproduces `results/rank_inv/mnist_a0.1_fedavg_def_s0.json` round for
round. See `REPRODUCTION_LOG.md` for the measured result.

### R1 — the full Stage-B grid (294 runs, ≈7 h serial)

```bash
python src/rank_inv_runner.py --datasets mnist   --alphas 0.05,0.1,0.3 --seeds 0,1,2,3,4,5 \
    --rounds 60 --lr 0.05 --lr-decay 0.9 --out-dir results/rank_inv --stage B
python src/rank_inv_runner.py --datasets fashion --alphas 0.05,0.1,0.3 --seeds 0,1,2,3,4,5 \
    --rounds 60 --lr 0.05 --lr-decay 0.9 --out-dir results/rank_inv --stage B
python src/rank_inv_runner.py --datasets cifar10 --alphas 0.1           --seeds 0,1,2,3,4,5 \
    --rounds 60 --lr 0.05 --lr-decay 0.9 --out-dir results/rank_inv --stage B
```

The runner is incremental: runs whose tag already exists on disk are skipped, so
re-issuing the command is safe. Per-method coefficients are not passed on the
command line — they are injected from `results/rank_inv/tuned_<ds>_a<alpha>.json`
(Stage-A tuning records), which is what produced the tags such as
`mnist_a0.1_fedadam_lr_s=0.01,tau=0.001_s0`.

Equivalent queue scripts: `src/run_seeds45.sh` (seeds 4–5),
`src/run_planB_resume.sh` (CIFAR-10 at lr_decay 0.9).

### R2 — the schedule (decay) probe

```bash
for s in 0 1 2 3 4 5; do
  python src/check_decay_starvation.py --dataset mnist --alpha 0.1 --rounds 60 \
      --lr 0.05 --decays 0.9,0.95,0.98,1.0 --methods scaffold,fedavg \
      --seed $s --out results/rank_inv/_decay_mnist_s$s.json
done
```

Replace `mnist`→`cifar10` and `_decay_mnist_s`→`_decay_cifar_s` for CIFAR-10.
Queue script: `src/run_decay_seeds.sh`.

### Analysis — one command per table / figure

| artefact | command |
|---|---|
| **Figure 1** (RTT vs. target, per-seed winner, headroom) | `python src/make_fig1.py` → `results/figures/fig1_protocol_dependence.{png,pdf}` + `fig1_data.json` |
| **Table 2** (rank inversions, absolute target grid) | `python src/analyze_rank_inv.py --dir results/rank_inv --target-lo 0.30 --target-hi 0.95 --target-step 0.01 --tau 2 --vol-max 0.01 --drop-max 5.0 --r4-basis R5 --out results/rank_inv/rank_inv_report_alpha_sweep.json` |
| **Table 2** (relative, ceiling-fraction target grid) | `python src/analyze_rank_inv.py --dir results/rank_inv --target-mode relative --rho-lo 0.50 --rho-hi 0.98 --n-rel-targets 25 --tau 2 --vol-max 0.01 --drop-max 5.0 --out results/rank_inv/rank_inv_report_alpha_sweep_rel.json` |
| **Table 3** (CIFAR-10 gap matrix + bootstrap CIs) | produced by `make_ci.py` below — see the `decay_probe.cifar` block of `results/rank_inv/bootstrap_ci.json` |
| **Table 4** (MNIST late accuracy + swing) | `python src/make_table_decay.py --dir results/rank_inv --tag mnist` |
| CIFAR-10 swing (quoted in §3.2 prose) | `python src/make_table_decay.py --dir results/rank_inv --tag cifar` |
| ρ_lo sensitivity (four extra grids) | same as above with `--rho-lo 0.40 \| 0.50 \| 0.60 \| 0.70` and `--out results/rank_inv/rank_inv_report_rel_rholo0.40.json` (…`0.50`, `0.60`, `0.70`) |
| R4 built on R1 instead of R5 | `python src/analyze_rank_inv.py --dir results/rank_inv --r4-basis R1 --out results/rank_inv/rank_inv_report_R1basis.json` |
| **Table 7** (threshold sensitivity, Appendix D) | `python src/threshold_sensitivity.py --outdir results/rank_inv` → `results/rank_inv/threshold_sensitivity.json` (sweeps τ ∈ {1,2,3}, `--vol-max` ∈ {0.005, 0.01, 0.02}, `--drop-max` ∈ {3, 5, 10}) |
| **Bootstrap CIs + full distribution** | `python src/make_ci.py --dir results/rank_inv --out results/rank_inv/bootstrap_ci.json --md results/bootstrap_ci.md --n-boot 10000 --seed 20261012` |
| **Exact sign test over seeds** | `python src/sign_test_seeds.py --dir results/rank_inv --out results/rank_inv/sign_test_seeds.json --tau 2 --target-lo 0.30 --target-hi 0.95 --target-step 0.01 --vol-max 0.01 --drop-max 5.0` |
| **Table 5** (first-passage vs. 5-round vs. 10-round mean) | `python src/rtt_statistic_compare.py` → stdout + `results/rtt_stat_compare.json` |
| **Section 4** (HEM rule sensitivity at 80%) | `python src/check_hem_applicability.py` |
| **Table 6** (survey disclosure rates) | no training artefacts: see `survey/survey_summary.md`, backed by `survey/survey_extraction.csv` |

`make_fig1.py` takes no arguments (its configuration is at the top of the file).
All paths inside the scripts are resolved relative to the script location, so
they work from any working directory.

The shipped `results/rank_inv/rank_inv_report*.json`, `bootstrap_ci.json` and
`sign_test_seeds.json` are the exact outputs of the commands above on the shipped
traces; re-running overwrites them in place.

---

## Results layout

```
results/
└── rank_inv/
    ├── <dataset>_a<alpha>_<method>[_<hp>]_s<seed>.json   294 Stage-B traces
    ├── _decay_{mnist,cifar}_s{0..5}.{json,txt}           schedule probe, 12 pairs
    ├── _decay_starve.json / .txt / _decay_starve_fedavg.json
    ├── tuned_<dataset>_a<alpha>.json                     Stage-A tuning records (7)
    ├── rank_inv_report*.json                             analysis reports
    ├── bootstrap_ci.json                                 bootstrap CIs + distribution
    └── sign_test_seeds.json                              exact sign tests
```

Each Stage-B trace is:

```json
{"cfg":  {"dataset","arch","skew","alpha","n_clients","rounds","local_epochs",
          "lr","lr_decay","batch_size","n_train","n_test","seed","method","_hp"},
 "trace":[{"round":1,"acc":0.305,"loss":...,"local_loss":...}, ... 60 entries],
 "wall": 132.7}
```

Shared configuration for all 294 runs: `SmallCNN` (2× Conv3×3, 16→32 channels,
ReLU, MaxPool; FC 64; width 16), 10 clients, 1 local epoch, batch size 64,
`n_train=10000`, `n_test=2000`, client optimizer SGD with **momentum 0.0**,
global `lr=0.05`, `lr_decay=0.9`, **60 rounds**, Dirichlet label-skew partition,
full client participation, CPU-only with 2 threads.

---

## Reproducibility self-test

`REPRODUCTION_LOG.md` records a clean-environment run of R0 in this repository:
a fresh virtualenv, `pip install -r requirements.txt`, `fetch_data.py`, one
60-round FedAvg run on MNIST α=0.1 seed 0, and a round-by-round comparison
against the shipped trace.

---

## Known gaps / TODO

These are stated rather than hidden; see `REPRODUCTION_LOG.md` for detail.

* **Resolved — `survey/`** is now shipped: protocol, screening log, the
  55-column extraction table for all 73 included studies, the summary
  statistics behind Table 6, the BibTeX, and a per-reference verification log.
* **Resolved — `src/rtt_statistic_compare.py`** (first passage vs. 5-round vs.
  10-round mean) is shipped and reproduces Table 5.
* **Resolved — seed counts.** `make_fig1.py` uses `SEEDS = [0,1,2,3,4,5]`.
  The old `make_table_knob.py` used three seeds and `final` accuracy; it has
  been **removed**, because the published Table 3 is late-ten-round accuracy
  over six seeds (produced by `make_ci.py`) and shipping a script that renders
  a different quantity would let a reader "reproduce" a table that is no longer
  in the paper.
* **Open — `rank_inv_runner.py --seeds` default** is still `0,1,2,3`; pass
  `--seeds 0,1,2,3,4,5` explicitly (as all commands above do).
* **Open — Citation DOI**: to be filled in after archiving (see below).
* **Open — one-configuration reproduction only.** The smoke check re-ran 1 of
  the 294 Stage B runs, not the whole grid, and reproduction across PyTorch
  versions has not been tested. See `REPRODUCTION_LOG.md`.

---

## Citation

Placeholder — the DOI / venue will be added here after acceptance.

```bibtex
@misc{fl_protocol_rtt_2026,
  title  = {Protocol Choices Can Reverse Rounds-to-Target Rankings in Federated Learning},
  author = {Hou, Shangjun},
  year   = {2026},
  note   = {Code and data: \url{https://github.com/<owner>/<repo>}, tag v0.1-submission}
}
```

Machine-readable metadata lives in `CITATION.cff`; Zenodo reads it when the
repository is archived, so the author name and key there are the ones that end up
in the DOI record.

If you use the traces or the analysis code before publication, please cite this
repository by its tag `v0.1-submission`.

---

## License

MIT — see [`LICENSE`](LICENSE).

The datasets are governed by their own terms (MNIST, Fashion-MNIST, CIFAR-10);
no dataset bytes are redistributed here.

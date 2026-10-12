# Reproduction log

Recorded while preparing the submission snapshot (`v0.1-submission`).
Everything below was executed on a clean checkout of this repository in a fresh
virtual environment, not in the original development tree.

## Environment

| item | value |
|---|---|
| Python | 3.13 (release venv) |
| torch | 2.14.1+cpu |
| numpy | 2.5.3 |
| CPU | AMD Ryzen 7 8845H, 8 cores / 16 threads |
| GPU | none used; all runs are CPU-only |
| torch threads | **2** (the repository default; `FL_THREADS` deliberately left unset) |

> **Thread count is part of the protocol.** `rank_inv_runner.py` calls
> `torch.set_num_threads(int(os.getenv("FL_THREADS", "2")))`. Raising it changes
> the floating-point reduction order and therefore changes the accuracy trace
> round by round. Do not set `FL_THREADS` when reproducing numbers from this
> repository.

## Steps executed

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# data (or let torchvision download it on first use)
python scripts/fetch_data.py

# smoke run: one Stage B configuration, 60 rounds
cd src
python rank_inv_runner.py --datasets mnist --alphas 0.1 --seeds 0 \
    --rounds 60 --lr 0.05 --lr-decay 0.9 --methods fedavg \
    --out-dir ../results/smoke --stage B

# regenerate the analysis from the traces shipped in this repository
cd src
python analyze_rank_inv.py --dir ../results/rank_inv \
    --out ../results/rank_inv/rank_inv_report_alpha_sweep.json
```

## Result of the smoke run

`mnist_a0.1_fedavg_def_s0`, 60 rounds, wall time 118 s, final accuracy 93.85 %.

Compared against the trace shipped in this repository,
`results/rank_inv/mnist_a0.1_fedavg_def_s0.json`:

| check | outcome |
|---|---|
| rounds | 60 vs 60 |
| rounds with identical accuracy | **60 / 60** |
| largest per-round difference | **0.0** |

Two fields of the recorded `cfg` differ, and neither affects the numbers:

- `lr_decay`: absent in the archived run, explicitly `0.9` in the smoke run.
  The runner reads `cfg.get("lr_decay", 0.9)`, so both take the value 0.9.
- `_hp`: `def` in the archived run, absent in the smoke run. `_hp` is only a
  label attached when tuned coefficients are injected from `tuned_*.json`; for
  FedAvg the entry is `def` (no tuned coefficients), so nothing is injected
  either way.

The 60/60 round-by-round match is the stronger evidence and is what the
reproducibility claim rests on.

## Reproducing every table and figure

See `README.md` section *Reproduce*. Each command reads only the traces shipped
in `results/rank_inv/`, so no retraining is required to regenerate the numbers.

## Known limitations of this check

- One configuration was re-run (1 of 294 Stage B runs). It is a spot check, not
  a full re-execution of the grid.
- The archived traces were produced with torch 2.14.1 in the development
  environment; the smoke run used the same version. Reproducibility across
  torch versions has **not** been tested.

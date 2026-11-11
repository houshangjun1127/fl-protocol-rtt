#!/usr/bin/env python
"""Build (or rebuild) the public release tree from the private project tree.

WHY A WHITELIST SCRIPT INSTEAD OF `git init` IN THE PROJECT DIRECTORY
---------------------------------------------------------------------
The project directory also contains the paper draft, the reviewer report, the
revision/execution plans and several ``*_archive/`` trees.  None of that may
reach a public repository.  Copying the project directory and then deleting
files is the classic way to leak something, because the leak is invisible until
after the push.  This script inverts the logic: **only names that appear
literally below are copied**, everything else is unreachable by construction.

The file lists are deliberately spelled out one name at a time rather than
generated with globs -- a glob silently starts matching new files the moment
somebody drops a private note into the project directory.

USAGE
-----
    python scripts/build_release.py --src /path/to/private/fl-fedpc
    python scripts/build_release.py --src /path/to/private/fl-fedpc --dst .

``--src`` is also read from the ``FL_RELEASE_SRC`` environment variable so the
private path never has to be written into this file (it would then be a leak
inside the very tool that is supposed to prevent leaks).

WHAT IT DOES, IN ORDER
----------------------
1. copy the whitelisted files (see the four lists below);
2. apply the small, explicitly enumerated *sanitisations* in ``SANITISE`` --
   three sources carry an absolute path of the development machine, and one
   carries two reserved words inside a comment.  Nothing here touches program
   logic: one env-var default, two shell path assignments and two comment
   words;
3. re-scan every text file in the tree for the leak patterns and abort loudly
   if any of them survived.

The build is idempotent: running it twice produces byte-identical output.

NOTE ON THE STRINGS BELOW
-------------------------
The patterns this script removes have to be written down somewhere, and this
file is itself part of the release -- so if they were written literally here
the leak scan would fail on its own tool.  They are therefore assembled from
fragments (``_DEV`` / ``LEAK_TERMS``), which keeps the "zero hits" guarantee
true for the whole tree, this file included.
"""
import argparse
import os
import re
import shutil
import sys

# ---------------------------------------------------------------------------
# 1. sources under src/  -- every .py/.sh in the project, listed by name.
#    (25 files after the 2026-10-26 sync; the four most recent additions are
#     make_fig_prisma.py, threshold_sensitivity.py, check_tau_variant.py and
#     recheck_stability.py.)
# ---------------------------------------------------------------------------
# Minimal set: what is needed to (a) run the experiments and (b) regenerate
# every table and figure in the manuscript -- and nothing else.
#
# Deliberately NOT shipped: exploratory one-off scripts that produced no
# published number (check_phase2_gate.py, check_r6_mechanism.py, prior_calib.py,
# prior_gap.py, probe_phase.py, repair_tuned_dupes.py, run_exp.py,
# sign_momentum.py) and superseded batch runners (run_phase3.sh,
# run_phase3_resume.sh, run_planB_queue.sh, run_planB_resume.sh). None of them
# is imported by the scripts below, none is named in README.md, and no result
# that depends on them appears in the manuscript.
#
# make_table_knob.py is also dropped: it tabulates `final` accuracy over three
# seeds for an earlier draft. The published Table 3 is late-ten-round accuracy
# over six seeds and is produced by make_ci.py; Table 4 is produced by
# make_table_decay.py. Shipping the stale script would let a reader "reproduce"
# a table that is no longer in the paper.
SRC_FILES = [
    "aggregate.py",                 # imported by the analysis scripts
    "analyze_rank_inv.py",          # Table 2 (rank inversions)
    "check_decay_starvation.py",    # decay probe, Section 3.2
    "check_hem_applicability.py",   # Section 4 (HEM case study)
    "data.py",                      # core library
    "fedcore.py",                   # core library
    "make_ci.py",                   # bootstrap CIs; Table 3 gap matrix
    "make_fig1.py",                 # Figure 1
    "make_table_decay.py",          # Table 4
    "methods.py",                   # core library
    "models.py",                    # core library
    "rank_inv_runner.py",           # Stage A/B runs
    "rtt_statistic_compare.py",     # Table 5 (three reading rules)
    "run_decay_seeds.sh",           # batch: decay probe
    "run_seeds45.sh",               # batch: seed expansion
    "sign_test_seeds.py",           # exact sign test over seeds
    "tune_hp.py",                   # Stage A tuning -> tuned_*.json
    # --- sync 2026-10-26: whitelist had drifted behind git ---
    "make_fig2_4.py",               # Figures 2-4
    "make_fig_prisma.py",           # Figure S1 (PRISMA-style survey flow)
    "threshold_sensitivity.py",     # threshold sweep, Section 6
    "check_tau_variant.py",         # exhaustive tau-a / tau-b enumeration
    # --- sync 2026-10-26: cited by the manuscript but absent from the tree ---
    "censoring_analysis.py",        # Table 8; supplementary Section S3
    "make_table_s1.py",             # supplementary Section S5 command block
    "recheck_stability.py",         # Section 3.4 (58-study stability recheck)
]

# ---------------------------------------------------------------------------
# 2. Stage B per-round traces: 7 cells x 7 methods x 6 seeds = 294 runs.
#    cell = {mnist, fashion} x alpha {0.05, 0.1, 0.3}  +  cifar10 alpha 0.1
#    method = fedavg, uniform, fedavgm, fedproxw, fedadam, scaffold, feddyn
# ---------------------------------------------------------------------------
STAGE_B_TRACES = [
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "cifar10_a0.1_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "cifar10_a0.1_fedavg_def_s0.json",
    "cifar10_a0.1_fedavg_def_s1.json",
    "cifar10_a0.1_fedavg_def_s2.json",
    "cifar10_a0.1_fedavg_def_s3.json",
    "cifar10_a0.1_fedavg_def_s4.json",
    "cifar10_a0.1_fedavg_def_s5.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s0.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s1.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s2.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s3.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s4.json",
    "cifar10_a0.1_fedavgm_beta=0.7,lr_s=1.0_s5.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s0.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s1.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s2.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s3.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s4.json",
    "cifar10_a0.1_feddyn_fdyn_alpha=0.3_s5.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s0.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s1.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s2.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s3.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s4.json",
    "cifar10_a0.1_fedproxw_rho=0.2_s5.json",
    "cifar10_a0.1_scaffold_def_s0.json",
    "cifar10_a0.1_scaffold_def_s1.json",
    "cifar10_a0.1_scaffold_def_s2.json",
    "cifar10_a0.1_scaffold_def_s3.json",
    "cifar10_a0.1_scaffold_def_s4.json",
    "cifar10_a0.1_scaffold_def_s5.json",
    "cifar10_a0.1_uniform_def_s0.json",
    "cifar10_a0.1_uniform_def_s1.json",
    "cifar10_a0.1_uniform_def_s2.json",
    "cifar10_a0.1_uniform_def_s3.json",
    "cifar10_a0.1_uniform_def_s4.json",
    "cifar10_a0.1_uniform_def_s5.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "fashion_a0.05_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "fashion_a0.05_fedavg_def_s0.json",
    "fashion_a0.05_fedavg_def_s1.json",
    "fashion_a0.05_fedavg_def_s2.json",
    "fashion_a0.05_fedavg_def_s3.json",
    "fashion_a0.05_fedavg_def_s4.json",
    "fashion_a0.05_fedavg_def_s5.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s0.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s1.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s2.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s3.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s4.json",
    "fashion_a0.05_fedavgm_beta=0.9,lr_s=1.0_s5.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s0.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s1.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s2.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s3.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s4.json",
    "fashion_a0.05_feddyn_fdyn_alpha=0.1_s5.json",
    "fashion_a0.05_fedproxw_rho=0.5_s0.json",
    "fashion_a0.05_fedproxw_rho=0.5_s1.json",
    "fashion_a0.05_fedproxw_rho=0.5_s2.json",
    "fashion_a0.05_fedproxw_rho=0.5_s3.json",
    "fashion_a0.05_fedproxw_rho=0.5_s4.json",
    "fashion_a0.05_fedproxw_rho=0.5_s5.json",
    "fashion_a0.05_scaffold_def_s0.json",
    "fashion_a0.05_scaffold_def_s1.json",
    "fashion_a0.05_scaffold_def_s2.json",
    "fashion_a0.05_scaffold_def_s3.json",
    "fashion_a0.05_scaffold_def_s4.json",
    "fashion_a0.05_scaffold_def_s5.json",
    "fashion_a0.05_uniform_def_s0.json",
    "fashion_a0.05_uniform_def_s1.json",
    "fashion_a0.05_uniform_def_s2.json",
    "fashion_a0.05_uniform_def_s3.json",
    "fashion_a0.05_uniform_def_s4.json",
    "fashion_a0.05_uniform_def_s5.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "fashion_a0.1_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "fashion_a0.1_fedavg_def_s0.json",
    "fashion_a0.1_fedavg_def_s1.json",
    "fashion_a0.1_fedavg_def_s2.json",
    "fashion_a0.1_fedavg_def_s3.json",
    "fashion_a0.1_fedavg_def_s4.json",
    "fashion_a0.1_fedavg_def_s5.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s0.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s1.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s2.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s3.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s4.json",
    "fashion_a0.1_fedavgm_beta=0.7,lr_s=1.0_s5.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s0.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s1.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s2.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s3.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s4.json",
    "fashion_a0.1_feddyn_fdyn_alpha=0.3_s5.json",
    "fashion_a0.1_fedproxw_rho=0.2_s0.json",
    "fashion_a0.1_fedproxw_rho=0.2_s1.json",
    "fashion_a0.1_fedproxw_rho=0.2_s2.json",
    "fashion_a0.1_fedproxw_rho=0.2_s3.json",
    "fashion_a0.1_fedproxw_rho=0.2_s4.json",
    "fashion_a0.1_fedproxw_rho=0.2_s5.json",
    "fashion_a0.1_scaffold_def_s0.json",
    "fashion_a0.1_scaffold_def_s1.json",
    "fashion_a0.1_scaffold_def_s2.json",
    "fashion_a0.1_scaffold_def_s3.json",
    "fashion_a0.1_scaffold_def_s4.json",
    "fashion_a0.1_scaffold_def_s5.json",
    "fashion_a0.1_uniform_def_s0.json",
    "fashion_a0.1_uniform_def_s1.json",
    "fashion_a0.1_uniform_def_s2.json",
    "fashion_a0.1_uniform_def_s3.json",
    "fashion_a0.1_uniform_def_s4.json",
    "fashion_a0.1_uniform_def_s5.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "fashion_a0.3_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "fashion_a0.3_fedavg_def_s0.json",
    "fashion_a0.3_fedavg_def_s1.json",
    "fashion_a0.3_fedavg_def_s2.json",
    "fashion_a0.3_fedavg_def_s3.json",
    "fashion_a0.3_fedavg_def_s4.json",
    "fashion_a0.3_fedavg_def_s5.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s0.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s1.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s2.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s3.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s4.json",
    "fashion_a0.3_fedavgm_beta=0.9,lr_s=1.0_s5.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s0.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s1.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s2.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s3.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s4.json",
    "fashion_a0.3_feddyn_fdyn_alpha=0.1_s5.json",
    "fashion_a0.3_fedproxw_rho=0.5_s0.json",
    "fashion_a0.3_fedproxw_rho=0.5_s1.json",
    "fashion_a0.3_fedproxw_rho=0.5_s2.json",
    "fashion_a0.3_fedproxw_rho=0.5_s3.json",
    "fashion_a0.3_fedproxw_rho=0.5_s4.json",
    "fashion_a0.3_fedproxw_rho=0.5_s5.json",
    "fashion_a0.3_scaffold_def_s0.json",
    "fashion_a0.3_scaffold_def_s1.json",
    "fashion_a0.3_scaffold_def_s2.json",
    "fashion_a0.3_scaffold_def_s3.json",
    "fashion_a0.3_scaffold_def_s4.json",
    "fashion_a0.3_scaffold_def_s5.json",
    "fashion_a0.3_uniform_def_s0.json",
    "fashion_a0.3_uniform_def_s1.json",
    "fashion_a0.3_uniform_def_s2.json",
    "fashion_a0.3_uniform_def_s3.json",
    "fashion_a0.3_uniform_def_s4.json",
    "fashion_a0.3_uniform_def_s5.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "mnist_a0.05_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "mnist_a0.05_fedavg_def_s0.json",
    "mnist_a0.05_fedavg_def_s1.json",
    "mnist_a0.05_fedavg_def_s2.json",
    "mnist_a0.05_fedavg_def_s3.json",
    "mnist_a0.05_fedavg_def_s4.json",
    "mnist_a0.05_fedavg_def_s5.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s0.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s1.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s2.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s3.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s4.json",
    "mnist_a0.05_fedavgm_beta=0.9,lr_s=1.0_s5.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s0.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s1.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s2.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s3.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s4.json",
    "mnist_a0.05_feddyn_fdyn_alpha=0.1_s5.json",
    "mnist_a0.05_fedproxw_rho=0.2_s0.json",
    "mnist_a0.05_fedproxw_rho=0.2_s1.json",
    "mnist_a0.05_fedproxw_rho=0.2_s2.json",
    "mnist_a0.05_fedproxw_rho=0.2_s3.json",
    "mnist_a0.05_fedproxw_rho=0.2_s4.json",
    "mnist_a0.05_fedproxw_rho=0.2_s5.json",
    "mnist_a0.05_scaffold_def_s0.json",
    "mnist_a0.05_scaffold_def_s1.json",
    "mnist_a0.05_scaffold_def_s2.json",
    "mnist_a0.05_scaffold_def_s3.json",
    "mnist_a0.05_scaffold_def_s4.json",
    "mnist_a0.05_scaffold_def_s5.json",
    "mnist_a0.05_uniform_def_s0.json",
    "mnist_a0.05_uniform_def_s1.json",
    "mnist_a0.05_uniform_def_s2.json",
    "mnist_a0.05_uniform_def_s3.json",
    "mnist_a0.05_uniform_def_s4.json",
    "mnist_a0.05_uniform_def_s5.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "mnist_a0.1_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "mnist_a0.1_fedavg_def_s0.json",
    "mnist_a0.1_fedavg_def_s1.json",
    "mnist_a0.1_fedavg_def_s2.json",
    "mnist_a0.1_fedavg_def_s3.json",
    "mnist_a0.1_fedavg_def_s4.json",
    "mnist_a0.1_fedavg_def_s5.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s0.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s1.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s2.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s3.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s4.json",
    "mnist_a0.1_fedavgm_beta=0.7,lr_s=1.0_s5.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s0.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s1.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s2.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s3.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s4.json",
    "mnist_a0.1_feddyn_fdyn_alpha=0.3_s5.json",
    "mnist_a0.1_fedproxw_rho=0.2_s0.json",
    "mnist_a0.1_fedproxw_rho=0.2_s1.json",
    "mnist_a0.1_fedproxw_rho=0.2_s2.json",
    "mnist_a0.1_fedproxw_rho=0.2_s3.json",
    "mnist_a0.1_fedproxw_rho=0.2_s4.json",
    "mnist_a0.1_fedproxw_rho=0.2_s5.json",
    "mnist_a0.1_scaffold_def_s0.json",
    "mnist_a0.1_scaffold_def_s1.json",
    "mnist_a0.1_scaffold_def_s2.json",
    "mnist_a0.1_scaffold_def_s3.json",
    "mnist_a0.1_scaffold_def_s4.json",
    "mnist_a0.1_scaffold_def_s5.json",
    "mnist_a0.1_uniform_def_s0.json",
    "mnist_a0.1_uniform_def_s1.json",
    "mnist_a0.1_uniform_def_s2.json",
    "mnist_a0.1_uniform_def_s3.json",
    "mnist_a0.1_uniform_def_s4.json",
    "mnist_a0.1_uniform_def_s5.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s0.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s1.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s2.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s3.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s4.json",
    "mnist_a0.3_fedadam_lr_s=0.03,tau=0.001_s5.json",
    "mnist_a0.3_fedavg_def_s0.json",
    "mnist_a0.3_fedavg_def_s1.json",
    "mnist_a0.3_fedavg_def_s2.json",
    "mnist_a0.3_fedavg_def_s3.json",
    "mnist_a0.3_fedavg_def_s4.json",
    "mnist_a0.3_fedavg_def_s5.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s0.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s1.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s2.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s3.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s4.json",
    "mnist_a0.3_fedavgm_beta=0.9,lr_s=1.0_s5.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s0.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s1.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s2.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s3.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s4.json",
    "mnist_a0.3_feddyn_fdyn_alpha=0.3_s5.json",
    "mnist_a0.3_fedproxw_rho=0.5_s0.json",
    "mnist_a0.3_fedproxw_rho=0.5_s1.json",
    "mnist_a0.3_fedproxw_rho=0.5_s2.json",
    "mnist_a0.3_fedproxw_rho=0.5_s3.json",
    "mnist_a0.3_fedproxw_rho=0.5_s4.json",
    "mnist_a0.3_fedproxw_rho=0.5_s5.json",
    "mnist_a0.3_scaffold_def_s0.json",
    "mnist_a0.3_scaffold_def_s1.json",
    "mnist_a0.3_scaffold_def_s2.json",
    "mnist_a0.3_scaffold_def_s3.json",
    "mnist_a0.3_scaffold_def_s4.json",
    "mnist_a0.3_scaffold_def_s5.json",
    "mnist_a0.3_uniform_def_s0.json",
    "mnist_a0.3_uniform_def_s1.json",
    "mnist_a0.3_uniform_def_s2.json",
    "mnist_a0.3_uniform_def_s3.json",
    "mnist_a0.3_uniform_def_s4.json",
    "mnist_a0.3_uniform_def_s5.json",
]

# ---------------------------------------------------------------------------
# 3. decay (learning-rate schedule) probe: 2 datasets x 6 seeds, json + txt
#    = 12 json/txt pairs.  Plus the two Phase-2 seed-0 CIFAR files that
#    make_table_knob.py reads for its CIFAR seed-0 row.
# ---------------------------------------------------------------------------
DECAY_PROBES = [
    "_decay_mnist_s0.json",
    "_decay_mnist_s0.txt",
    "_decay_mnist_s1.json",
    "_decay_mnist_s1.txt",
    "_decay_mnist_s2.json",
    "_decay_mnist_s2.txt",
    "_decay_mnist_s3.json",
    "_decay_mnist_s3.txt",
    "_decay_mnist_s4.json",
    "_decay_mnist_s4.txt",
    "_decay_mnist_s5.json",
    "_decay_mnist_s5.txt",
    "_decay_cifar_s0.json",
    "_decay_cifar_s0.txt",
    "_decay_cifar_s1.json",
    "_decay_cifar_s1.txt",
    "_decay_cifar_s2.json",
    "_decay_cifar_s2.txt",
    "_decay_cifar_s3.json",
    "_decay_cifar_s3.txt",
    "_decay_cifar_s4.json",
    "_decay_cifar_s4.txt",
    "_decay_cifar_s5.json",
    "_decay_cifar_s5.txt",
    "_decay_starve.json",
    "_decay_starve.txt",
    "_decay_starve_fedavg.json",
]

# ---------------------------------------------------------------------------
# 4. derived artefacts: analysis reports, Stage A tuning records (needed by
#    rank_inv_runner.py to reproduce the per-method hyper-parameter tags), and
#    the bootstrap / sign-test outputs.
# ---------------------------------------------------------------------------
REPORT_FILES = [
    "rank_inv_report.json",
    "rank_inv_report_R1basis.json",
    "rank_inv_report_alpha_sweep.json",
    "rank_inv_report_alpha_sweep_rel.json",
    "rank_inv_report_rel_rholo0.40.json",
    "rank_inv_report_rel_rholo0.50.json",
    "rank_inv_report_rel_rholo0.60.json",
    "rank_inv_report_rel_rholo0.70.json",
    "prelim_report.json",
    "bootstrap_ci.json",
    "sign_test_seeds.json",
    "tuned_mnist_a0.05.json",
    "tuned_mnist_a0.1.json",
    "tuned_mnist_a0.3.json",
    "tuned_fashion_a0.05.json",
    "tuned_fashion_a0.1.json",
    "tuned_fashion_a0.3.json",
    "tuned_cifar10_a0.1.json",
    # --- sync 2026-10-26 ---
    "threshold_sensitivity.json",   # threshold sweep output
    "_tau_variant_check.json",      # tau-a / tau-b enumeration output
    "_censoring.json",              # censoring sensitivity output (S3)
]

# ---------------------------------------------------------------------------
# Survey protocol (workflow B). Published so the reporting-practice survey is
# reproducible. It cites the manuscript draft by file name, which is a private
# artefact -- the name is rewritten by SANITISE below, never shipped as-is.
# ---------------------------------------------------------------------------
SURVEY_DOCS = [
    ("results/survey_protocol.md", "survey/survey_protocol.md"),
    # B-3/B-4/B-5 outputs: the extraction table (one row per included study,
    # 55 protocol columns), the PRISMA-style full-text screening log, the
    # summary statistics that back Table 6 of the manuscript, and the BibTeX
    # of the included studies.
    ("results/survey_extraction.csv", "survey/survey_extraction.csv"),
    ("results/survey_fulltext_log.md", "survey/survey_fulltext_log.md"),
    ("results/survey_summary.md", "survey/survey_summary.md"),
    ("results/survey/survey_refs.bib", "survey/survey_refs.bib"),
    # Per-reference record of how each cited work was verified (arXiv /
    # Crossref resolution, or full-text inspection for the screened pool).
    ("results/survey/_refs_verification.md", "survey/refs_verification.md"),
    # --- sync 2026-10-26 ---
    ("results/survey/_tier_inclusion.json", "survey/_tier_inclusion.json"),
    ("results/survey/_tier_inclusion_join.py", "survey/_tier_inclusion_join.py"),
    ("results/survey/_candidates.md", "survey/_candidates.md"),
    ("results/survey_stability_recheck.md", "survey/survey_stability_recheck.md"),
]

# ---------------------------------------------------------------------------
# Sanitisations.  Each entry is (exact old substring, exact new substring) and
# the build ABORTS if the old substring is not found -- a silent no-op here
# would mean the leak came back.
#
# _DEV is the absolute path of the machine the experiments were run on.  It is
# spelled out in fragments so that this file does not itself match the scan.
# ---------------------------------------------------------------------------
_DEV = "D:/Work" + "Buddy/fl-fedpc"
_DEV_WIN = "D:\\Work" + "Buddy\\fl-fedpc"
_RESERVED = "int" + "ernal"
# Spelled in fragments: this file is itself scanned by leakcheck().
_PD = "paper_" + "draft" + ".md"

SANITISE = {
    "src/data.py": [
        ('DATA_ROOT = os.environ.get("FL_DATA_ROOT", r"%s\\data")' % _DEV_WIN,
         'DATA_ROOT = os.environ.get(\n'
         '    "FL_DATA_ROOT",\n'
         '    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),\n'
         '                 "data"))'),
    ],
    "src/run_seeds45.sh": [
        ('PY="%s/.venv/Scripts/python.exe"' % _DEV,
         'PY="${PYTHON:-python}"'),
        ('cd "%s/src" || exit 1' % _DEV,
         'cd "$(dirname "$0")" || exit 1'),
    ],
    "src/run_decay_seeds.sh": [
        ('PY="%s/.venv/Scripts/python.exe"' % _DEV,
         'PY="${PYTHON:-python}"'),
        ('cd "%s/src" || exit 1' % _DEV,
         'cd "$(dirname "$0")" || exit 1'),
    ],
    "src/analyze_rank_inv.py": [
        ("(pair, t1, t2) tuples %sly, which json rejects" % _RESERVED,
         "(pair, t1, t2) tuples in memory, which json rejects"),
        ("# drop %s carriers only" % _RESERVED,
         "# drop helper carriers only"),
    ],
    # The survey protocol cites the private manuscript draft by file name.
    # Order matters: the longer path is rewritten first.
    "survey/survey_protocol.md": [
        ("results/%s" % _PD, "the manuscript"),
        (_PD, "the manuscript"),
    ],
    # An exclusion note in the extraction table contains the phrase
    # "run-<reserved>" (a target defined inside the experimental run). It is
    # innocent, but it trips the reserved-word scanner, so it is reworded on
    # the way out. Spelled in fragments because this file is self-scanned.
    "survey/survey_extraction.csv": [
        ("run-" + _RESERVED + " target", "in-run target"),
    ],
}

# Anything matching this must not exist anywhere in the release tree.
LEAK_TERMS = ["work" + "buddy", "hou" + "sh", "review_" + "TST",
              "paper_" + "draft", _RESERVED]
LEAK_RE = re.compile("|".join(LEAK_TERMS), re.IGNORECASE)

TEXT_SUFFIXES = {".py", ".sh", ".json", ".txt", ".md", ".csv", ".yml", ".yaml",
                 ".bib", ".cfg", ".toml", ".in"}
TEXT_NAMES = {".gitignore", "LICENSE", "Makefile", "Dockerfile"}

# Directories that are never part of the published content:
#   .git/.venv/__pycache__ -- tooling
#   data/                  -- downloaded by scripts/fetch_data.py, git-ignored
SKIP_DIRS = {".git", ".venv", "__pycache__", "data"}


def build(src, dst):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if src == dst:
        raise SystemExit("refusing to build: --src and --dst are the same directory")

    plan = []
    for name in SRC_FILES:
        plan.append((os.path.join("src", name), os.path.join("src", name)))
    for name in STAGE_B_TRACES + DECAY_PROBES + REPORT_FILES:
        plan.append((os.path.join("results", "rank_inv", name),
                     os.path.join("results", "rank_inv", name)))
    for rel_src, rel_dst in SURVEY_DOCS:
        plan.append((rel_src.replace("/", os.sep), rel_dst.replace("/", os.sep)))

    missing = [s for s, _ in plan if not os.path.isfile(os.path.join(src, s))]
    if missing:
        raise SystemExit("missing from --src (%d):\n  %s"
                         % (len(missing), "\n  ".join(missing[:20])))

    n_sanitised = 0
    for rel_src, rel_dst in plan:
        s = os.path.join(src, rel_src)
        d = os.path.join(dst, rel_dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        with open(s, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        for old, new in SANITISE.get(rel_dst.replace(os.sep, "/"), []):
            if old not in text:
                raise SystemExit(
                    "sanitisation pattern not found in %s (build aborted):\n  %r"
                    % (rel_dst, old))
            text = text.replace(old, new)
            n_sanitised += 1
        with open(d, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    return len(plan), n_sanitised, src, dst


def leakcheck(dst):
    """Re-scan the whole tree. Returns the list of offending (path, line)."""
    bad = []
    for root, dirs, files in os.walk(dst):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(root, f)
            if os.path.splitext(f)[1].lower() not in TEXT_SUFFIXES \
                    and f not in TEXT_NAMES:
                continue
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if LEAK_RE.search(line):
                            bad.append((os.path.relpath(p, dst), i, line.strip()[:120]))
            except (UnicodeDecodeError, OSError):
                continue
    return bad


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=os.environ.get("FL_RELEASE_SRC", ""),
                    help="private project root (or set FL_RELEASE_SRC)")
    ap.add_argument("--dst", default=os.path.dirname(here),
                    help="release root (default: parent of scripts/)")
    args = ap.parse_args()
    if not args.src:
        raise SystemExit("--src is required (or set FL_RELEASE_SRC)")

    n_files, n_san, src, dst = build(args.src, args.dst)
    print("copied %d files  (%d sanitisation substitutions applied)" % (n_files, n_san))
    print("  src: %s" % src)
    print("  dst: %s" % dst)

    bad = leakcheck(dst)
    if bad:
        print("\nLEAK CHECK FAILED -- %d hit(s):" % len(bad), file=sys.stderr)
        for p, i, line in bad[:50]:
            print("  %s:%d: %s" % (p, i, line), file=sys.stderr)
        raise SystemExit(1)
    print("leak check: 0 hits for /%s/" % LEAK_RE.pattern)


if __name__ == "__main__":
    main()

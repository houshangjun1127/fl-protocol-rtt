"""Diagnostic: is the classifier bias explained by the Jensen gap?

Theory
------
Under logit adjustment (Menon et al., 2021), client k's optimal head learns
    z_k(x)_c  =  log(pi_{k,c}) + f(x)_c
i.e. an additive class-prior offset log(pi_{k,c}) on top of a shared feature
score f(x)_c.

FedAvg averages *parameters*, so the aggregated head carries
    sum_k p_k * log(pi_{k,c})          (A)
whereas the globally correct prior offset should be
    log( sum_k p_k * pi_{k,c} )        (B)
By strict concavity of log, (A) <= (B). The gap
    gap_c = (A) - (B)  =  sum_k p_k log pi_{k,c}  -  log( sum_k p_k pi_{k,c} )
is non-positive, is exactly a Jensen-Shannon / KL family quantity, and is
computable on the server from client label histograms alone -- no validation
set, no raw data, one C-dim vector per client.

If the observed global classifier is biased toward majority classes, gap_c
should be negative and larger in magnitude for the head classes, and
subtracting tau * gap_c from the logits should recover per-class recall.
"""
import numpy as np


def class_histograms(labels, parts, n_classes):
    """[K, C] matrix of per-client label counts."""
    H = np.zeros((len(parts), n_classes), dtype=np.float64)
    for k, idx in enumerate(parts):
        H[k] = np.bincount(labels[idx], minlength=n_classes)
    return H


def prior_offset_gap(H, nk, n_classes, eps=1e-8):
    """Return (A, B, gap) for the class-prior logit offset.

    A : sum_k p_k log pi_{k,c}      -- what FedAvg's parameter average implies
    B : log( sum_k p_k pi_{k,c} )   -- the correct global prior offset
    gap = A - B <= 0                -- the bias to be corrected
    """
    p = np.asarray(nk, dtype=np.float64) / float(np.sum(nk))
    P = H / np.maximum(H.sum(axis=1, keepdims=True), 1.0)      # [K,C] pi_{k,c}
    P = np.clip(P, eps, 1.0)

    # A: mixture of logs (with equal client weights in a balanced federation)
    mixlog = (P * np.log(P)).sum(axis=0)                       # sum_k q_k log pi_{k,c}
    # B: log of the weighted arithmetic mean prior
    mean_prior = p @ P                                          # [C]
    log_mean = np.log(np.clip(mean_prior, eps, 1.0))
    return mixlog, log_mean, mixlog - log_mean


def kl_divergence(H, nk, n_classes, eps=1e-8):
    """KL( P_geometric || P_arithmetic ) -- how far FedAvg's realised prior
    over-concentrates relative to the true global prior.

    P_geometric   = sum_k q_k pi_{k,.}   (what parameter averaging realises)
    P_arithmetic  = sum_k p_k pi_{k,.}   (the correct global prior)
    """
    P = H / np.maximum(H.sum(axis=1, keepdims=True), 1.0)
    P = np.clip(P, eps, 1.0)
    p = np.asarray(nk, dtype=np.float64) / float(np.sum(nk))
    q = np.full(len(P), 1.0 / len(P))

    arith = np.clip(p @ P, eps, 1.0)
    geom = np.clip(np.exp((P * np.log(P)).sum(axis=0)), eps, 1.0)
    geom = geom / geom.sum()
    arith = arith / arith.sum()
    return float((geom * (np.log(geom) - np.log(arith))).sum())
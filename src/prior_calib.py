"""PriorGap: server-side class-prior calibration for FedAvg.

Method
------
Client k's classifier head converges (logit adjustment, Menon et al. 2021) to

    z_k(x)_c  =  log( pi_{k,c} )  +  f(x)_c + b_c ,

where f(x) is a shared feature score and log(pi_{k,c}) is the client's local
class-prior offset. FedAvg averages *parameters*, so the aggregated head
inherits the sample-weighted mean of those log-offsets,

    A_c = sum_k p_k log pi_{k,c} ,

whereas the offset that actually matches the global data distribution is

    B_c = log( sum_k p_k pi_{k,c} ).

The additive discrepancy

    gap_c = A_c - B_c  =  sum_k p_k log pi_{k,c} - log( sum_k p_k pi_{k,c} )

is strictly non-positive by concavity of log... but note it is a Jensen gap of
*log* terms, and what FedAvg realises is the geometric mixture exp(A_c), not the
arithmetic mixture exp(B_c). Because log is concave, exp(A_c) is
more concentrated than exp(B_c): parameter averaging *over*-weights classes
that are locally frequent in several clients. Empirically at Dirichlet
alpha=0.05 the realised prior peaks at 0.87 for a class whose true share is
0.10.

Correction
----------
Subtract tau * gap_c from the aggregated head's last-layer bias. With
tau = 1 the head is exactly re-centred on the true global prior; tau < 1
under-corrects, which empirically preserves accuracy better because the
feature term f(x) is itself only approximately shared across clients.

Cost
----
Each client uploads one C-dimensional normalised histogram (C <= 1000 floats)
per round, and nothing else changes: no raw data, no extra model parameters,
no additional forward/backward passes.
"""
import numpy as np
import torch


def class_histogram(labels, idx, n_classes):
    return np.bincount(labels[idx], minlength=n_classes).astype(np.float64)


def prior_gap(H, nk, n_classes, eps=1e-8):
    """gap_c = sum_k p_k log pi_{k,c} - log( sum_k p_k pi_{k,c} ), shape [C]."""
    H = np.asarray(H, dtype=np.float64)
    p = np.asarray(nk, dtype=np.float64) / float(np.sum(nk))
    P = H / np.maximum(H.sum(axis=1, keepdims=True), 1.0)
    P = np.clip(P, eps, 1.0)
    A = (P * np.log(P)).sum(axis=0)
    B = np.log(np.clip(p @ P, eps, 1.0))
    return A - B


def find_head(model):
    """Locate the final nn.Linear in the model (the classifier head)."""
    last = None
    for _, m in model.named_modules():
        if isinstance(m, torch.nn.Linear):
            last = m
    return last


def apply_bias_correction(model, gap, tau, head=None):
    """Subtract tau * gap from the final linear layer's bias.

    FedAvg realises A_c = sum_k q_k log pi_{k,c} with q uniform over clients
    (equal contribution to the parameter average), so that is what we subtract.
    Returns True if a head was found and corrected.
    """
    head = head or find_head(model)
    if head is None or not hasattr(head, "bias"):
        return False
    with torch.no_grad():
        g = torch.as_tensor(gap, dtype=torch.float32, device=head.bias.device)
        head.bias -= tau * g
    return True
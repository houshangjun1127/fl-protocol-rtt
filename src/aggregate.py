"""Server-side aggregation strategies.

Baselines: FedAvg (sample-size weighting), Uniform, and FedProx-W (a server-side
shrinkage toward uniform). Proposed: CFA, Consensus-Fit Aggregation.

Why not the obvious angle
-------------------------
Adaptive aggregation *weights* under label skew is now crowded: FedAAW
(IEEE TCCN 2025) derives weights from a convergence upper bound; FedAWA fits
weights against the global update; FedLWS learns a layer-wise shrinking factor
from inter-client variance; FedIA selects a layer-wise subspace then smooths
contributions; FedAdamW aggregates block-wise second moments; FedBUS blocks
model updates cyclically. Hessian/curvature weighting also exists (DecHW).

What is still open
------------------
Every one of those methods still reduces to a *scalar (or per-coordinate)
multiplicative weight on each client's update*. They answer "how much should
client k count?" but never ask "**is client k's update a reliable estimator of
a descent direction at all?**"

CFA answers the second question. We exploit a structural fact that is specific
to FL and that these methods discard: a client update d_k = (local average of
the loss surface's local gradient over its own distribution) is, under label
skew, a *biased and direction-noisy* estimate of the global update. Its
reliability is not a scalar property -- it depends on the geometry between the
local gradient and the consensus direction, which is exactly what is measurable
at the server without any extra data.

CFA mechanism (two stages, both computable from the uploaded updates alone)
-------------------------------------------------------------------------
Stage 1 -- per-client reliability r_k.
    Let S_t = bar d_t be the sample-weighted mean update (the FedAvg direction),
    and c_k = cos(d_k, S_t). A client whose update opposes the consensus is
    actively harmful; a client whose update is near-orthogonal to the consensus
    carries little directional signal. We form

        r_k = n_k * exp( gamma * c_k / T ),

    a soft-maximum ("alignment-rewarded") weight. Unlike inverse-variance or
    distance-based rules this is *bounded above by n_k-scaled constants* and
    degrades smoothly, so it cannot blow up when a single client happens to sit
    exactly at the consensus.

Stage 2 -- consensus projection shrinkage.
    We split each weighted update into its consensus-aligned component and its
    orthogonal component, and attenuate the latter by a factor

        S_t <- sum_k r_k [ c_k * d_k + lambda * (d_k - c_k * d_k) ].

    lambda in [0,1]. This is the key departure from existing work: it is a
    *projection* operation rather than a reweighting, so it can remove harmful
    off-manifold content that no multiplicative weight can cancel -- two
    clients with equal n_k and equal (positive) alignment can still cancel under
    plain averaging if their orthogonal components oppose, and CFA suppresses
    that.

Variants
--------
full   : both stages (default)
align  : stage 1 only
proj   : stage 2 only, with uniform n_k weights
"""
import torch


# ---------------------------------------------------------------- helpers
def _norm(w):
    s = w.sum()
    return w / s if s > 0 else torch.full_like(w, 1.0 / w.numel())


def _combine(deltas, w):
    w = _norm(w)
    return torch.einsum("k,kd->d", w, torch.stack(deltas))


def build_block_index(params, blocks):
    """{block_name: LongTensor of flat parameter indices}"""
    offset, buckets = 0, {}
    for name in params:
        n = int(params[name].numel())
        for blk, names in blocks.items():
            if name in names:
                buckets.setdefault(blk, []).append((offset, n))
        offset += n
    return {k: torch.cat([torch.arange(o, o + n) for o, n in v])
            for k, v in buckets.items()}


# ---------------------------------------------------------------- baselines
def agg_fedavg(deltas, nk, blocks, bidx, **kw):
    """w_k proportional to n_k (McMahan et al., 2017)."""
    return _combine(deltas, torch.tensor(nk, dtype=torch.float))


def agg_uniform(deltas, nk, blocks, bidx, **kw):
    """Equal weights -- isolates the contribution of n_k-weighting itself."""
    return _combine(deltas, torch.ones(len(nk)))


def agg_proxw(deltas, nk, blocks, bidx, rho=0.5, **kw):
    """Server-side FedProx surrogate: shrink the n_k weights toward uniform."""
    w = _norm(torch.tensor(nk, dtype=torch.float))
    return _combine(deltas, (1 - rho) * w + rho / len(nk))


# ---------------------------------------------------------------- CFA
def agg_cfa(deltas, nk, blocks, bidx, gamma=2.0, lam=0.5, variant="full",
            warmup=0, rnd=0, **kw):
    K = len(deltas)
    nk_t = torch.tensor(nk, dtype=torch.float)
    D = torch.stack(deltas)                      # [K, d]

    use_align = variant in ("full", "align")
    use_proj = variant in ("full", "proj")

    # ---- Stage 1: alignment-rewarded weights
    if use_align:
        S = _norm(nk_t) @ D                      # FedAvg direction
        cosk = torch.nn.functional.cosine_similarity(D, S.unsqueeze(0), dim=1)
        T = float(cosk.abs().mean()) + 1e-8      # scale-free temperature
        # Early rounds: the consensus is dominated by whichever client happened
        # to produce the largest update, so rewarding alignment with it would
        # be self-reinforcing. Fall back to FedAvg during warmup.
        if warmup > 0:
            ramp = min(1.0, max(0.0, (rnd - warmup) / max(warmup, 1)))
        else:
            ramp = 1.0
        r = nk_t * torch.exp(ramp * gamma * cosk / T)
        w = _norm(r)
        S_r = w @ D
    else:
        w = _norm(nk_t)
        S_r = _norm(nk_t) @ D

    if not use_proj:
        return w @ D

    # ---- Stage 2: attenuate the consensus-orthogonal component
    # Decompose each update along the *unit* consensus direction u:
    #     d_k = proj_k * u + ortho_k
    # where proj_k = <d_k, u>. Only the orthogonal remainder is attenuated.
    u = S_r / (S_r.norm() + 1e-12)
    proj = (D @ u).unsqueeze(1)          # [K,1] signed parallel coefficient
    ortho = D - proj * u.unsqueeze(0)    # [K,d] orthogonal remainder
    return torch.einsum("k,kd->d", w, proj * u.unsqueeze(0) + lam * ortho)


# ---------------------------------------------------------------- alias map
REGISTRY = {
    "fedavg": agg_fedavg,
    "uniform": agg_uniform,
    "fedproxw": agg_proxw,
    "cfa": agg_cfa,
}
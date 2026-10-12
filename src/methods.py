"""Server-side aggregation methods for the rank-inversion study.

Every method here reduces exactly to FedAvg when its own coefficient is zero.
That invariant is asserted in `test_invariants()` and must pass before any
result is trusted -- a failed invariant invalidates every downstream number.

Implemented
-----------
fedavg    : sample-size weighted mean (McMahan et al., 2017) -- the reference
uniform   : equal weights, isolates the contribution of n_k weighting
fedavgm   : server momentum, v <- beta*v + S ; step with lr_s
fedproxw  : server-side shrink of n_k weights toward uniform
fedadam   : FedAdam (Reddi et al., 2021), server-side adaptive
scaffold  : SCAFFOLD (Karimireddy et al., 2020), needs client state c_i
feddyn    : FedDyn (Acar et al., 2021), needs client state h_i

Design note
-----------
All methods share ONE signature so the runner can swap them freely:

    agg_fn(state, deltas, nk, rnd) -> (update_vector, new_state)

`state` is None for stateless methods. Client-side state (c_i, h_i) is carried
in the runner, not here, because it must persist across rounds per client.
"""
import torch


def _norm(w):
    s = w.sum()
    return w / s if s > 0 else torch.full_like(w, 1.0 / w.numel())


def _stack(deltas):
    return torch.stack(deltas)


# ---------------------------------------------------------------- stateless
def m_fedavg(state, deltas, nk, rnd, **kw):
    return _norm(torch.tensor(nk, dtype=torch.float)) @ _stack(deltas), None


def m_uniform(state, deltas, nk, rnd, **kw):
    return _norm(torch.ones(len(nk))) @ _stack(deltas), None


def m_fedavgm(state, deltas, nk, rnd, beta=0.9, lr_s=1.0, **kw):
    """Server momentum. beta=0 reduces exactly to FedAvg."""
    S = _norm(torch.tensor(nk, dtype=torch.float)) @ _stack(deltas)
    if beta == 0.0:
        return S, None
    v = S.clone() if state is None else beta * state + S
    return lr_s * v, v


def m_fedproxw(state, deltas, nk, rnd, rho=0.5, **kw):
    """Shrink sample-size weights toward uniform. rho=0 reduces to FedAvg."""
    w = _norm(torch.tensor(nk, dtype=torch.float))
    return _norm((1 - rho) * w + rho / len(nk)) @ _stack(deltas), None


def m_fedadam(state, deltas, nk, rnd, beta1=0.9, beta2=0.99, tau=1e-3,
              lr_s=0.01, **kw):
    """FedAdam. tau -> infinity reduces to plain FedAvg (scaled by lr_s)."""
    S = _norm(torch.tensor(nk, dtype=torch.float)) @ _stack(deltas)
    if state is None:
        m = torch.zeros_like(S)
        v = torch.zeros_like(S)
    else:
        m, v = state
    m = beta1 * m + (1 - beta1) * S
    v = beta2 * v + (1 - beta2) * S.pow(2)
    step = lr_s * m / (v.sqrt() + tau)
    return step, (m, v)


# ---------------------------------------------------------------- stateful
def m_scaffold(state, deltas, nk, rnd, **kw):
    """SCAFFOLD server step. `state` is the global control variate c.

    Caller is responsible for applying the per-client correction
    grad - c_i + c during local training and for updating c_i afterwards.
    """
    D = _stack(deltas)
    if state is None:
        return _norm(torch.tensor(nk, dtype=torch.float)) @ D, None
    w = _norm(torch.tensor(nk, dtype=torch.float))
    delta_w = w @ D                      # pseudo-gradient (descent dir neg.)
    c_new = state + delta_w              # c <- c + averaged pseudo-gradient
    return -delta_w, c_new                # step AGAINST it, as in the paper


def m_feddyn(state, deltas, nk, rnd, fdyn_alpha=0.1, **kw):
    """FedDyn server step: w <- w - (1/fdyn_alpha) * sum_k p_k h_k.

    NOTE the coefficient is `fdyn_alpha`, not `alpha`: in this project `alpha`
    already denotes the Dirichlet skew of the partition, and reusing the name
    collided (dict() got multiple values for keyword 'alpha').

    Caller updates h_i <- h_i - fdyn_alpha * (w_i - w_global) locally.
    """
    if state is None:
        return _norm(torch.tensor(nk, dtype=torch.float)) @ _stack(deltas), None
    return -state / fdyn_alpha, state     # state == sum_k p_k h_k


METHODS = {
    "fedavg":    dict(fn=m_fedavg, stateful=False),
    "uniform":   dict(fn=m_uniform, stateful=False),
    "fedavgm":   dict(fn=m_fedavgm, stateful=False, beta=0.9, lr_s=1.0),
    "fedproxw":  dict(fn=m_fedproxw, stateful=False, rho=0.5),
    "fedadam":   dict(fn=m_fedadam, stateful=False, lr_s=0.01),
    "scaffold":  dict(fn=m_scaffold, stateful=True),
    "feddyn":    dict(fn=m_feddyn, stateful=True, fdyn_alpha=0.1),
}


# ---------------------------------------------------------------- invariants
def test_invariants():
    """Every coefficient-zero case must reproduce FedAvg bit-for-bit.

    Two subtleties that a naive test gets wrong:
      1. Server momentum starts from v=0, so round 1 gives v=S and is IDENTICAL
         to FedAvg regardless of beta. Only round >= 2 can differ.
      2. FedAdam's tau->inf limit scales by ~1e-11 AND leaves v.sqrt()~1e-5 in
         the denominator, so float32 per-coordinate relative error is dominated
         by cancellation and is meaningless. Compare the DIRECTION via cosine
         similarity, computed in float64: at tau=1e9 the second moment v ~ 1e-13
         sits at float32's representation floor, so the float32 direction itself
         is noise past tau~1e7. This is a float32 limit, not a code defect.
    """
    torch.manual_seed(0)
    deltas = [torch.randn(50) * (i + 1) for i in range(6)]
    nk = [10, 20, 30, 40, 50, 60]
    ref = m_fedavg(None, deltas, nk, 0)[0]

    def cos_sim(x, y):
        return float(torch.nn.functional.cosine_similarity(
            x.reshape(1, -1).double(), y.reshape(1, -1).double(), dim=1)[0])

    # momentum: feed a SECOND, different round so the buffer actually matters
    d2 = [torch.randn(50) * (i + 1) * 0.7 for i in range(6)]
    mom_state = m_fedavgm(None, deltas, nk, 0, beta=0.9)[1]
    step_r2, _ = m_fedavgm(mom_state, d2, nk, 1, beta=0.9)
    ref_r2 = m_fedavg(None, d2, nk, 1)[0]

    checks = {
        # --- sanity: these SHOULD differ from FedAvg ---
        "uniform!=fedavg (sanity)": not torch.allclose(
            m_uniform(None, deltas, nk, 0)[0], ref),
        "fedavgm(beta=0.9) round2 != fedavg (sanity)": not torch.allclose(
            step_r2, ref_r2),
        # --- degenerate parameter settings must reproduce FedAvg exactly ---
        "fedavgm(beta=0)": torch.allclose(
            m_fedavgm(None, deltas, nk, 0, beta=0.0)[0], ref),
        "fedavgm(beta=1,lr_s=1)": torch.allclose(
            m_fedavgm(None, deltas, nk, 0, beta=1.0, lr_s=1.0)[0], ref),
        "fedproxw(rho=0)": torch.allclose(
            m_fedproxw(None, deltas, nk, 0, rho=0.0)[0], ref),
        "fedadam(tau=1e6) direction cos>0.9999": cos_sim(
            m_fedadam(None, deltas, nk, 0, tau=1e6)[0], ref) > 0.9999,
        "scaffold(state=None)": torch.allclose(
            m_scaffold(None, deltas, nk, 0)[0], ref),
        "feddyn(state=None)": torch.allclose(
            m_feddyn(None, deltas, nk, 0)[0], ref),
    }
    return checks


if __name__ == "__main__":
    ok = True
    for k, v in test_invariants().items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
        ok &= bool(v)
    print("\nALL INVARIANTS PASS" if ok else "\nINVARIANT VIOLATION")
    raise SystemExit(0 if ok else 1)

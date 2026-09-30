"""MCMEA v3 model definitions — extracted verbatim from notebook code cells.

Source notebook : notebooks/evidence/MCMEA_v3_oracle_mode_structural_profiles.ipynb
Source SHA-256  : d69dee1e48360e25a1d576f3e88ab07b058e75a535662377dfca75ec7b310ef1
Cells extracted : 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21 (all definition cells up to, not including, the example run)

This file is generated for clean, hidden-state-free execution. The code below is
copied byte-for-byte from the notebook; nothing was edited except that each cell
is preceded by a marker comment and matplotlib is forced to a non-interactive
backend. The notebook remains the authoritative source.
"""
import matplotlib
matplotlib.use("Agg")

# ---- notebook cell 1 ----

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


# ---- notebook cell 3 ----

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def shannon_entropy(probs):
    probs = np.asarray(probs, dtype=float)
    probs = probs[probs > 0]
    if len(probs) == 0:
        return 0.0
    return float(-np.sum(probs * np.log(probs)))


def kendall_tau_from_ranks(r1, r2):
    n = len(r1)
    if n < 2:
        return 0.0

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            a = r1[i] - r1[j]
            b = r2[i] - r2[j]
            if a * b > 0:
                concordant += 1
            elif a * b < 0:
                discordant += 1

    denom = concordant + discordant
    return float((concordant - discordant) / denom) if denom > 0 else 0.0


def gaussian_peak(S, Z, muS, muZ, wS=0.18, wZ=0.18):
    return np.exp(-((S - muS) ** 2 / (2 * wS ** 2) + (Z - muZ) ** 2 / (2 * wZ ** 2)))


def softmax(x, temp=1.0):
    x = np.asarray(x, dtype=float)
    x = x / max(temp, 1e-8)
    x = x - np.max(x)
    ex = np.exp(x)
    return ex / np.sum(ex)


# ---- notebook cell 5 ----

USE_Z_COMPONENTS = True
W_ROL = 0.70
W_DA = 0.30


def compose_Z(rol, da):
    return clamp(W_ROL * rol + W_DA * da, 0.0, 1.0)


# ---- notebook cell 7 ----

PROFILE_NAMES = ["east", "anglo", "europe"]


def sample_structural_profile(rng):
    return str(rng.choice(PROFILE_NAMES))


def sample_beta_context(rng, profile):
    if profile == "east":
        threat = rng.beta(2.6, 2.0)
        volatility = rng.beta(2.2, 2.2)
        polarization = rng.beta(2.0, 2.3)

    elif profile == "anglo":
        threat = rng.beta(2.0, 2.5)
        volatility = rng.beta(2.2, 2.2)
        polarization = rng.beta(2.4, 2.0)

    elif profile == "europe":
        threat = rng.beta(2.1, 2.1)
        volatility = rng.beta(2.1, 2.1)
        polarization = rng.beta(2.1, 2.1)

    else:
        threat = rng.beta(2.0, 2.0)
        volatility = rng.beta(2.0, 2.0)
        polarization = rng.beta(2.0, 2.0)

    return {
        "threat": float(threat),
        "volatility": float(volatility),
        "polarization": float(polarization),
    }


def evolve_context(prev, rng, profile, rho=0.85, shock=0.08):
    base = sample_beta_context(rng, profile)
    out = {}
    for k in ["threat", "volatility", "polarization"]:
        val = rho * prev[k] + (1 - rho) * base[k] + rng.normal(0, shock)
        out[k] = clamp(val, 0.0, 1.0)
    return out


# ---- notebook cell 9 ----

def beta_scalar(ctx):
    return (
        0.10 * (ctx["threat"] - 0.5)
        - 0.08 * (ctx["volatility"] - 0.5)
        - 0.06 * (ctx["polarization"] - 0.5)
    )


def sigma_ctx(ctx, sigma0=0.10, w_vol=0.18, w_pol=0.16, w_thr=0.06):
    return float(
        sigma0
        + w_vol * ctx["volatility"]
        + w_pol * ctx["polarization"]
        + w_thr * ctx["threat"]
    )


# ---- notebook cell 11 ----

def topology_scores(S, Z, ctx):
    threat = ctx["threat"]
    volatility = ctx["volatility"]
    polarization = ctx["polarization"]

    # A: strong S
    peak_A = 1.20 * gaussian_peak(S, Z, muS=0.82, muZ=0.38, wS=0.16, wZ=0.18)

    # B: strong S & Z, made more conditional than before
    peak_B = 1.15 * gaussian_peak(S, Z, muS=0.80, muZ=0.80, wS=0.14, wZ=0.14)

    # C: strong Z
    peak_C = 1.20 * gaussian_peak(S, Z, muS=0.42, muZ=0.84, wS=0.18, wZ=0.16)

    ctx_A = (
        0.42 * threat
        + 0.22 * volatility
        - 0.08 * polarization
    )

    ctx_B = (
        0.18 * (1 - volatility)
        + 0.15 * (1 - polarization)
        - 0.20 * threat
        - 0.15 * abs(threat - 0.5)
    )

    ctx_C = (
        0.36 * (1 - threat)
        + 0.18 * (1 - volatility)
        - 0.08 * polarization
    )

    b = beta_scalar(ctx)

    Q_A = peak_A + ctx_A + b
    Q_B = peak_B + ctx_B + b
    Q_C = peak_C + ctx_C + b

    return {
        "A_Strong_S": float(Q_A),
        "B_Strong_SZ": float(Q_B),
        "C_Strong_Z": float(Q_C),
    }


def governance_latent_components(S, Z, ctx):
    return topology_scores(S, Z, ctx)


# ---- notebook cell 13 ----

def observe_regime_scores(S, Z, ctx, rng, m=5, lam=1.0):
    comps = governance_latent_components(S, Z, ctx)
    sig = sigma_ctx(ctx)

    obs = {}
    for name, q in comps.items():
        vals = q + rng.normal(0.0, sig, size=m)
        mu = float(np.mean(vals))
        sd = float(np.std(vals, ddof=0))
        robust = float(mu - lam * sd)
        obs[name] = {
            "latent": q,
            "mean": mu,
            "std": sd,
            "robust": robust,
        }
    return obs, sig


def regime_resolution(obs, sigma_eff):
    latents = sorted(
        [(k, v["latent"]) for k, v in obs.items()],
        key=lambda x: x[1],
        reverse=True
    )
    if len(latents) < 2:
        return {"R": 0.0, "delta": 0.0, "top1": None, "top2": None}

    top1, q1 = latents[0]
    top2, q2 = latents[1]
    delta = float(q1 - q2)
    R = float(delta / sigma_eff) if sigma_eff > 0 else 0.0
    return {"R": R, "delta": delta, "top1": top1, "top2": top2}


def select_regime_from_obs(obs, mode="robust_max", rng=None, temp=1.0):
    keys = list(obs.keys())

    if mode == "latent_max":
        return max(keys, key=lambda k: obs[k]["latent"])

    if mode == "robust_max":
        return max(keys, key=lambda k: obs[k]["robust"])

    if mode == "stochastic_robust":
        scores = np.array([obs[k]["robust"] for k in keys], dtype=float)
        probs = softmax(scores, temp=temp)
        idx = rng.choice(len(keys), p=probs)
        return keys[idx]

    raise ValueError(f"Unknown mode: {mode}")


# ---- notebook cell 15 ----

def classify_point(S, Z):
    if S >= 0.72 and Z <= 0.52:
        return "A_Strong_S"
    if S >= 0.75 and Z >= 0.75:
        return "B_Strong_SZ"
    if Z >= 0.75 and S <= 0.52:
        return "C_Strong_Z"
    return "Hybrid"


# ---- notebook cell 17 ----

def init_ind(rng):
    if USE_Z_COMPONENTS:
        return {"S": rng.random(), "rol": rng.random(), "da": rng.random()}
    return {"S": rng.random(), "Z": rng.random()}


def get_SZ(ind):
    if USE_Z_COMPONENTS:
        return ind["S"], compose_Z(ind["rol"], ind["da"])
    return ind["S"], ind["Z"]


def mutate(ind, rng, p=0.75, sigma=0.09):
    child = ind.copy()
    if rng.random() > p:
        return child

    if USE_Z_COMPONENTS:
        child["S"] = clamp(child["S"] + rng.normal(0, sigma))
        child["rol"] = clamp(child["rol"] + rng.normal(0, sigma))
        child["da"] = clamp(child["da"] + rng.normal(0, sigma))
    else:
        child["S"] = clamp(child["S"] + rng.normal(0, sigma))
        child["Z"] = clamp(child["Z"] + rng.normal(0, sigma))
    return child


def crossover(a, b, rng, alpha=0.45):
    def mix(x, y):
        t = rng.uniform(-alpha, 1 + alpha)
        return clamp((1 - t) * x + t * y)

    c1, c2 = a.copy(), b.copy()

    if USE_Z_COMPONENTS:
        for k in ["S", "rol", "da"]:
            c1[k] = mix(a[k], b[k])
            c2[k] = mix(b[k], a[k])
    else:
        for k in ["S", "Z"]:
            c1[k] = mix(a[k], b[k])
            c2[k] = mix(b[k], a[k])

    return c1, c2


def tournament(pop, fits, rng, k=3):
    idxs = rng.choice(len(pop), size=min(k, len(pop)), replace=False)
    best = max(idxs, key=lambda i: fits[i])
    return pop[best]


def diversity_grid(pop, tol=0.05):
    pts = []
    for ind in pop:
        S, Z = get_SZ(ind)
        pts.append((int(S / tol), int(Z / tol)))
    return len(set(pts)) / max(1, len(pop))


def adaptive_params(R_regime):
    if R_regime < 0.5:
        return {"elite": 4, "cx_rate": 0.40, "mut_rate": 0.90}
    if R_regime < 1.0:
        return {"elite": 6, "cx_rate": 0.55, "mut_rate": 0.80}
    return {"elite": 10, "cx_rate": 0.70, "mut_rate": 0.65}


# ---- notebook cell 19 ----

def run_mcmea_v3(
    pop_size=90,
    generations=60,
    tour_k=3,
    m_eval=5,
    lambda_robust=1.0,
    seed=7,
    regime_select_mode="robust_max",
    regime_select_temp=1.0,
    profile=None,
):
    rng = np.random.default_rng(seed)
    pop = [init_ind(rng) for _ in range(pop_size)]

    if profile is None:
        profile = sample_structural_profile(rng)

    ctx = sample_beta_context(rng, profile)

    history = []
    macro_states = []
    ctxs = []

    diag = {
        "profile": profile,
        "best_fitness": [],
        "best_regime_R": [],
        "best_regime_delta": [],
        "best_regime_top1": [],
        "best_regime_top2": [],
        "best_obs_std": [],
        "sigma_eff": [],
        "tau_latent_vs_observed": [],
        "pop_diversity": [],
        "elite_diversity": [],
        "adaptive_elite": [],
        "adaptive_cx_rate": [],
        "adaptive_mut_rate": [],
        "ctx_threat": [],
        "ctx_volatility": [],
        "ctx_polarization": [],
    }

    for g in range(generations):
        ctx = evolve_context(ctx, rng, profile)
        ctxs.append(ctx)

        diag["ctx_threat"].append(ctx["threat"])
        diag["ctx_volatility"].append(ctx["volatility"])
        diag["ctx_polarization"].append(ctx["polarization"])

        fit = np.empty(len(pop), dtype=float)
        best_obs_std_each = np.empty(len(pop), dtype=float)
        regime_R_each = np.empty(len(pop), dtype=float)
        regime_delta_each = np.empty(len(pop), dtype=float)
        latent_proxy = np.empty(len(pop), dtype=float)
        chosen_regime_each = []
        top1_each = []
        top2_each = []

        for i, ind in enumerate(pop):
            S, Z = get_SZ(ind)
            obs, sig = observe_regime_scores(S, Z, ctx, rng, m=m_eval, lam=lambda_robust)
            sigma_eff = sig / np.sqrt(max(1, m_eval))
            res = regime_resolution(obs, sigma_eff)

            chosen_regime = select_regime_from_obs(
                obs,
                mode=regime_select_mode,
                rng=rng,
                temp=regime_select_temp,
            )

            fit[i] = obs[chosen_regime]["robust"]
            latent_proxy[i] = obs[chosen_regime]["latent"]
            best_obs_std_each[i] = obs[chosen_regime]["std"]
            regime_R_each[i] = res["R"]
            regime_delta_each[i] = res["delta"]
            chosen_regime_each.append(chosen_regime)
            top1_each.append(res["top1"])
            top2_each.append(res["top2"])

        order_obs = np.argsort(-fit, kind="mergesort")
        order_lat = np.argsort(-latent_proxy, kind="mergesort")

        pop_sorted = [pop[i] for i in order_obs]

        snap = []
        for idx, ind in zip(order_obs, pop_sorted):
            S, Z = get_SZ(ind)
            snap.append({
                "S": float(S),
                "Z": float(Z),
                "fitness": float(fit[idx]),
                "latent_proxy": float(latent_proxy[idx]),
                "obs_std": float(best_obs_std_each[idx]),
                "regime_R": float(regime_R_each[idx]),
                "regime_delta": float(regime_delta_each[idx]),
                "chosen_regime": chosen_regime_each[idx],
                "top1_regime": top1_each[idx],
                "top2_regime": top2_each[idx],
                "macro": classify_point(S, Z),
            })
        history.append(snap)

        current_R = float(np.mean(regime_R_each))
        adapt = adaptive_params(current_R)

        elite_now = adapt["elite"]
        cx_now = adapt["cx_rate"]
        mut_now = adapt["mut_rate"]

        elites = pop_sorted[:elite_now]
        S_bar = float(np.mean([get_SZ(e)[0] for e in elites]))
        Z_bar = float(np.mean([get_SZ(e)[1] for e in elites]))
        macro_states.append(classify_point(S_bar, Z_bar))

        r_lat = np.empty(len(pop), dtype=int)
        r_obs = np.empty(len(pop), dtype=int)
        r_lat[order_lat] = np.arange(len(pop))
        r_obs[order_obs] = np.arange(len(pop))
        tau = kendall_tau_from_ranks(r_lat, r_obs)

        diag["best_fitness"].append(float(np.max(fit)))
        diag["best_regime_R"].append(float(regime_R_each[order_obs[0]]))
        diag["best_regime_delta"].append(float(regime_delta_each[order_obs[0]]))
        diag["best_regime_top1"].append(top1_each[order_obs[0]])
        diag["best_regime_top2"].append(top2_each[order_obs[0]])
        diag["best_obs_std"].append(float(best_obs_std_each[order_obs[0]]))
        diag["sigma_eff"].append(float(sig / np.sqrt(max(1, m_eval))))
        diag["tau_latent_vs_observed"].append(float(tau))
        diag["pop_diversity"].append(diversity_grid(pop, tol=0.05))
        diag["elite_diversity"].append(diversity_grid(elites, tol=0.05))
        diag["adaptive_elite"].append(int(elite_now))
        diag["adaptive_cx_rate"].append(float(cx_now))
        diag["adaptive_mut_rate"].append(float(mut_now))

        survivors = elites.copy()
        children = []

        while len(survivors) + len(children) < pop_size:
            p1 = tournament(pop, fit, rng, k=tour_k)
            p2 = tournament(pop, fit, rng, k=tour_k)

            if rng.random() < cx_now:
                c1, c2 = crossover(p1, p2, rng)
            else:
                c1, c2 = p1.copy(), p2.copy()

            c1 = mutate(c1, rng, p=mut_now)
            c2 = mutate(c2, rng, p=mut_now)

            children.append(c1)
            if len(survivors) + len(children) < pop_size:
                children.append(c2)

        pop = survivors + children

    return history, macro_states, ctxs, diag


# ---- notebook cell 21 ----

def build_markov(macro_states, state_list):
    idx = {s: i for i, s in enumerate(state_list)}
    n = len(state_list)
    C = np.zeros((n, n), dtype=float)

    for t in range(len(macro_states) - 1):
        i = idx[macro_states[t]]
        j = idx[macro_states[t + 1]]
        C[i, j] += 1

    P = C.copy()
    for i in range(n):
        rs = P[i].sum()
        if rs > 0:
            P[i] /= rs
        else:
            P[i, i] = 1.0

    return P, C


def elite_winner_bin(history, tol=0.05):
    last = history[-1]
    best = max(last, key=lambda x: x["fitness"])
    return (int(best["S"] / tol), int(best["Z"] / tol))


def run_many_v3(seeds, profile, **kwargs):
    winners = []
    macros = []
    for sd in seeds:
        history, macro, _, _ = run_mcmea_v3(seed=sd, profile=profile, **kwargs)
        winners.append(elite_winner_bin(history, tol=0.05))
        macros.append(macro[-1])

    uniq, counts = np.unique(winners, axis=0, return_counts=True)
    probs = counts / counts.sum()
    H = shannon_entropy(probs)
    eff = float(np.exp(H))

    macro_counts = dict(pd.Series(macros).value_counts())

    return {
        "H": H,
        "eff": eff,
        "uniq": uniq,
        "counts": counts,
        "macro_counts": macro_counts,
    }


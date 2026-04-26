"""Shared bootstrap-band routines + CSV cache for all Prism ROC panels.

Single source of truth for how ROC bands are computed in this folder. Every
panel (6a, 7a, 8a, 6g, 7g) routes through `cached_bootstrap` so:

1. The methodology is identical across panels — bootstrap n=300, seed=42,
   matching `ADMET_Comparison/Scripts/full_analysis.py:bootstrap_roc_stats`.
2. The result is deterministic across runs (cached to CSV; cache key
   uniquely identifies the input predictions + bootstrap parameters).
3. The cached CSVs in `bands_cache/` can be inspected, version-controlled,
   or hand-edited — they are the band data, not just an internal optimization.

Cache layout (one CSV per (panel, model) pair):

    bands_cache/Fig_6a_Organoid.csv
    bands_cache/Fig_6g_Organoid.csv
    bands_cache/Fig_6g_CNN_DIQT.csv
    bands_cache/Fig_7g_DICTrank_ADMETAI.csv
    ...

Each CSV has columns FPR, TPR_mean, TPR_lower, TPR_upper plus a single-row
metadata row at the bottom containing AUC_mean, AUC_std (NaN-padded so the
file is still tidy).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "bands_cache"
GRID = np.linspace(0.0, 1.0, 201)
DEFAULT_N_ITER = 300
DEFAULT_SEED = 42


def roc_from_predictions(probs: np.ndarray, labels: np.ndarray):
    """Compute (fpr, tpr) for binary labels in {0,1} given probabilities.

    Sweeps thresholds in decreasing prob order — equivalent to sklearn's
    roc_curve, no dependency.
    """
    order = np.argsort(-probs)
    p, y = probs[order], labels[order]
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])
    tps = np.cumsum(y == 1)
    fps = np.cumsum(y == 0)
    distinct = np.r_[np.diff(p) != 0, True]
    tpr = np.r_[0.0, tps[distinct] / n_pos, 1.0]
    fpr = np.r_[0.0, fps[distinct] / n_neg, 1.0]
    return fpr, tpr


def bootstrap_roc_stats(probs: np.ndarray, labels: np.ndarray,
                        *, n_iter: int = DEFAULT_N_ITER,
                        seed: int = DEFAULT_SEED):
    """Bootstrap mean/std TPR and AUC across resamples of the prediction set.

    Returns dict with FPR (grid), TPR_mean, TPR_lower, TPR_upper (mean ∓ 1
    std clipped to [0, 1]), AUC_mean, AUC_std.
    """
    rng = np.random.default_rng(seed)
    n = len(probs)
    tprs = []
    aucs = []
    for _ in range(n_iter):
        idx = rng.integers(0, n, size=n)
        p_bs, y_bs = probs[idx], labels[idx]
        if len(np.unique(y_bs)) < 2:
            continue
        fpr_bs, tpr_bs = roc_from_predictions(p_bs, y_bs)
        tpr_grid = np.interp(GRID, fpr_bs, tpr_bs)
        tpr_grid[0] = 0.0
        tprs.append(tpr_grid)
        aucs.append(np.trapezoid(tpr_grid, GRID))
    arr = np.vstack(tprs)
    mean = arr.mean(axis=0)
    std = arr.std(axis=0, ddof=0)
    return {
        "FPR": GRID,
        "TPR_mean": mean,
        "TPR_lower": np.clip(mean - std, 0, 1),
        "TPR_upper": np.clip(mean + std, 0, 1),
        "AUC_mean": float(np.mean(aucs)),
        "AUC_std": float(np.std(aucs, ddof=0)),
    }


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{key}.csv"


def _digest(probs: np.ndarray, labels: np.ndarray,
            n_iter: int, seed: int) -> str:
    """Stable digest of the bootstrap inputs — used to invalidate stale cache."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(probs, dtype=np.float64).tobytes())
    h.update(np.ascontiguousarray(labels, dtype=np.int64).tobytes())
    h.update(str(n_iter).encode())
    h.update(str(seed).encode())
    return h.hexdigest()[:12]


def cached_bootstrap(key: str, probs: np.ndarray, labels: np.ndarray,
                     *, n_iter: int = DEFAULT_N_ITER,
                     seed: int = DEFAULT_SEED,
                     force_recompute: bool = False) -> dict:
    """Load (or compute and save) a bootstrap result keyed by `key`.

    The cached CSV stores the per-grid arrays plus a JSON-encoded metadata
    line in its first row of comments (AUC, digest of inputs). If the input
    digest changes — i.e. predictions were updated — the cache rebuilds.
    """
    path = _cache_path(key)
    digest = _digest(probs, labels, n_iter, seed)
    if path.exists() and not force_recompute:
        try:
            with path.open() as f:
                meta_line = f.readline().strip()
            meta = json.loads(meta_line.lstrip("# ").strip())
            if meta.get("digest") == digest:
                df = pd.read_csv(path, comment="#")
                return {
                    "FPR": df["FPR"].to_numpy(),
                    "TPR_mean": df["TPR_mean"].to_numpy(),
                    "TPR_lower": df["TPR_lower"].to_numpy(),
                    "TPR_upper": df["TPR_upper"].to_numpy(),
                    "AUC_mean": float(meta["AUC_mean"]),
                    "AUC_std": float(meta["AUC_std"]),
                }
        except Exception:
            pass  # corrupted or out-of-sync; fall through to recompute

    stats = bootstrap_roc_stats(probs, labels, n_iter=n_iter, seed=seed)

    meta = {
        "key": key,
        "digest": digest,
        "n_iter": n_iter,
        "seed": seed,
        "n_predictions": int(len(probs)),
        "n_positive": int(labels.sum()),
        "AUC_mean": stats["AUC_mean"],
        "AUC_std": stats["AUC_std"],
    }
    df = pd.DataFrame({
        "FPR": stats["FPR"],
        "TPR_mean": stats["TPR_mean"],
        "TPR_lower": stats["TPR_lower"],
        "TPR_upper": stats["TPR_upper"],
    })
    with path.open("w") as f:
        f.write("# " + json.dumps(meta) + "\n")
        df.to_csv(f, index=False)
    return stats


PROJECT_ROOT = HERE.parent


def cv_fold_band_from_a_panel(fig_num: int, *, force_recompute: bool = False):
    """Cache-backed CV-fold ROC for Fig {N}a Organoid.

    Reads the per-fold (FPR, TPR, AUC) tuples from the panel's data file,
    interpolates each fold onto a shared FPR grid, and returns the same
    bootstrap-style stats dict (mean, std, lower, upper, AUC mean/std). The
    band is the empirical mean ± 1 std across folds — naturally NOT pinched
    at the extremes (this is the same shape we want everywhere).

    Cached to bands_cache/Fig_{N}a_Organoid.csv keyed by a digest of the
    raw fold curves, so it's deterministic across runs.
    """
    import re
    src = (PROJECT_ROOT / "Output" / "PowerPoint_Figures" / f"Fig_{fig_num}" /
           f"Fig_{fig_num}a_data.xlsx")
    df = pd.read_excel(src, sheet_name="ROC_Data")
    df.columns = [str(c).strip() for c in df.columns]
    fold_pat = re.compile(r"^Fold(\d+) - (FPR|TPR|ROC)$")
    fold_ids = sorted({int(m.group(1)) for c in df.columns
                       if (m := fold_pat.match(c))})
    tprs = []
    aucs = []
    for k in fold_ids:
        fpr = df[f"Fold{k} - FPR"].to_numpy(dtype=float)
        tpr = df[f"Fold{k} - TPR"].to_numpy(dtype=float)
        auc_val = df[f"Fold{k} - ROC"].dropna().iloc[0]
        order = np.argsort(fpr)
        fpr_s, tpr_s = fpr[order], tpr[order]
        if fpr_s[0] > 0:
            fpr_s = np.r_[0.0, fpr_s]
            tpr_s = np.r_[0.0, tpr_s]
        if fpr_s[-1] < 1:
            fpr_s = np.r_[fpr_s, 1.0]
            tpr_s = np.r_[tpr_s, 1.0]
        tprs.append(np.interp(GRID, fpr_s, tpr_s))
        aucs.append(float(auc_val))
    arr = np.vstack(tprs)
    mean = arr.mean(axis=0)
    std = arr.std(axis=0, ddof=0)
    stats = {
        "FPR": GRID,
        "TPR_mean": mean,
        "TPR_lower": np.clip(mean - std, 0, 1),
        "TPR_upper": np.clip(mean + std, 0, 1),
        "AUC_mean": float(np.mean(aucs)),
        "AUC_std": float(np.std(aucs, ddof=0)),
    }
    # Cache to CSV
    key = f"Fig_{fig_num}a_Organoid"
    digest = hashlib.sha256(arr.tobytes()).hexdigest()[:12]
    path = _cache_path(key)
    if path.exists() and not force_recompute:
        try:
            with path.open() as f:
                meta = json.loads(f.readline().lstrip("# ").strip())
            if meta.get("digest") == digest:
                return stats   # cache valid; we still recomputed cheaply, but this is the same data
        except Exception:
            pass
    meta = {"key": key, "digest": digest, "method": "cv_fold_mean_std",
            "n_folds": len(fold_ids), "AUC_mean": stats["AUC_mean"],
            "AUC_std": stats["AUC_std"]}
    df_out = pd.DataFrame({"FPR": GRID, "TPR_mean": mean,
                           "TPR_lower": stats["TPR_lower"],
                           "TPR_upper": stats["TPR_upper"]})
    with path.open("w") as f:
        f.write("# " + json.dumps(meta) + "\n")
        df_out.to_csv(f, index=False)
    return stats


def cv_fold_band_for_7g_organoid(*, force_recompute: bool = False):
    """Same approach as cv_fold_band_from_a_panel but for 7g Organoid, which
    sources from Output/ROC_Data/roc_curves_all_models.xlsx HeartDamage."""
    import re
    src = PROJECT_ROOT / "Output" / "ROC_Data" / "roc_curves_all_models.xlsx"
    df = pd.read_excel(src, sheet_name="HeartDamage")
    df.columns = [str(c).strip() for c in df.columns]
    fold_pat = re.compile(r"^Fold(\d+) - (FPR|TPR)$")
    fold_ids = sorted({int(m.group(1)) for c in df.columns
                       if (m := fold_pat.match(c))})
    tprs = []
    aucs = []
    for k in fold_ids:
        fpr = df[f"Fold{k} - FPR"].dropna().to_numpy(dtype=float)
        tpr = df[f"Fold{k} - TPR"].dropna().to_numpy(dtype=float)
        if len(fpr) < 2:
            continue
        order = np.argsort(fpr)
        fpr_s, tpr_s = fpr[order], tpr[order]
        if fpr_s[0] > 0:
            fpr_s = np.r_[0.0, fpr_s]
            tpr_s = np.r_[0.0, tpr_s]
        if fpr_s[-1] < 1:
            fpr_s = np.r_[fpr_s, 1.0]
            tpr_s = np.r_[tpr_s, 1.0]
        tpr_grid = np.interp(GRID, fpr_s, tpr_s)
        tprs.append(tpr_grid)
        aucs.append(float(np.trapezoid(tpr_grid, GRID)))
    arr = np.vstack(tprs)
    mean = arr.mean(axis=0)
    std = arr.std(axis=0, ddof=0)
    stats = {
        "FPR": GRID,
        "TPR_mean": mean,
        "TPR_lower": np.clip(mean - std, 0, 1),
        "TPR_upper": np.clip(mean + std, 0, 1),
        "AUC_mean": float(np.mean(aucs)),
        "AUC_std": float(np.std(aucs, ddof=0)),
    }
    key = "Fig_7g_Organoid"
    digest = hashlib.sha256(arr.tobytes()).hexdigest()[:12]
    path = _cache_path(key)
    meta = {"key": key, "digest": digest, "method": "cv_fold_mean_std",
            "n_folds": len(tprs), "AUC_mean": stats["AUC_mean"],
            "AUC_std": stats["AUC_std"]}
    df_out = pd.DataFrame({"FPR": GRID, "TPR_mean": mean,
                           "TPR_lower": stats["TPR_lower"],
                           "TPR_upper": stats["TPR_upper"]})
    with path.open("w") as f:
        f.write("# " + json.dumps(meta) + "\n")
        df_out.to_csv(f, index=False)
    return stats

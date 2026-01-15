"""
Retrain DICTRank models using the notebook parameters and scaffold splits.

Outputs:
  - Output/ADMET_Comparison/dictrank_retrain_metrics.csv
  - Output/ADMET_Comparison/dictrank_retrain_roc.pdf
  - Output/ADMET_Comparison/dictrank_retrain_pr.pdf
  - ADMET_Comparison/Models/dictrank_retrain/ADMET-AI_xgb.pkl
  - ADMET_Comparison/Models/dictrank_retrain/SwissADME_xgb.pkl
  - Output/ADMET_Comparison/dictrank_retrain_predictions_25.csv
  - Output/ADMET_Comparison/dictrank_retrain_metrics_25.csv
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# chemprop expects numpy.VisibleDeprecationWarning (removed in numpy>=2.0)
if not hasattr(np, "VisibleDeprecationWarning"):
    class VisibleDeprecationWarning(UserWarning):
        pass
    np.VisibleDeprecationWarning = VisibleDeprecationWarning

from chemprop.data.utils import get_data, split_data
from sklearn import metrics
from sklearn.ensemble import GradientBoostingClassifier
import joblib


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"
ADMET_COMPARE_DIR = PROJECT_ROOT / "ADMET_Comparison"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
MODEL_DIR = ADMET_COMPARE_DIR / "Models" / "dictrank_retrain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CLEANED_DATA_DIR = PROJECT_ROOT / "Cleaned_Data"
SMILES_PATH = CLEANED_DATA_DIR / "drug_smiles.csv"
if not SMILES_PATH.exists():
    fallback = OUTPUT_DIR / "cardiac_rodeo_drugs_smiles.csv"
    if fallback.exists():
        SMILES_PATH = fallback
    else:
        fallback = DATA_DIR / "cardiac_rodeo_drugs_smiles.csv"
        if fallback.exists():
            SMILES_PATH = fallback
        else:
            raise FileNotFoundError(
                "Missing drug_smiles.csv. "
                f"Expected at {CLEANED_DATA_DIR / 'drug_smiles.csv'} "
                f"(or {fallback})."
            )


def load_dictrank_inputs():
    ad_data = pd.read_csv(DATA_DIR / "ADMET-AI_data.csv")
    ad_X = pd.read_csv(DATA_DIR / "ADMET-AI_Xvals.csv", index_col=0)
    ad_y = pd.read_csv(DATA_DIR / "ADMET-AI_yvals.csv", index_col=0)

    swiss_data = pd.read_csv(DATA_DIR / "SwissADME_data.csv")
    swiss_X = pd.read_csv(DATA_DIR / "SwissADME_Xvals.csv", index_col=0)
    swiss_y = pd.read_csv(DATA_DIR / "SwissADME_yvals.csv", index_col=0)

    return ad_data, ad_X, ad_y, swiss_data, swiss_X, swiss_y


def build_scaffold_splits(ad_data: pd.DataFrame, num_folds: int = 10):
    adxdata = get_data(
        str(DATA_DIR / "ADMET-AI_data.csv"),
        smiles_columns=["Standardized_SMILES"],
        target_columns=["DICTrank"],
    )
    scaf_splits: dict[int, dict[str, pd.DataFrame]] = {}

    for seed in range(num_folds):
        train, val, test = split_data(
            data=adxdata,
            split_type="scaffold_balanced",
            num_folds=num_folds,
            seed=seed,
            sizes=(0.80, 0.0, 0.20),
        )
        scaf_splits[seed] = {}

        for split, name in [(train, "train"), (val, "val"), (test, "test")]:
            indices = []
            smiles = []
            dranks = []
            for i, s in enumerate(split.smiles()):
                smi = s[0]
                smiles.append(smi)
                dranks.append(split.targets()[i][0])
                idx = ad_data[ad_data["Standardized_SMILES"] == smi].index[0]
                indices.append(idx)
            scaf_splits[seed][name] = pd.DataFrame(
                {
                    "data_index": indices,
                    "Standardized_SMILES": smiles,
                    "DICTrank": dranks,
                }
            )

    return scaf_splits


def to_binary_labels(y_series: pd.Series) -> np.ndarray:
    return np.asarray([0 if yx == "no" else 1 for yx in y_series])


def train_cv_metrics(X: pd.DataFrame, y: np.ndarray, scaf_splits: dict[int, dict[str, pd.DataFrame]]):
    tprs = []
    roc_aucs = []
    pr_aucs = []
    accs = []
    y_real = []
    y_prob = []
    precisions = []
    recalls = []
    mean_fpr = np.linspace(0, 1, 100)

    for i in scaf_splits:
        train_index = list(scaf_splits[i]["train"]["data_index"].values)
        test_index = list(scaf_splits[i]["test"]["data_index"].values)

        X_train = X.iloc[train_index]
        y_train = y[train_index]
        X_test = X.iloc[test_index]
        y_test = y[test_index]

        xgb = GradientBoostingClassifier(
            n_estimators=500,
            learning_rate=0.1,
            max_depth=12,
            random_state=0,
        )
        xgb.fit(X_train, y_train)
        probs = xgb.predict_proba(X_test)[:, 1]
        preds = (probs >= 0.5).astype(int)

        fpr, tpr, _ = metrics.roc_curve(y_test, probs)
        precision, recall, _ = metrics.precision_recall_curve(y_test, probs)

        roc_auc = metrics.auc(fpr, tpr)
        pr_auc = metrics.average_precision_score(y_test, probs)
        acc = metrics.accuracy_score(y_test, preds)

        interp_tpr = np.interp(mean_fpr, fpr, tpr)
        interp_tpr[0] = 0.0
        tprs.append(interp_tpr)
        roc_aucs.append(roc_auc)
        pr_aucs.append(pr_auc)
        accs.append(acc)
        y_real.append(y_test)
        y_prob.append(probs)
        precisions.append(precision)
        recalls.append(recall)

    return {
        "mean_fpr": mean_fpr,
        "tprs": tprs,
        "roc_aucs": roc_aucs,
        "pr_aucs": pr_aucs,
        "accs": accs,
        "y_real": y_real,
        "y_prob": y_prob,
        "precisions": precisions,
        "recalls": recalls,
    }


def plot_roc_pr(results: dict[str, dict], out_roc: Path, out_pr: Path):
    colors = {"ADMET-AI": "#2196F3", "SwissADME": "#FF9800"}

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal", adjustable="box")
    for f, r in results.items():
        for tpr in r["tprs"]:
            ax.plot(r["mean_fpr"], tpr, color=colors[f], lw=0.75, alpha=0.5, linestyle="--")
        mean_tpr = np.mean(r["tprs"], axis=0)
        mean_tpr[-1] = 1.0
        mean_auc = metrics.auc(r["mean_fpr"], mean_tpr)
        std_auc = np.std(r["roc_aucs"])
        ax.plot(
            r["mean_fpr"],
            mean_tpr,
            color=colors[f],
            label=f"{f} ROC AUC = {mean_auc:.2f} (± {std_auc:.2f})",
            lw=3,
            alpha=0.9,
        )
        std_tpr = np.std(r["tprs"], axis=0)
        tprs_upper = np.minimum(mean_tpr + std_tpr, 1)
        tprs_lower = np.maximum(mean_tpr - std_tpr, 0)
        ax.fill_between(r["mean_fpr"], tprs_lower, tprs_upper, color=colors[f], alpha=0.1)
    ax.set_title("Performance on DICTrank: ROC curve", fontsize=18)
    ax.plot([0, 1], [0, 1], "k--", label="chance (AUC = 0.50)")
    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])
    ax.set_ylabel("True Positive Rate", fontsize=14)
    ax.set_xlabel("False Positive Rate", fontsize=14)
    ax.grid(axis="both", which="major", color="grey", linestyle="--", linewidth=1)
    ax.legend(loc="lower right", fontsize=12)
    plt.tight_layout()
    plt.savefig(out_roc)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal", adjustable="box")
    for f, r in results.items():
        yr = np.concatenate(r["y_real"])
        yp = np.concatenate(r["y_prob"])
        pr, rec, _ = metrics.precision_recall_curve(yr, yp)
        mean_auc = metrics.average_precision_score(yr, yp)
        std_auc = np.std(r["pr_aucs"])
        ax.plot(rec, pr, color=colors[f], lw=3, alpha=0.9,
                label=f"{f} PR AUC = {mean_auc:.2f} (± {std_auc:.2f})")
    ax.set_title("Performance on DICTrank: PR curve", fontsize=18)
    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])
    ax.set_ylabel("Precision", fontsize=14)
    ax.set_xlabel("Recall", fontsize=14)
    ax.grid(axis="both", which="major", color="grey", linestyle="--", linewidth=1)
    ax.legend(loc="lower right", fontsize=12)
    plt.tight_layout()
    plt.savefig(out_pr)
    plt.close()


def prepare_swiss_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    feat = df[feature_cols].copy()
    for col in feature_cols:
        if feat[col].dtype == "object":
            feat[col] = feat[col].map({"Yes": 1, "No": 0, "High": 1, "Low": 0}).fillna(feat[col])
            feat[col] = pd.to_numeric(feat[col], errors="coerce")
    return feat.fillna(0)


def main():
    ad_data, ad_X, ad_y, swiss_data, swiss_X, swiss_y = load_dictrank_inputs()
    scaf_splits = build_scaffold_splits(ad_data, num_folds=10)

    dictrank_sets = {
        "ADMET-AI": {"data": ad_data, "X": ad_X, "y": ad_y},
        "SwissADME": {"data": swiss_data, "X": swiss_X, "y": swiss_y},
    }

    results = {}
    for f in dictrank_sets:
        y = to_binary_labels(dictrank_sets[f]["y"]["DICT _ Concern"])
        X = dictrank_sets[f]["X"]
        results[f] = train_cv_metrics(X, y, scaf_splits)

    plot_roc_pr(
        results,
        OUTPUT_DIR / "dictrank_retrain_roc.pdf",
        OUTPUT_DIR / "dictrank_retrain_pr.pdf",
    )

    metrics_rows = []
    for f, r in results.items():
        metrics_rows.append(
            {
                "Model": f,
                "ROC_AUC_Mean": float(np.mean(r["roc_aucs"])),
                "ROC_AUC_Std": float(np.std(r["roc_aucs"])),
                "PR_AUC_Mean": float(np.mean(r["pr_aucs"])),
                "PR_AUC_Std": float(np.std(r["pr_aucs"])),
                "Accuracy_Mean": float(np.mean(r["accs"])),
                "Accuracy_Std": float(np.std(r["accs"])),
            }
        )
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUTPUT_DIR / "dictrank_retrain_metrics.csv", index=False)

    # Train full models and save
    full_models = {}
    for f in dictrank_sets:
        y = to_binary_labels(dictrank_sets[f]["y"]["DICT _ Concern"])
        X = dictrank_sets[f]["X"]
        xgb = GradientBoostingClassifier(
            n_estimators=500,
            learning_rate=0.1,
            max_depth=12,
            random_state=0,
        )
        xgb.fit(X, y)
        joblib.dump(xgb, MODEL_DIR / f"{f}_xgb.pkl")
        full_models[f] = xgb

    # Predict on 25-drug set (SwissADME only has 23 drugs)
    drugs_df = pd.read_csv(SMILES_PATH)
    drug_names = drugs_df["Drug"].tolist()

    admet_25 = pd.read_csv(OUTPUT_DIR / "cardiac_rodeo_full_ADMET.csv")
    admet_feat_cols = ad_X.columns.tolist()
    X_admet_25 = admet_25[admet_feat_cols].copy()

    swiss_25 = pd.read_csv(OUTPUT_DIR / "cardiac_rodeo_full_swissadme.csv")
    swiss_feat_cols = swiss_X.columns.tolist()
    if "Drug" not in swiss_25.columns:
        raise KeyError("SwissADME features must include a Drug column.")

    swiss_indexed = swiss_25.set_index("Drug")
    swiss_drug_names = [d for d in drug_names if d in swiss_indexed.index]
    missing_swiss = [d for d in drug_names if d not in swiss_indexed.index]
    if missing_swiss:
        print("SwissADME missing drugs (expected 23 rows):")
        for drug in missing_swiss:
            print(f"  - {drug}")

    swiss_25_aligned = swiss_indexed.loc[swiss_drug_names].reset_index()
    X_swiss_25 = prepare_swiss_features(swiss_25_aligned, swiss_feat_cols)

    admet_probs = full_models["ADMET-AI"].predict_proba(X_admet_25)[:, 1]
    swiss_probs = full_models["SwissADME"].predict_proba(X_swiss_25)[:, 1]

    preds_df = pd.DataFrame(
        {
            "Drug": drug_names,
            "ADMET_AI_Prob": admet_probs,
        }
    )
    preds_df["SwissADME_Prob"] = np.nan
    preds_df.loc[preds_df["Drug"].isin(swiss_drug_names), "SwissADME_Prob"] = swiss_probs
    preds_df.to_csv(OUTPUT_DIR / "dictrank_retrain_predictions_25.csv", index=False)

    # Evaluate against 25-drug labels (SwissADME evaluated on 23 drugs only)
    labels = pd.read_csv(PROJECT_ROOT / "Cleaned_Data" / "drug_classification.csv")
    y_true_all = labels.set_index("Drug").loc[drug_names, "heart_damage"].astype(bool).astype(int).values
    metrics_25 = []
    preds_admet = (admet_probs >= 0.5).astype(int)
    fpr, tpr, _ = metrics.roc_curve(y_true_all, admet_probs)
    metrics_25.append(
        {
            "Model": "ADMET-AI",
            "ROC_AUC": float(metrics.auc(fpr, tpr)),
            "Accuracy": float(metrics.accuracy_score(y_true_all, preds_admet)),
            "N": int(len(y_true_all)),
        }
    )

    if swiss_drug_names:
        y_true_swiss = labels.set_index("Drug").loc[swiss_drug_names, "heart_damage"].astype(bool).astype(int).values
        preds_swiss = (swiss_probs >= 0.5).astype(int)
        fpr, tpr, _ = metrics.roc_curve(y_true_swiss, swiss_probs)
        metrics_25.append(
            {
                "Model": "SwissADME",
                "ROC_AUC": float(metrics.auc(fpr, tpr)),
                "Accuracy": float(metrics.accuracy_score(y_true_swiss, preds_swiss)),
                "N": int(len(y_true_swiss)),
            }
        )
    pd.DataFrame(metrics_25).to_csv(OUTPUT_DIR / "dictrank_retrain_metrics_25.csv", index=False)

    print("Retraining complete.")
    print(f"Metrics: {OUTPUT_DIR / 'dictrank_retrain_metrics.csv'}")
    print(f"ROC: {OUTPUT_DIR / 'dictrank_retrain_roc.pdf'}")
    print(f"PR: {OUTPUT_DIR / 'dictrank_retrain_pr.pdf'}")
    print(f"Models: {MODEL_DIR}")
    print(f"25-drug predictions: {OUTPUT_DIR / 'dictrank_retrain_predictions_25.csv'}")


if __name__ == "__main__":
    main()

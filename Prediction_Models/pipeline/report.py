"""
LaTeX Report Generation

Generates a comprehensive LaTeX report of the prediction model results.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import zipfile

from . import config


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_number(value: float, precision: int = 4) -> str:
    """Format a number for LaTeX."""
    if np.isnan(value):
        return "N/A"
    return f"{value:.{precision}f}"


def generate_metrics_table(
    evaluations: Dict[str, Dict[str, Any]]
) -> str:
    """
    Generate LaTeX table of model metrics.

    Parameters:
    -----------
    evaluations : Dict[str, Dict]
        Evaluation results

    Returns:
    --------
    str
        LaTeX table code
    """
    latex = r"""
\begin{table}[htbp]
\centering
\caption{Model Performance Metrics (LOOCV)}
\label{tab:metrics}
\begin{tabular}{lccccc}
\toprule
\textbf{Model} & \textbf{Accuracy} & \textbf{F1-Score} & \textbf{AUC-ROC} & \textbf{Sensitivity} & \textbf{Specificity} \\
\midrule
"""

    for model_name in ['arrhythmia', 'heart_damage']:
        if model_name not in evaluations:
            continue

        metrics = evaluations[model_name]['metrics']
        display_name = model_name.replace('_', ' ').title()

        latex += f"{display_name} & "
        latex += f"{format_number(metrics['accuracy'])} & "
        latex += f"{format_number(metrics['f1'])} & "
        latex += f"{format_number(metrics.get('auc', np.nan))} & "
        latex += f"{format_number(metrics['sensitivity'])} & "
        latex += f"{format_number(metrics['specificity'])} \\\\\n"

    # Multiclass (Concern)
    if 'concern' in evaluations:
        metrics = evaluations['concern']['metrics']
        latex += f"Concern & "
        latex += f"{format_number(metrics['accuracy'])} & "
        latex += f"{format_number(metrics['f1_macro'])} & "
        latex += f"{format_number(metrics.get('mean_auc', np.nan))} & "
        latex += "-- & -- \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_concern_table(
    evaluations: Dict[str, Dict[str, Any]]
) -> str:
    """
    Generate LaTeX table for Concern per-class metrics.

    Parameters:
    -----------
    evaluations : Dict[str, Dict]
        Evaluation results

    Returns:
    --------
    str
        LaTeX table code
    """
    if 'concern' not in evaluations:
        return ""

    metrics = evaluations['concern']['metrics']

    latex = r"""
\begin{table}[htbp]
\centering
\caption{Concern Model Per-Class Metrics}
\label{tab:concern_metrics}
\begin{tabular}{lccc}
\toprule
\textbf{Class} & \textbf{Accuracy} & \textbf{F1-Score} & \textbf{AUC-ROC} \\
\midrule
"""

    for label in config.CONCERN_LABELS:
        acc = metrics['per_class_accuracy'].get(label, np.nan)
        f1 = metrics['per_class_f1'].get(label, np.nan)
        auc_val = metrics.get('per_class_auc', {}).get(label, np.nan)

        latex += f"{label.capitalize()} & "
        latex += f"{format_number(acc)} & "
        latex += f"{format_number(f1)} & "
        latex += f"{format_number(auc_val)} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_feature_importance_table(
    explanations: Dict[str, Dict[str, Any]],
    top_n: int = 10
) -> str:
    """
    Generate LaTeX table of top features.

    Parameters:
    -----------
    explanations : Dict[str, Dict]
        Explanation results
    top_n : int
        Number of top features to show

    Returns:
    --------
    str
        LaTeX table code
    """
    latex = r"""
\begin{table}[htbp]
\centering
\caption{Top """ + str(top_n) + r""" Most Important Features by Model}
\label{tab:features}
\begin{tabular}{clc}
\toprule
\textbf{Rank} & \textbf{Feature} & \textbf{Importance} \\
\midrule
"""

    for model_name in ['arrhythmia', 'heart_damage', 'concern']:
        if model_name not in explanations:
            continue

        display_name = model_name.replace('_', ' ').title()
        latex += f"\\multicolumn{{3}}{{c}}{{\\textbf{{{display_name}}}}} \\\\\n"
        latex += "\\midrule\n"

        imp_df = explanations[model_name]['feature_importances'].head(top_n)
        for rank, (_, row) in enumerate(imp_df.iterrows(), 1):
            feature = escape_latex(str(row['Feature']))
            importance = format_number(row['Importance'])
            latex += f"{rank} & {feature} & {importance} \\\\\n"

        latex += "\\midrule\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_full_report(
    results: Dict[str, Dict[str, Any]],
    evaluations: Dict[str, Dict[str, Any]],
    explanations: Dict[str, Dict[str, Any]],
    equation_name: str = "dual_exponential",
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate complete LaTeX report.

    Parameters:
    -----------
    results : Dict[str, Dict]
        Training results
    evaluations : Dict[str, Dict]
        Evaluation results
    explanations : Dict[str, Dict]
        Explanation results
    equation_name : str
        Name of the equation used
    output_path : Path, optional
        Output file path

    Returns:
    --------
    Path
        Path to generated LaTeX file
    """
    if output_path is None:
        output_path = config.LATEX_OUTPUT_DIR / "prediction_models_report.tex"

    print("\nGenerating LaTeX report...")

    # Document header
    latex = r"""\documentclass[11pt,a4paper]{article}

% Packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{cleveref}
\usepackage[margin=1in]{geometry}
\usepackage{float}

% Title
\title{Prediction Models Report\\
\large Cardiac Outcome Prediction using """ + escape_latex(equation_name.replace('_', ' ').title()) + r""" Coefficients}
\author{Generated by Cardiac RODEO Pipeline}
\date{""" + datetime.now().strftime("%B %d, %Y") + r"""}

\begin{document}

\maketitle

\begin{abstract}
This report presents the results of machine learning models trained to predict cardiac outcomes
(Arrhythmia, Heart Damage, and Concern level) from drug response coefficients.
Models were trained using Leave-One-Out Cross-Validation (LOOCV) for robust performance estimation.
\end{abstract}

\tableofcontents
\newpage

\section{Introduction}

Three prediction models were trained on """ + escape_latex(equation_name.replace('_', ' ').title()) + r""" coefficients:

\begin{description}
    \item[Arrhythmia] XGBoost classifier (binary: true/false)
    \item[Heart Damage] RBF SVM classifier (binary: positive/negative)
    \item[Concern] Random Forest classifier (multiclass: no/less/most)
\end{description}

All models were evaluated using Leave-One-Out Cross-Validation (LOOCV) to provide
unbiased performance estimates on small sample sizes.

\section{Model Performance}

"""

    # Add metrics tables
    latex += generate_metrics_table(evaluations)
    latex += "\n"
    latex += generate_concern_table(evaluations)

    # ROC curves section
    latex += r"""
\section{ROC Curves}

\\cref{fig:roc_summary} shows the ROC curves for all three models.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{../Prediction_Plots/summary_roc.png}
\caption{ROC curves for all prediction models.}
\label{fig:roc_summary}
\end{figure}

"""

    # Individual ROC curves
    for model_name in ['arrhythmia', 'heart_damage', 'concern']:
        if model_name not in results:
            continue

        display_name = model_name.replace('_', ' ').title()
        latex += f"""
\\subsection{{{display_name}}}

\\begin{{figure}}[H]
\\centering
\\includegraphics[width=0.7\\textwidth]{{../Prediction_Plots/roc_{model_name}.png}}
\\caption{{ROC curve for {display_name} prediction.}}
\\label{{fig:roc_{model_name}}}
\\end{{figure}}

"""

    # Confusion matrices section
    latex += r"""
\section{Confusion Matrices}

"""

    for model_name in ['arrhythmia', 'heart_damage', 'concern']:
        if model_name not in evaluations:
            continue

        display_name = model_name.replace('_', ' ').title()
        latex += f"""
\\subsection{{{display_name}}}

\\begin{{figure}}[H]
\\centering
\\includegraphics[width=0.5\\textwidth]{{../Prediction_Plots/cm_{model_name}.png}}
\\caption{{Confusion matrix for {display_name} prediction.}}
\\label{{fig:cm_{model_name}}}
\\end{{figure}}

"""

    # Feature importance section
    latex += r"""
\section{Feature Importance}

"""
    latex += generate_feature_importance_table(explanations)

    for model_name in ['arrhythmia', 'heart_damage', 'concern']:
        if model_name not in explanations:
            continue

        display_name = model_name.replace('_', ' ').title()
        latex += f"""
\\subsection{{{display_name}}}

\\begin{{figure}}[H]
\\centering
\\includegraphics[width=0.8\\textwidth]{{../Prediction_Plots/importance_{model_name}.png}}
\\caption{{Top features for {display_name} prediction.}}
\\label{{fig:importance_{model_name}}}
\\end{{figure}}

"""

    # Methods section
    latex += r"""
\section{Methods}

\subsection{Data}

Features were extracted from """ + escape_latex(equation_name.replace('_', ' ').title()) + r""" coefficients
fitted to drug response data. Each drug has coefficients for both Contractility and O2 responses.

\subsection{Models}

\begin{description}
    \item[Arrhythmia (XGBoost)] Gradient boosting with 100 trees, max depth 3, learning rate 0.1
    \item[Heart Damage (RBF SVM)] Radial basis function kernel with C=1.0, gamma='scale'
    \item[Concern (Random Forest)] 100 trees, max depth 5, min samples split 5
\end{description}

\subsection{Cross-Validation}

Leave-One-Out Cross-Validation (LOOCV) was used to evaluate model performance.
Each sample was held out exactly once for testing while the remaining samples were used for training.
This provides an unbiased estimate of generalization performance.

\subsection{Feature Importance}

\begin{description}
    \item[XGBoost] Native feature importance (gain-based)
    \item[RBF SVM] Permutation importance (10 repeats)
    \item[Random Forest] Native feature importance (impurity-based)
\end{description}

\section{Conclusion}

The models demonstrate varying levels of predictive performance across the three cardiac outcomes.
The LOOCV approach ensures robust evaluation on the limited sample size.

\end{document}
"""

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex)

    print(f"  Saved: {output_path}")

    zip_path = create_report_zip(output_path)
    print(f"  Saved: {zip_path}")

    return output_path


def create_report_zip(tex_path: Path) -> Path:
    """Create a zip archive containing the LaTeX report and referenced plots."""
    zip_path = tex_path.with_suffix(".zip")
    project_root = config.PROJECT_ROOT

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Include the .tex file with repo-relative path to preserve figure references.
        try:
            zf.write(tex_path, tex_path.relative_to(project_root))
        except ValueError:
            zf.write(tex_path, tex_path.name)

        # Include all plots referenced by the report (and any other files in the plots dir).
        for path in config.PLOTS_OUTPUT_DIR.rglob("*"):
            if not path.is_file():
                continue
            try:
                arcname = path.relative_to(project_root)
            except ValueError:
                arcname = path.name
            zf.write(path, arcname)

    return zip_path


if __name__ == "__main__":
    print("Report module loaded successfully")
    print(f"Output directory: {config.LATEX_OUTPUT_DIR}")

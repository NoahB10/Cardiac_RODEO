# Prediction Model Output Updates

When modifying prediction models in Cardiac RODEO, you MUST update all associated outputs.

## Trigger

Use this skill automatically when:
- Changing model selection (e.g., adding GaussianNB, changing from SVM to RandomForest)
- Modifying SHAP analysis
- Updating ROC curve generation
- Changing performance metrics
- Any change to `Prediction_Models/loocv_model_comparison.py`

## Required Outputs

After ANY prediction model change, update these outputs:

### 1. Excel Files in `Output/Excel_Figures/`

Create **ONE Excel file per figure type** with sheets for each target inside:

| Excel File | Sheets Inside |
|------------|---------------|
| `Performance_Metrics.xlsx` | Arrhythmia, Heart Damage, Concern Binary |
| `SHAP_Feature_Importance.xlsx` | Arrhythmia, Heart Damage, Concern Binary |
| `ROC_Curves.xlsx` | Arrhythmia, Heart Damage, Concern Binary |
| `Cumulative_Feature_Importance.xlsx` | Arrhythmia, Heart Damage, Concern Binary |
| `Prediction_Scatter.xlsx` | Arrhythmia, Heart Damage, Concern Binary |
| `Confusion_Matrices.xlsx` | Arrhythmia, Heart Damage, Concern Binary |

### 2. Excel Files MUST Have Embedded Charts

Every Excel file must contain openpyxl charts embedded in each sheet. Data alone is NOT sufficient.

### 3. Save Matplotlib PNG Images (NO PDF)

For every Excel chart, save a corresponding PNG image to `Output/Excel_Figures/`:
- `metrics_arrhythmia.png`, `metrics_heart_damage.png`, `metrics_concern_binary.png`
- `shap_arrhythmia.png`, `shap_heart_damage.png`, `shap_concern_binary.png`
- `roc_arrhythmia.png`, `roc_heartdamage.png`, `roc_concernbinary.png`
- `cumulative_arrhythmia.png`, `cumulative_heart_damage.png`, `cumulative_concern_binary.png`
- `scatter_arrhythmia.png`, `scatter_heart_damage.png`, `scatter_concern_binary.png`
- `confmat_arrhythmia.png`, `confmat_heart_damage.png`, `confmat_concern_binary.png`

**Do NOT save PDF versions.**

### 4. Only Binary Targets

Only include these 3 targets everywhere:
- **Arrhythmia**
- **Heart Damage** (heart_damage)
- **Concern Binary** (concern_binary)

Do NOT include multiclass concern (no "Concern No", "Concern Less", "Concern Most").

### 5. Consistent Thresholds

Thresholds MUST be consistent across all plots and confusion matrices:
- Read from `Output/Prediction_Scatter_Data/prediction_thresholds.json`
- Currently: Arrhythmia=35%, Heart Damage=5%, Concern Binary=40%
- Confusion matrices must use these thresholds (not default 50%)
- Scatter plots must show threshold line at these values
- Cumulative plots must show threshold line at these values

### 6. Figure Sizes

All figures: **1.72" height** with width scaled proportionally:
- Performance metrics: 1.69" x 1.72"
- SHAP: 2.15" x 1.72"
- ROC: 1.72" x 1.72" (square)
- Cumulative: 5.5" x 1.72" (wide for legend)
- Scatter: 3.44" x 1.72"
- Confusion: 2.06" x 1.72"

### 7. ROC Curves

- Use **ScatterChart** (not LineChart) for proper X-Y plotting
- Mean ROC line (solid blue)
- Std deviation range (grey shaded fill)
- Upper/lower std bounds (grey dotted lines)
- Random classifier line (black dashed)

### 8. Cumulative Feature Importance

- Each drug gets its own line (rainbow colormap)
- **Markers based on pass/fail:**
  - `o` (circles) = Positive class (Arrhythmia=True, heart_damage=True, Concern='most')
  - `x` (X markers) = Negative class
- Threshold line (red dashed) from prediction_thresholds.json
- X-axis: Feature rank (1-14)
- Y-axis: Predicted Probability (0-100%)
- Legend outside plot

### 9. Prediction Scatter

- Each drug as a point
- Color by actual class: green=#2ecc71 (positive), red=#e74c3c (negative)
- Threshold line (red dashed) from prediction_thresholds.json
- Y-axis: 0-105% (percentages, not probabilities)

### 10. Performance Metrics Bar Chart

- Include 4 metrics: Accuracy, F1, MCC, AUC
- Metric names on x-axis (no legend)
- Model name in title (not on x-axis)
- Bar colors: blue, green, purple, red

## Script Location

Run `update_excel_charts.py` in the project root to regenerate all Excel files and images:

```bash
python update_excel_charts.py
```

## Pipeline for Full Regeneration

1. Run pipeline: `python Prediction_Models/loocv_model_comparison.py`
2. Update Excel/PNG: `python update_excel_charts.py`

## Checklist Before Completing Any Prediction Model Change

- [ ] Updated model in `loocv_model_comparison.py`
- [ ] Ran the pipeline to generate new metrics
- [ ] Ran `update_excel_charts.py`
- [ ] Verified Excel files have embedded charts (not just data)
- [ ] Verified PNG images saved for each chart
- [ ] Verified only 3 binary targets in all outputs
- [ ] Verified ROC curves show std range with ScatterChart
- [ ] Verified thresholds are consistent (scatter, cumulative, confusion)
- [ ] Verified cumulative has X/O markers for fail/pass

---

# ADMET Comparison Outputs

When updating ADMET comparison analysis, update all associated outputs.

## Trigger

Use this section when:
- Modifying `ADMET_Comparison/Scripts/full_analysis.py`
- Changing DICTrank model training
- Updating scaffold CV analysis
- Any ADMET vs Organoid comparison changes

## ADMET Output Files

Output folder: `Output/Excel_Figures/ADMET/`

| Excel File | PNG Image | Contents |
|------------|-----------|----------|
| `DICTrank_Predictions.xlsx` | `dictrank_predictions_25.png` | Heart damage predictions for 25 drugs |
| `DICTrank_Training.xlsx` | `dictrank_training.png` | DICTrank training (555 drugs, 10-fold CV) |
| `Scaffold_CV.xlsx` | `scaffold_cv_metrics.png` | Scaffold CV on 25 drugs + confusion matrices |
| `ROC_Comparison.xlsx` | `roc_comparison.png` | ROC overlay: DICTrank vs Scaffold vs Organoid |
| `Overall_Comparison.xlsx` | `overall_comparison.png` | Summary comparing all models |

## ADMET-Specific Rules

### 1. SwissADME Missing Drugs
Always note that **SwissADME is missing 2 drugs**:
- Dactinomycin
- Plicamycin
- Reason: Molecules too large for SwissADME

### 2. What to Show
- DICTrank on 25 drugs (predictions, ROC, confusion)
- Scaffold CV for heart damage (newly trained on 25 drugs)
- ROC overlay comparison (Organoid vs DICTrank vs Scaffold)
- Heart damage probability plot

### 3. What NOT to Show
- LOOCV version on 25 drugs (not useful)

### 4. Prediction Plot Markers
- ADMET-AI: circles (`o`)
- SwissADME: squares (`s`)
- Colors: green = HD positive, red = HD negative

### 5. Figure Sizes
Same as prediction models: **1.72" height**, width scaled proportionally

## ADMET Script

Run `update_admet_excel_charts.py` in project root:

```bash
python update_admet_excel_charts.py
```

## ADMET Checklist

- [ ] Ran `ADMET_Comparison/Scripts/full_analysis.py` if data changed
- [ ] Ran `update_admet_excel_charts.py`
- [ ] Verified SwissADME missing drugs noted
- [ ] Verified ROC comparison includes Organoid
- [ ] Verified Excel files have embedded charts
- [ ] Verified PNG images saved

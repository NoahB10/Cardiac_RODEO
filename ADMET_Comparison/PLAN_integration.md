# Integration Plan: Manually-Gathered ADMET & SwissADME Features

## Problem Statement

The original SMILES in `drug_smiles.csv` were incorrect for many drugs. You manually gathered correct features from:
- **ADMET-AI website** → `25 drugs ADMET.xlsx` (all 25 drugs)
- **SwissADME website** → `23 drugs swissadme.csv` (23 drugs - **skipped Dactinomycin and Plicamycin** because they're too large)

## Current State

**Existing Files:**
- `Output/ADMET_Comparison/cardiac_rodeo_full_ADMET.csv` (25 × 42) - OLD features from wrong SMILES
- `Output/ADMET_Comparison/cardiac_rodeo_full_swissadme.csv` (25 × 49) - OLD features from wrong SMILES
- `Cleaned_Data/drug_smiles.csv` (25 drugs) - Contains incorrect SMILES

**New Files:**
- `ADMET_Comparison/25 drugs ADMET.xlsx` (25 × 41) - Correct features from website
- `ADMET_Comparison/23 drugs swissadme.csv` (23 × 49) - Correct features from website (missing Dactinomycin, Plicamycin)

## Drug Name Mapping

### All 25 Drugs (Alphabetical Order):
1. Amiodarone
2. Bortezomib
3. Chlorpromazine
4. Cobimetinib
5. **Dactinomycin** ← NOT in SwissADME (too large)
6. Daunorubicin
7. Doxorubicin
8. Epirubicin
9. Erlotinib
10. Etomoxir
11. Gemcitibine
12. Ibrutinib
13. Ibuprofen
14. Isoproterenol
15. Mexiletine
16. Nifedipine
17. Panobinostat
18. **Plicamycin** ← NOT in SwissADME (too large)
19. Rosiglitazone
20. Sotalol
21. Sunitinib
22. Vandetanib
23. Vincristine
24. Vioxx
25. Vorinostat

### SwissADME Mapping (Molecule 1-23):
- Molecule 1 = Amiodarone
- Molecule 2 = Bortezomib
- Molecule 3 = Chlorpromazine
- Molecule 4 = Cobimetinib
- **[SKIP Dactinomycin]**
- Molecule 5 = Daunorubicin
- Molecule 6 = Doxorubicin
- Molecule 7 = Epirubicin
- Molecule 8 = Erlotinib
- Molecule 9 = Etomoxir
- Molecule 10 = Gemcitibine
- Molecule 11 = Ibrutinib
- Molecule 12 = Ibuprofen
- Molecule 13 = Isoproterenol
- Molecule 14 = Mexiletine
- Molecule 15 = Nifedipine
- Molecule 16 = Panobinostat
- **[SKIP Plicamycin]**
- Molecule 17 = Rosiglitazone
- Molecule 18 = Sotalol
- Molecule 19 = Sunitinib
- Molecule 20 = Vandetanib
- Molecule 21 = Vincristine
- Molecule 22 = Vioxx
- Molecule 23 = Vorinostat

## Integration Steps

### Step 1: Backup Old Files
```
Output/ADMET_Comparison/cardiac_rodeo_full_ADMET.csv
  → cardiac_rodeo_full_ADMET_OLD.csv

Output/ADMET_Comparison/cardiac_rodeo_full_swissadme.csv
  → cardiac_rodeo_full_swissadme_OLD.csv

Cleaned_Data/drug_smiles.csv
  → drug_smiles_OLD.csv
```

### Step 2: Create New cardiac_rodeo_full_ADMET.csv
1. Load `25 drugs ADMET.xlsx` (25 rows × 41 ADMET feature columns)
2. Insert 'Drug' column at position 0 with all 25 drug names (alphabetically sorted)
3. Merge with `drug_classification.csv` to add target columns:
   - Arrhythmia
   - Cardiotoxicity
   - heart_damage
   - Concern
4. **Result:** 25 rows × ~46 columns (Drug + 41 ADMET + 4 targets)
5. Save to `Output/ADMET_Comparison/cardiac_rodeo_full_ADMET.csv`

### Step 3: Create New cardiac_rodeo_full_swissadme.csv
1. Load `23 drugs swissadme.csv` (23 rows × 49 columns)
2. Drop columns: 'Molecule', 'Canonical SMILES', 'Formula' (keep features only)
3. Add 'Drug' column with correct mapping (accounting for skipped drugs)
4. Insert NaN rows for Dactinomycin and Plicamycin at correct positions (5th and 18th)
5. Merge with `drug_classification.csv` to add target columns
6. **Result:** 25 rows × ~52 columns (Drug + ~47 SwissADME + 4 targets)
7. Save to `Output/ADMET_Comparison/cardiac_rodeo_full_swissadme.csv`

### Step 4: Update drug_smiles.csv
1. Load current `drug_smiles.csv`
2. Backup to `drug_smiles_OLD.csv`
3. Extract 'Canonical SMILES' from `23 drugs swissadme.csv`
4. Update SMILES for the 23 drugs
5. Keep original SMILES for Dactinomycin and Plicamycin (or mark for manual update)
6. Save to `Cleaned_Data/drug_smiles.csv`

### Step 5: Validation & Comparison
1. Compare old vs new ADMET features (sample 5 drugs)
2. Compare old vs new SwissADME features (sample 5 drugs)
3. Generate comparison report:
   - Which drugs changed most?
   - Which features changed most?
   - Feature correlation analysis

## Files Affected in Pipeline

These scripts read the feature files and will automatically use the new data:
- `Scripts/full_analysis.py` (line 346-347)
- `Scripts/retrain_dictrank_models.py` (line 297, 301)
- `Scripts/predict_swissadme.py` (line 41)
- `Scripts/predict_retrained_dictrank.py` (line 49, 54)

**No code changes needed** - they read from the same file paths we'll overwrite.

## Expected Output Structure

### cardiac_rodeo_full_ADMET.csv (25 × ~46)
```
Drug,Mutagenicity,Blood-Brain Barrier Penetration,...,Arrhythmia,Cardiotoxicity,heart_damage,Concern
Amiodarone,0.176364,0.819352,...,true,true,true,most
Bortezomib,0.508760,0.484189,...,false,false,false,no
...
```

### cardiac_rodeo_full_swissadme.csv (25 × ~52)
```
Drug,MW,#Heavy atoms,#Aromatic heavy atoms,...,Arrhythmia,Cardiotoxicity,heart_damage,Concern
Amiodarone,645.31,31,15,...,true,true,true,most
Bortezomib,384.24,28,12,...,false,false,false,no
...
Dactinomycin,NaN,NaN,NaN,...,true,true,true,most
...
Plicamycin,NaN,NaN,NaN,...,false,false,false,no
...
```

## Validation Checks

Before running the pipeline:
1. ✓ All 25 drugs present in both files
2. ✓ Drug order matches (alphabetically sorted)
3. ✓ Target labels match across both files
4. ✓ No unexpected NaN values (except Dactinomycin/Plicamycin in SwissADME)
5. ✓ Feature counts: ADMET=41, SwissADME=~47

## Next Steps (After Approval)

1. Run integration script to create new files
2. Generate comparison report (old vs new)
3. Run `full_analysis.py` to retrain models with correct features
4. Compare model performance (old vs new)
5. Update reports and figures

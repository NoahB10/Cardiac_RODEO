DRUG SMILES MASTER FILE
========================

File: drug_smiles.csv
Purpose: Master copy of SMILES strings for all 25 Cardiac RODEO drugs

IMPORTANT NOTES:
----------------
1. This is the SOURCE OF TRUTH for drug SMILES strings
2. All analysis pipelines (ADMET comparison, prediction models, etc.) read from this file
3. To correct SMILES errors, edit drug_smiles.csv directly
4. Changes will be automatically used in all downstream analyses
5. Do NOT edit the copy in Output/ADMET_Comparison/ - it may be overwritten

FILE FORMAT:
-----------
Drug,CID,MolecularFormula,MolecularWeight,SMILES

- Drug: Common name
- CID: PubChem Compound ID
- MolecularFormula: Chemical formula
- MolecularWeight: Molecular weight (g/mol)
- SMILES: Simplified Molecular Input Line Entry System string

USAGE:
------
Referenced by:
- ADMET_Comparison/Scripts/full_analysis.py
- Future: prediction model pipelines (if SMILES-based features added)

To verify SMILES correctness:
1. Check against PubChem: https://pubchem.ncbi.nlm.nih.gov/compound/{CID}
2. Use SMILES validators (RDKit, OpenBabel, etc.)
3. Ensure consistency with molecular formula and weight

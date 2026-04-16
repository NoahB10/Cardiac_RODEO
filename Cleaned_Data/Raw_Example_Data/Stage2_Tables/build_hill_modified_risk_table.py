"""
Build grouped risk table Excel from modified Hill coefficients.

Functions:
- load_coefficients(csv_path): read coefficients CSV to DataFrame.
- group_and_write(tbl, out_xlsx): split into the same clinical groups as plot_modified_hill.m and write to Excel sheets.

Usage:
    python build_hill_modified_risk_table.py

Notes:
- Uses the grouping logic found in plot_modified_hill.m.
- Writes to hill_modified_risk_table.xlsx in the current folder.
"""

import os
import pandas as pd


def normalize_name(s: pd.Series) -> pd.Series:
    return (s.astype(str)
            .str.lower()
            .str.replace(r"\s|\(.*?\)", "", regex=True))


def load_coefficients(csv_path: str) -> pd.DataFrame:
    cols = [
        'Drug','O0','Emax','Kappa','Tau','n','m','Cmax_used',
        'CT50_at_tau','CT50_ratio','N_points','SSE','RMSE','R2'
    ]
    tbl = pd.read_csv(csv_path)
    # Keep only known columns if present
    keep = [c for c in cols if c in tbl.columns]
    tbl = tbl[keep]
    tbl['DrugKey'] = normalize_name(tbl['Drug'])
    return tbl


def lookup_idx(drug_keys, tbl_keys):
    idx = []
    for k in drug_keys:
        hit = tbl_keys[tbl_keys == k]
        if len(hit) == 0:
            # startswith fallback
            hit = tbl_keys[tbl_keys.str.startswith(k)]
        if len(hit) > 0:
            # take first match index
            i = tbl_keys[tbl_keys == hit.iloc[0]].index[0]
            idx.append(i)
    # unique preserve order
    idx = pd.Index(idx).drop_duplicates().tolist()
    return idx


def group_and_write(tbl: pd.DataFrame, out_xlsx: str) -> None:
    # Clinical groupings (mirroring plot_modified_hill.m)
    arrhythmia_high = normalize_name(pd.Series([
        'Bortezomib', 'Epirubicin', 'Ibrutinib', 'Mexiletine', 'Panobinostat', 'Sotalol', 'Sunitinib', 'Vandetanib'
    ])).tolist()
    arrhythmia_low = normalize_name(pd.Series([
        'Chlorpromazine', 'Gemcitibine', 'Nifedipine'
    ])).tolist()

    heartfailure_high = normalize_name(pd.Series([
        'Bortezomib', 'Epirubicin', 'Erlotinib', 'Ibuprofen', 'Sotalol', 'Sunitinib', 'Vandetanib', 'Rosiglitazon',
        'DOXOrubicin', 'Daunorubicin', 'Cobimetinib'
    ])).tolist()
    heartfailure_low = normalize_name(pd.Series([
        'Gemcitibine', 'Vincristine', 'Vorinostat'
    ])).tolist()

    none_group = normalize_name(pd.Series([
        'Amiodarone', 'Dactinomycin', 'Etomoxir', 'Isoproterenol', 'Plicamycin', 'Troglitazone'
    ])).tolist()

    # Resolve indices
    keys = tbl['DrugKey']
    groups = {
        'Arrhythmia_High': tbl.loc[lookup_idx(arrhythmia_high, keys)],
        'Arrhythmia_Low': tbl.loc[lookup_idx(arrhythmia_low, keys)],
        'HeartFailure_High': tbl.loc[lookup_idx(heartfailure_high, keys)],
        'HeartFailure_Low': tbl.loc[lookup_idx(heartfailure_low, keys)],
        'None': tbl.loc[lookup_idx(none_group, keys)],
        'Overview_All': tbl,
    }

    # Sort within sheets for readability
    for name, df in groups.items():
        if 'CT50_ratio' in df.columns:
            groups[name] = df.sort_values(by=['CT50_ratio','n','Emax'], ascending=[True, True, False])
        else:
            groups[name] = df

    # Write to Excel
    with pd.ExcelWriter(out_xlsx, engine='xlsxwriter') as writer:
        for sheet, df in groups.items():
            df_out = df.copy()
            # Drop helper key
            if 'DrugKey' in df_out.columns:
                df_out = df_out.drop(columns=['DrugKey'])
            df_out.to_excel(writer, sheet_name=sheet, index=False)

    print(f"Wrote grouped risk table to {out_xlsx}")


def main():
    coef_csv = 'hill_coefficients_modified_averaged.csv'
    out_xlsx = 'hill_modified_risk_table.xlsx'
    if not os.path.exists(coef_csv):
        raise FileNotFoundError(f"Missing coefficients CSV: {coef_csv}")
    tbl = load_coefficients(coef_csv)
    group_and_write(tbl, out_xlsx)


if __name__ == '__main__':
    main()







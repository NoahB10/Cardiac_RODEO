"""
Rebuild hill_modified_risk_table.csv using coefficients and MATLAB risk groupings.

Output columns:
Drug,Arrhythmia Risk High,Arrhythmia Risk Low,Cardiac Risk High,Cardiac Risk Low,O0,Emax,Kappa,Tau,n,m,Cmax,R2
"""

import os
import pandas as pd


def normalize_name(s: pd.Series) -> pd.Series:
    return (s.astype(str)
            .str.lower()
            .str.replace(r"\s|\(.*?\)", "", regex=True))


def load_coefficients(csv_path: str) -> pd.DataFrame:
    tbl = pd.read_csv(csv_path)
    # Expected columns in averaged coefficients
    # Drug,O0,Emax,Kappa,Tau,n,m,Cmax_used,CT50_at_tau,CT50_ratio,N_points,SSE,RMSE,R2
    tbl['DrugKey'] = normalize_name(tbl['Drug'])
    return tbl


def build_flags(tbl: pd.DataFrame) -> pd.DataFrame:
    keys = tbl['DrugKey']

    # MATLAB groupings mirrored
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

    def in_list(k, L):
        # exact or startswith match
        return (k in L) or any(k.startswith(x) for x in L)

    rows = []
    for _, r in tbl.iterrows():
        k = r['DrugKey']
        row = {
            'Drug': r['Drug'],
            'Arrhythmia Risk High': 'TRUE' if in_list(k, arrhythmia_high) else 'FALSE',
            'Arrhythmia Risk Low': 'TRUE' if in_list(k, arrhythmia_low) else 'FALSE',
            'Cardiac Risk High': 'TRUE' if in_list(k, heartfailure_high) else 'FALSE',
            'Cardiac Risk Low': 'TRUE' if in_list(k, heartfailure_low) else 'FALSE',
            'O0': r.get('O0', ''),
            'Emax': r.get('Emax', ''),
            'Kappa': r.get('Kappa', ''),
            'Tau': r.get('Tau', ''),
            'n': r.get('n', ''),
            'm': r.get('m', ''),
            'Cmax': r.get('Cmax_used', ''),
            'R2': r.get('R2', '')
        }
        rows.append(row)

    out = pd.DataFrame(rows)

    # Drop known controls if they exist in coefficients and you don't want them listed
    # (Your MATLAB plots excluded some; here we include all provided in coefficients.)

    return out


def main():
    coef_csv = 'hill_coefficients_modified_averaged.csv'
    out_csv = 'hill_modified_risk_table.csv'
    if not os.path.exists(coef_csv):
        raise FileNotFoundError(coef_csv)
    tbl = load_coefficients(coef_csv)
    out = build_flags(tbl)
    # Ensure column order
    cols = ['Drug','Arrhythmia Risk High','Arrhythmia Risk Low','Cardiac Risk High','Cardiac Risk Low',
            'O0','Emax','Kappa','Tau','n','m','Cmax','R2']
    out = out[cols]
    out.to_csv(out_csv, index=False)
    print(f"Wrote updated {out_csv} with {len(out)} rows")


if __name__ == '__main__':
    main()







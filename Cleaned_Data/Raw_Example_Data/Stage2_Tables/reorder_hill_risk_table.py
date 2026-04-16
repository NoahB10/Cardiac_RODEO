"""
Reorder hill_modified_risk_table.csv to match user-specified groupings.

The order (top to bottom) will be the following groups with blank-group separators preserved via a Group index:
1) [Sotalol, Sunitinib (H08), Vandetanib (G11), Epirubicin (B04)]
2) [Cobimetinib (E03), Erlotinib (E09), Daunorubicin (F03), Doxorubicin (G03)]
3) [Amiodarone, Isoproterenol, Dactinomycin, Etomoxir, Plicamycin]
4) [Panobinostat (G07), Ibrutinib (C10)]
5) [Chlorpromazine, Nifedipine]
6) [Gemcitibine]
7) [Vincristine, Vorinostat (B06)]

Any remaining drugs not listed will be appended at the bottom.
"""

import os
import pandas as pd


def normalize(s: str) -> str:
    s = str(s)
    s = s.strip()
    return s


def main():
    csv_path = 'hill_modified_risk_table.csv'
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path)

    # Define groups exactly as provided by the user
    groups = [
        ["Sotalol", "Sunitinib (H08)", "Vandetanib (G11)", "Epirubicin (B04)"],
        ["Cobimetinib (E03)", "Erlotinib (E09)", "Daunorubicin (F03)", "Doxorubicin (G03)"],
        ["Amiodarone", "Isoproterenol", "Dactinomycin", "Etomoxir", "Plicamycin"],
        ["Panobinostat (G07)", "Ibrutinib (C10)"],
        ["Chlorpromazine", "Nifedipine"],
        ["Gemcitibine"],
        ["Vincristine", "Vorinostat (B06)"]
    ]

    # Build a ranking map
    rank = {}
    order = 0
    for g_idx, g in enumerate(groups, start=1):
        for item in g:
            # assign incremental order to preserve group order
            rank[normalize(item)] = order
            order += 1
        # insert a gap marker (not used in CSV; we just keep order contiguous)

    # Compute sort key for each row
    def sort_key(drug):
        drug_norm = normalize(drug)
        return rank.get(drug_norm, 10_000 + hash(drug_norm) % 1000)

    df['_sort_key'] = df['Drug'].map(sort_key)
    df_sorted = df.sort_values(by=['_sort_key', 'Drug'], kind='mergesort').drop(columns=['_sort_key'])

    # Write back in-place
    df_sorted.to_csv(csv_path, index=False)
    print(f"Reordered {csv_path} with {len(df_sorted)} rows.")


if __name__ == '__main__':
    main()







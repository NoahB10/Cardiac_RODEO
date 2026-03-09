"""
Update Paper_Plots notebook to use dynamic dose ratios from raw data
instead of hardcoded [0.5, 1.0, 1.5, 2.0] for 2D plots.
"""
import json

# Reload the original notebook
with open('Paper_Plots_PKPD_Elimination_Surfaces.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# New helper functions to add at the beginning of cell 28
cmax_loading_code = r'''# Load Cmax dictionary for dynamic dose ratio calculation
cmax_df = pd.read_csv(r"C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Cleaned_Data\drug_Cmax.csv")
cmax_dict = {}
for _, row in cmax_df.iterrows():
    key = row['Drug'].lower().replace(' ', '')
    cmax_dict[key] = row['Cmax_uM']

def get_cmax(drug_name):
    """Get Cmax for a drug."""
    key = drug_name.lower().replace(' ', '')
    return cmax_dict.get(key)

def get_dose_ratios_from_raw(xlsx_path, drug_name, cmax):
    """Extract actual dose ratios from raw data."""
    try:
        df = pd.read_excel(xlsx_path, sheet_name=drug_name)
        conc_cols = df.columns[1:]  # Skip time column
        concentrations = []
        for col in conc_cols:
            try:
                c = float(str(col).replace('_', '.'))
                concentrations.append(c)
            except:
                pass
        if concentrations and cmax and cmax > 0:
            return sorted([c / cmax for c in concentrations])
    except:
        pass
    return [0.5, 1.0, 1.5, 2.0]  # Fallback

'''

# Get cell 28
cell = nb['cells'][28]
source = ''.join(cell['source'])

# Check if already modified
if 'get_dose_ratios_from_raw' in source:
    # Remove previously added code to start fresh
    idx = source.find('# Cell 12')
    if idx >= 0:
        source = source[idx:]

# Add helper functions at the top
source = cmax_loading_code + source

# Remove the hardcoded concentrations lines (both O2 and Contractility)
# Pattern: "    # Concentrations to average over\n    concentrations = [0.5, 1.0, 1.5, 2.0]\n    \n"
source = source.replace(
    '    # Concentrations to average over\n    concentrations = [0.5, 1.0, 1.5, 2.0]\n    \n',
    ''
)

# Now add dynamic calculation after each "drug_name = str(row['Drug'])" line
# For O2 section - add after the print statement
o2_insert_after = '''        print(f"\\nProcessing drug {i+1}/{len(heart_damage_true_indices)}: {drug_name}")'''
o2_dynamic_code = '''

        # Get actual dose ratios from raw data for this drug
        cmax = get_cmax(drug_name)
        concentrations = get_dose_ratios_from_raw(o2_xlsx_path, drug_name, cmax)
        print(f"  Using {len(concentrations)} dose ratios: {min(concentrations):.2f} - {max(concentrations):.2f}")'''

# Only replace the first occurrence (O2 section)
if o2_insert_after in source:
    idx = source.find(o2_insert_after)
    # Check if dynamic code already added
    if 'get_dose_ratios_from_raw(o2_xlsx_path' not in source[idx:idx+500]:
        source = source[:idx] + source[idx:].replace(o2_insert_after, o2_insert_after + o2_dynamic_code, 1)

# For Contractility section
contract_insert_after = '''        print(f"\\nProcessing drug {i+1}/{len(heart_damage_true_indices_contractility)}: {drug_name}")'''
contract_dynamic_code = '''

        # Get actual dose ratios from raw data for this drug
        cmax = get_cmax(drug_name)
        concentrations = get_dose_ratios_from_raw(contractility_xlsx_path, drug_name, cmax)
        print(f"  Using {len(concentrations)} dose ratios: {min(concentrations):.2f} - {max(concentrations):.2f}")'''

# Replace the contractility section
if contract_insert_after in source:
    # Find position after O2 section
    o2_end = source.find('CONTRACTILITY HEART DAMAGE DRUGS')
    if o2_end > 0:
        idx = source.find(contract_insert_after, o2_end)
        if idx > 0 and 'get_dose_ratios_from_raw(contractility_xlsx_path' not in source[idx:idx+500]:
            source = source[:idx] + source[idx:].replace(contract_insert_after, contract_insert_after + contract_dynamic_code, 1)

# Convert back to list format for notebook
new_source_lines = []
for i, line in enumerate(source.split('\n')):
    if i < len(source.split('\n')) - 1:
        new_source_lines.append(line + '\n')
    else:
        new_source_lines.append(line)

# Update the cell
nb['cells'][28]['source'] = new_source_lines

# Save the notebook
with open('Paper_Plots_PKPD_Elimination_Surfaces.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

# Verify changes
with open('Paper_Plots_PKPD_Elimination_Surfaces.ipynb', 'r', encoding='utf-8') as f:
    nb_verify = json.load(f)

source_verify = ''.join(nb_verify['cells'][28]['source'])
hardcoded_count = source_verify.count('concentrations = [0.5, 1.0, 1.5, 2.0]')
dynamic_count = source_verify.count('get_dose_ratios_from_raw')

print("Notebook updated!")
print(f"Hardcoded concentrations remaining: {hardcoded_count}")
print(f"Dynamic dose ratio calls: {dynamic_count}")

if hardcoded_count == 0 and dynamic_count >= 2:
    print("SUCCESS: 2D plots will now use actual dose ratios from raw data")
else:
    print("WARNING: Update may be incomplete, please check manually")

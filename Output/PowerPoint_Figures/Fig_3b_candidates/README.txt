Figure 3b Candidate Surfaces - Explanation
===========================================

PURPOSE
-------
These scripts were created to help choose which equation shape(s) to feature
in Figure 3b of the paper. Fig 3b is designated as an "External Panel" in the
figure registry - the user manually places the chosen surface(s) there.

TWO SCRIPTS
-----------

1) generate_surface_gallery.py (root directory)
   - Generates ONE representative 3D surface plot per equation (12 total).
   - For each equation, it tries multiple drugs and picks the one with the
     largest Z-range (most visually interesting, non-flat surface).
   - Prefers O2 response type; falls back to Contractility if O2 is flat.
   - Output: Surface_1.png through Surface_12.png in this folder.
   - Equation ordering:
       Surface 1  = dual_exponential
       Surface 2  = bivariate_gaussian
       Surface 3  = gaussian_hill_hybrid
       Surface 4  = modified_hill_hormesis
       Surface 5  = gaussian_ridge
       Surface 6  = adaptive_response
       Surface 7  = biphasic_response
       Surface 8  = cumulative_exposure
       Surface 9  = recovery_model
       Surface 10 = modified_hill_simple
       Surface 11 = pkpd_elimination
       Surface 12 = hormesis_v0

2) generate_surface_intensities.py (root directory)
   - Focuses on 4 shortlisted equations: Surfaces 1, 5, 11, 12.
   - For each, generates 5 intensity variants using different drugs' O2
     coefficients, selected at the 10th/30th/50th/70th/90th percentiles
     of Z-range across all drugs.
   - Shows how each equation behaves from mild (v1) to intense (v5) response.
   - Output: 20 plots in the intensities/ subfolder.

RENAMING (2026-03-09)
---------------------
The intensity variant files were originally named Surface_X_vY.png (grouped
by equation number). They were renamed to DrugName_Surface_X.png so that
the same drug's surfaces across different equations are grouped together
when sorted alphabetically. This makes it easier to compare how a single
drug looks under different equation models.

Old name format:  Surface_1_v1.png, Surface_1_v2.png, ...
New name format:  Chlorpromazine_Surface_1.png, Doxorubicin_Surface_1.png, ...

The intensity_summary.csv in the intensities/ folder was also updated to
reflect the new filenames. It contains the full mapping:
  Surface number, Equation name, Variant, Drug name, Z_Range, Filename

DRUG-TO-EQUATION MAPPING (intensities/)
----------------------------------------
Amiodarone:     Surface 1 (dual_exponential), Surface 5 (gaussian_ridge)
Chlorpromazine: Surface 1 (dual_exponential), Surface 5 (gaussian_ridge), Surface 11 (pkpd_elimination)
Cobimetinib:    Surface 5 (gaussian_ridge), Surface 11 (pkpd_elimination)
Daunorubicin:   Surface 11 (pkpd_elimination)
Doxorubicin:    Surface 1 (dual_exponential)
Epirubicin:     Surface 12 (hormesis_v0)
Erlotinib:      Surface 12 (hormesis_v0)
Etomoxir:       Surface 12 (hormesis_v0)
Gemcitibine:    Surface 12 (hormesis_v0)
Ibrutinib:      Surface 5 (gaussian_ridge), Surface 11 (pkpd_elimination)
Ibuprofen:      Surface 1 (dual_exponential), Surface 11 (pkpd_elimination)
Mexiletine:     Surface 1 (dual_exponential)
Vandetanib:     Surface 5 (gaussian_ridge)
Vioxx:          Surface 12 (hormesis_v0)

DATA SOURCE
-----------
All coefficients come from: EQN_Coefficients/all_equations_coefficients.xlsx
Each equation has its own sheet. O2 columns use the .1 suffix convention.
Excluded drugs: DMSO, Troglitazone, Troglitarazine.

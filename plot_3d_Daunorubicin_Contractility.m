%% 3D PK-PD Surface with Raw Data Overlay - Daunorubicin Contractility
% Matches the style from Paper_Plots_PKPD_Elimination_Surfaces.ipynb

clear; clc; close all;

%% CONFIGURATION
DRUG_NAME = 'Daunorubicin';
RESPONSE_TYPE = 'Contractility';
REMOVE_R0_OFFSET = true;

% Paths
PROJECT_ROOT = fileparts(mfilename('fullpath'));
COEFF_PATH = fullfile(PROJECT_ROOT, 'EQN_Coefficients', 'all_equations_coefficients.xlsx');
RAW_DATA_PATH = fullfile(PROJECT_ROOT, 'Cleaned_Data', 'Heart_Contractility_Averaged.xlsx');

%% Load Coefficients
fprintf('Loading coefficients for %s - %s...\n', DRUG_NAME, RESPONSE_TYPE);

coeff_table = readtable(COEFF_PATH, 'Sheet', 'pkpd_elimination', 'Range', 'A2');

drug_idx = find(strcmp(coeff_table.Drug, DRUG_NAME));
if isempty(drug_idx)
    error('Drug "%s" not found in coefficients file', DRUG_NAME);
end

% Contractility columns (no suffix)
R0 = coeff_table.R0(drug_idx);
Emax = coeff_table.Emax(drug_idx);
kappa = coeff_table.kappa(drug_idx);
n = coeff_table.n(drug_idx);
m = coeff_table.m(drug_idx);
tau = coeff_table.tau(drug_idx);
k_elim = coeff_table.k_elim(drug_idx);
Cmax = coeff_table.Cmax_used(drug_idx);

fprintf('  R0=%.4f, Emax=%.4f, kappa=%.4f\n', R0, Emax, kappa);
fprintf('  n=%.4f, m=%.4f, tau=%.4f, k_elim=%.4f\n', n, m, tau, k_elim);
fprintf('  Cmax=%.4f uM\n', Cmax);

%% PK-PD Elimination Equation
pkpd_response = @(dose_ratio, time) R0 + Emax * (1 - exp(-kappa * ...
    (dose_ratio .* exp(-k_elim * time)).^n .* (time / tau).^m));

%% Load Raw Data
fprintf('Loading raw data...\n');

raw_table = readtable(RAW_DATA_PATH, 'Sheet', DRUG_NAME);
time_vals = raw_table{:, 1};
var_names = raw_table.Properties.VariableNames(2:end);

raw_times = [];
raw_dose_ratios = [];
raw_responses = [];

for i = 1:length(var_names)
    col_name = var_names{i};
    col_clean = strrep(col_name, 'x', '');
    col_clean = strrep(col_clean, '_', '.');
    conc = str2double(col_clean);

    if ~isnan(conc)
        dose_ratio = conc / Cmax;
        col_data = raw_table{:, i+1};

        for j = 1:length(time_vals)
            if ~isnan(col_data(j))
                raw_times(end+1) = time_vals(j);
                raw_dose_ratios(end+1) = dose_ratio;
                raw_responses(end+1) = col_data(j);
            end
        end
    end
end

fprintf('  Raw data: %d points\n', length(raw_times));
fprintf('  Dose ratio range: %.2f - %.2f\n', min(raw_dose_ratios), max(raw_dose_ratios));

%% Create Surface Grid (extend to cover all raw data)
max_dose_ratio = max(2, ceil(max(raw_dose_ratios)));
dose_ratio_vec = linspace(0, max_dose_ratio, 60);
time_vec = linspace(0, 96, 60);
[T, Dr] = meshgrid(time_vec, dose_ratio_vec);

Response = pkpd_response(Dr, T);

if REMOVE_R0_OFFSET
    Response = Response - R0;
    raw_responses = raw_responses - R0;
end

%% Create 3D Plot
figure('Position', [100, 100, 900, 700], 'Color', 'w');

surf(T, Dr, Response, 'EdgeColor', 'none', 'FaceAlpha', 0.7);
colormap(turbo);
hold on;

vmin = 0;
vmax = max(Response(:));
caxis([vmin, vmax]);

% Plot raw data
scatter3(raw_times, raw_dose_ratios, raw_responses, ...
    25, 'k', 'filled', 'MarkerFaceAlpha', 0.8);

% Labels
xlabel('Time (hours)', 'FontSize', 11);
ylabel('Dose Ratio (C_0/C_{max})', 'FontSize', 11);
if REMOVE_R0_OFFSET
    zlabel('Contractility (R_0 removed)', 'FontSize', 11);
else
    zlabel('Contractility (Amp std)', 'FontSize', 11);
end

title(sprintf('%s - Contractility', DRUG_NAME), 'FontSize', 13, 'FontWeight', 'bold');

% View angle (same as notebook)
view(-158, 25);

% Z-axis limits
z_min = min(0, min(raw_responses));
z_max = max(vmax, max(raw_responses)) * 1.1;
zlim([z_min, z_max]);

% Legend
legend({'Surface', 'Raw Data'}, 'Location', 'northeast');

% Colorbar
c = colorbar;
c.Label.String = 'Contractility';
c.Label.FontSize = 10;

grid on;
box on;
rotate3d on;

fprintf('\nPlot created for %s - Contractility\n', DRUG_NAME);

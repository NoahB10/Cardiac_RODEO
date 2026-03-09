%% 3D PK-PD Surface with Raw Data Overlay
% Matches the style from Paper_Plots_PKPD_Elimination_Surfaces.ipynb
% Interactive MATLAB viewer for Bortezomib (or other drugs)

clear; clc; close all;

%% CONFIGURATION
DRUG_NAME = 'Bortezomib';
RESPONSE_TYPE = 'O2';  % 'O2' or 'Contractility'
REMOVE_R0_OFFSET = true;

% Paths (adjust if needed)
PROJECT_ROOT = fileparts(mfilename('fullpath'));
COEFF_PATH = fullfile(PROJECT_ROOT, 'EQN_Coefficients', 'all_equations_coefficients.xlsx');
O2_DATA_PATH = fullfile(PROJECT_ROOT, 'Cleaned_Data', 'O2_Mean_Averaged.xlsx');
CONTRACTILITY_DATA_PATH = fullfile(PROJECT_ROOT, 'Cleaned_Data', 'Heart_Contractility_Averaged.xlsx');

%% Load Coefficients
fprintf('Loading coefficients for %s - %s...\n', DRUG_NAME, RESPONSE_TYPE);

% Read the pkpd_elimination sheet (header on row 2)
coeff_table = readtable(COEFF_PATH, 'Sheet', 'pkpd_elimination', 'HeaderLines', 1);

% Find the drug row
drug_idx = find(strcmp(coeff_table.Drug, DRUG_NAME));
if isempty(drug_idx)
    error('Drug "%s" not found in coefficients file', DRUG_NAME);
end

% Extract coefficients based on response type
if strcmp(RESPONSE_TYPE, 'O2')
    % O2 columns have '.1' suffix (becomes '_1' in MATLAB)
    R0 = coeff_table.R0_1(drug_idx);
    Emax = coeff_table.Emax_1(drug_idx);
    kappa = coeff_table.kappa_1(drug_idx);
    n = coeff_table.n_1(drug_idx);
    m = coeff_table.m_1(drug_idx);
    tau = coeff_table.tau_1(drug_idx);
    k_elim = coeff_table.k_elim_1(drug_idx);
    Cmax = coeff_table.Cmax_used_1(drug_idx);
else
    % Contractility columns (no suffix)
    R0 = coeff_table.R0(drug_idx);
    Emax = coeff_table.Emax(drug_idx);
    kappa = coeff_table.kappa(drug_idx);
    n = coeff_table.n(drug_idx);
    m = coeff_table.m(drug_idx);
    tau = coeff_table.tau(drug_idx);
    k_elim = coeff_table.k_elim(drug_idx);
    Cmax = coeff_table.Cmax_used(drug_idx);
end

fprintf('  R0=%.4f, Emax=%.4f, kappa=%.4f\n', R0, Emax, kappa);
fprintf('  n=%.4f, m=%.4f, tau=%.4f, k_elim=%.4f\n', n, m, tau, k_elim);
fprintf('  Cmax=%.4f\n', Cmax);

%% PK-PD Elimination Equation
% R(C0, t) = R0 + Emax * (1 - exp(-kappa * (C0/Cmax * exp(-k_elim * t))^n * (t/tau)^m))

pkpd_response = @(dose_ratio, time) R0 + Emax * (1 - exp(-kappa * ...
    (dose_ratio .* exp(-k_elim * time)).^n .* (time / tau).^m));

%% Load Raw Data FIRST (to get dose ratio range)
fprintf('Loading raw data...\n');

if strcmp(RESPONSE_TYPE, 'O2')
    data_path = O2_DATA_PATH;
else
    data_path = CONTRACTILITY_DATA_PATH;
end

raw_table = readtable(data_path, 'Sheet', DRUG_NAME);

% First column is time
time_vals = raw_table{:, 1};

% Get concentration columns (numeric headers)
var_names = raw_table.Properties.VariableNames(2:end);

% Build arrays for 3D scatter
raw_times = [];
raw_dose_ratios = [];
raw_responses = [];

for i = 1:length(var_names)
    col_name = var_names{i};

    % Try to parse concentration from column name
    % MATLAB converts numeric headers like "0.05" to "x0_05"
    col_clean = strrep(col_name, 'x', '');
    col_clean = strrep(col_clean, '_', '.');
    conc = str2double(col_clean);

    if ~isnan(conc)
        dose_ratio = conc / Cmax;
        col_data = raw_table{:, i+1};  % +1 because first col is time

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
max_dose_ratio = max(2, ceil(max(raw_dose_ratios)));  % At least 2, or cover all data
dose_ratio_vec = linspace(0, max_dose_ratio, 60);
time_vec = linspace(0, 96, 60);
[T, Dr] = meshgrid(time_vec, dose_ratio_vec);

% Compute response surface
Response = pkpd_response(Dr, T);

% Remove R0 offset if requested
if REMOVE_R0_OFFSET
    Response = Response - R0;
end

% Remove R0 offset from raw data if requested
if REMOVE_R0_OFFSET
    raw_responses = raw_responses - R0;
end

%% Create 3D Plot
figure('Position', [100, 100, 900, 700], 'Color', 'w');

% Plot surface
surf(T, Dr, Response, 'EdgeColor', 'none', 'FaceAlpha', 0.7);
colormap(turbo);
hold on;

% Color limits
vmin = 0;
vmax = max(Response(:));
caxis([vmin, vmax]);

% Plot all raw data points
scatter3(raw_times, raw_dose_ratios, raw_responses, ...
    25, 'k', 'filled', 'MarkerFaceAlpha', 0.8);

% Labels
xlabel('Time (hours)', 'FontSize', 11);
ylabel('Dose Ratio (C_0/C_{max})', 'FontSize', 11);
if REMOVE_R0_OFFSET
    zlabel([RESPONSE_TYPE ' Response (R_0 removed)'], 'FontSize', 11);
else
    zlabel([RESPONSE_TYPE ' Response'], 'FontSize', 11);
end

title(sprintf('%s - %s', DRUG_NAME, RESPONSE_TYPE), 'FontSize', 13, 'FontWeight', 'bold');

% Set view angle (same as notebook: elev=25, azim=-158)
view(-158, 25);

% Z-axis limits
z_min = min(0, min(raw_responses));
z_max = max(vmax, max(raw_responses)) * 1.1;
zlim([z_min, z_max]);

% Legend
legend({'Surface', 'Raw Data'}, 'Location', 'northeast');

% Colorbar
c = colorbar;
c.Label.String = 'Response';
c.Label.FontSize = 10;

% Grid
grid on;
box on;

% Enable rotation
rotate3d on;

fprintf('\nPlot created. Use mouse to rotate.\n');
fprintf('Press any key to switch response type, or close figure to exit.\n');

%% Interactive: Press key to switch between O2 and Contractility
% (Optional - comment out if not needed)
% waitforbuttonpress;

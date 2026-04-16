function plot_modified_hill(coef_csv)
% Visualize modified Hill toxicity surfaces using the new kappa/tau model.
%
% Input CSV is expected to contain columns:
%   Drug, O0, Emax, Kappa, Tau, n, m, Cmax_used [, ...]
%
% Figures rendered:
%   - Arrhythmia (high/low risk panels)
%   - Heart Failure (high/low)
%   - None (unclassified)
%   - Overview (all drugs)

clearvars -except coef_csv; close all; clc;

%% ---- Locate CSV ----
if nargin < 1 || isempty(coef_csv)
    here = fileparts(mfilename('fullpath'));
    defaultCsv = fullfile(here, 'hill_coefficients_modified.csv');
    if ~isfile(defaultCsv)
        error('Could not find coefficient CSV. Pass the path explicitly.');
    end
    coef_csv = defaultCsv;
end
tbl = readtable(coef_csv);

needed = {'Drug','O0','Emax','Kappa','Tau','n','m'};
if ~all(ismember(needed, tbl.Properties.VariableNames))
    error('Coefficient file must include columns: %s', strjoin(needed, ', '));
end

normalizeName = @(s) regexprep(lower(string(s)), '\s|\(.*?\)', '');
tbl.DrugKey = normalizeName(tbl.Drug);
excludeKeys = normalizeName({'DMSO','Vioxx','Rosiglitazone','Ibuprofen','Troglitazone'});
keepMask = true(height(tbl),1);
for k = 1:numel(excludeKeys)
    keepMask = keepMask & tbl.DrugKey ~= excludeKeys(k);
end
tbl = tbl(keepMask, :);

ratioMax = compute_ratio_max(tbl);

cmaxCol = '';
for cand = {'Cmax_used','Cmax_phys_uM','Cmax_uM'}
    if ismember(cand{1}, tbl.Properties.VariableNames)
        cmaxCol = cand{1};
        break;
    end
end
if isempty(cmaxCol)
    error('Could not locate a Cmax column in %s.', coef_csv);
end

%% ---- Clinical categories ----
arrhythmia_high = normalizeName({ ...
 'Bortezomib', 'Epirubicin', 'Ibrutinib', 'Mexiletine', 'Panobinostat', 'Sotalol', 'Sunitinib', 'Vandetanib' ...
});
arrhythmia_low  = normalizeName({ 'Chlorpromazine', 'Gemcitibine', 'Nifedipine' });

heartfailure_high = normalizeName({ ...
 'Bortezomib', 'Epirubicin', 'Erlotinib', 'Ibuprofen', 'Sotalol', 'Sunitinib', 'Vandetanib', 'Rosiglitazon', ...
 'DOXOrubicin', 'Daunorubicin', 'Cobimetinib' ...
});
heartfailure_low  = normalizeName({ 'Gemcitibine', 'Vincristine', 'Vorinostat' });

none_group = normalizeName({ 'Amiodarone', 'Dactinomycin', 'Etomoxir', 'Isoproterenol', 'Plicamycin', 'Troglitazone' });

%% ---- Build figures ----
idx_arr_high = lookup_drugs(arrhythmia_high, tbl.DrugKey);
idx_arr_low  = lookup_drugs(arrhythmia_low,  tbl.DrugKey);
split_panel_figure(tbl, idx_arr_high, idx_arr_low, "Arrhythmia", cmaxCol, ratioMax);

idx_hf_high = lookup_drugs(heartfailure_high, tbl.DrugKey);
idx_hf_low  = lookup_drugs(heartfailure_low,  tbl.DrugKey);
split_panel_figure(tbl, idx_hf_high, idx_hf_low, "Heart Failure", cmaxCol, ratioMax);

idx_none = lookup_drugs(none_group, tbl.DrugKey);
figure('Color','w','Name','None','NumberTitle','off','Position',[60 60 1400 800]);
plot_grid_in_rect(tbl, idx_none, [0.06 0.08 0.88 0.86], "None", cmaxCol, ratioMax);

figure('Color','w','Name','All Drugs - Overview','NumberTitle','off','Position',[60 60 1600 900]);
plot_grid_in_rect(tbl, (1:height(tbl))', [0.06 0.08 0.88 0.86], "All Drugs - Overview", cmaxCol, ratioMax);

end % main


%% ================= Helpers =================
function idx = lookup_drugs(drugKeys, tblKeys)
    idx = [];
    for i = 1:numel(drugKeys)
        k = drugKeys(i);
        hit = find(tblKeys == k, 1);
        if isempty(hit)
            hit = find(startsWith(tblKeys, k), 1);
        end
        if ~isempty(hit), idx(end+1,1) = hit; end %#ok<AGROW>
    end
    if ~isempty(idx)
        [~, ia] = unique(idx, 'stable');
        idx = idx(ia);
    end
end

function split_panel_figure(tbl, idxHigh, idxLow, figTitle, cmaxCol, ratioMax)
    figure('Color','w','Name',figTitle,'NumberTitle','off','Position',[50 50 1600 900]);
    leftRect  = [0.03 0.06 0.46 0.88];
    rightRect = [0.51 0.06 0.46 0.88];
    plot_grid_in_rect(tbl, idxHigh, leftRect,  figTitle + " - High", cmaxCol, ratioMax);
    plot_grid_in_rect(tbl, idxLow,  rightRect, figTitle + " - Low",  cmaxCol, ratioMax);
end

function plot_grid_in_rect(tbl, idx, rect, titleStr, cmaxCol, ratioMax)
    if isempty(idx)
        annotation(gcf,'textbox',[rect(1) rect(2)+rect(4)/2-0.05 rect(3) 0.1], ...
            'String',[titleStr ' (no entries)'],'HorizontalAlignment','center','EdgeColor','none','FontSize',12,'FontWeight','bold');
        return;
    end

    n = numel(idx);
    nCols = 3; nRows = ceil(n / nCols);
    gap = 0.01;
    cellW = (rect(3) - (nCols+1)*gap) / nCols;
    cellH = (rect(4) - (nRows+1)*gap) / nRows;

    annotation(gcf,'textbox',[rect(1) rect(2)+rect(4)-0.035 rect(3) 0.03], ...
        'String',titleStr,'HorizontalAlignment','center','EdgeColor','none','FontSize',12,'FontWeight','bold');

    p = 1;
    for r = 1:nRows
        for c = 1:nCols
            if p > n, break; end
            i = idx(p);
            axPos = [rect(1) + gap + (c-1)*(cellW+gap), ...
                     rect(2) + rect(4) - (gap + r*cellH + (r-1)*gap) + gap, ...
                     cellW, cellH];
            ax = axes('Position', axPos); %#ok<LAXES>
            render_surface(ax, tbl, i, cmaxCol, ratioMax);
            p = p + 1;
        end
    end
end

function render_surface(ax, tbl, i, cmaxCol, ratioMax)
    Cmax = fetchCmax(tbl, i, cmaxCol);
    t_end = 96;
    t = linspace(0, t_end, 60);
    D_ratio = linspace(0, ratioMax, 60);
    [T, Dr] = meshgrid(t, D_ratio);
    U = Dr; % already normalized

    O0    = tbl.O0(i);
    Emax  = tbl.Emax(i);
    Kappa = max(tbl.Kappa(i), 1e-9);
    Tau   = max(tbl.Tau(i), 1e-9);
    nH    = max(tbl.n(i), 1e-9);
    mH    = max(tbl.m(i), 1e-9);

    frac = 1 - exp(-Kappa .* (U.^nH) .* ((T./Tau).^mH));
    O2 = O0 + Emax .* frac;
    O2 = min(O2, 100);

    surf(ax, T, Dr, O2, 'EdgeColor','none'); view(ax, 40, 28);
    try, colormap(ax, turbo); catch, colormap(ax, parula); end
    drugName = char(tbl.Drug(i));
    title(ax, sprintf('%s (C_{max}=%.2f)', drugName, Cmax), 'Interpreter','none', 'FontSize', 9);
    xlabel(ax,'Time (h)'); ylabel(ax,'Dose/C_{max} (ratio)'); zlabel(ax,'O_2 (%)');
    apply_axes(ax, T, Dr, O2, ratioMax);
end

function Cmax = fetchCmax(tbl, i, cmaxCol)
    Cmax = tbl.(cmaxCol)(i);
    if ~isfinite(Cmax) || Cmax <= 0
        alt = {'Cmax_used','Cmax_phys_uM','Cmax_uM'};
        for k = 1:numel(alt)
            if ismember(alt{k}, tbl.Properties.VariableNames)
                Cmax = tbl.(alt{k})(i);
                if isfinite(Cmax) && Cmax > 0, break; end
            end
        end
    end
    if ~isfinite(Cmax) || Cmax <= 0
        Cmax = 1;
        warning('Cmax missing/invalid for %s, using 1.', string(tbl.Drug(i)));
    end
end

function apply_axes(ax, T, Dr, O2, ratioMax)
    xlim(ax, [0, max(T(:))]);
    ylim(ax, [0, ratioMax]);
    clim(ax, [min(O2(:)), min(100, max(O2(:)))]);
    zlim(ax, [0, 100]);
    grid(ax, 'on');
end

function ratioMax = compute_ratio_max(tbl)
    ratioCandidates = [];
    if ismember('CT50_ratio', tbl.Properties.VariableNames)
        ratioCandidates = [ratioCandidates; tbl.CT50_ratio];
    end
    ratioCandidates = ratioCandidates(isfinite(ratioCandidates) & ratioCandidates > 0);
    if isempty(ratioCandidates)
        ratioMax = 2;
    else
        ratioMax = max(1.2, min(5, max(ratioCandidates) * 1.5));
    end
end

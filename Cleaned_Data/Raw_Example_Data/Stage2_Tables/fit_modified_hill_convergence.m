function fit_modified_hill_convergence(excelFile, cmaxCsv)
% Fit the modified dose-time Hill surface and plot optimizer convergence traces.
%
% Model:
%   O(C,t) = O0 + Emax * (1 - exp(-kappa * ( (C/Cmax)^n ) * ( (t/tau)^m )))
%
% Constraints requested by user:
%   - O0 (baseline O2) bounded between 5% and 25%.
%   - Peak oxygen not expected to exceed ~140%.
%   - Experiment duration limited to 0..96 h.
%
% Outputs a CSV with per-drug parameters and fit diagnostics.
%
% Usage:
%   fit_modified_hill_convergence()                                   % defaults
%   fit_modified_hill_convergence('O2_Mean_Averaged.xlsx','drug_Cmax.csv')

if nargin < 1, excelFile = 'O2_Mean_Averaged.xlsx'; end
if nargin < 2, cmaxCsv   = 'drug_Cmax.csv'; end

% ---- Configuration ----
fitCfg.bounds = struct( ...
    'O0',     [5, 25], ...        % percent oxygen baseline
    'Emax',   [0, 115], ...       % amplitude (kept <= ~140 as per user hint)
    'Kappa',  [1e-6, 1e3], ...    % potency
    'Tau',    [1e-2, 96], ...     % dynamic half-life proxy (hours)
    'n',      [0.5, 6.0], ...     % Hill slope for concentration
    'm',      [0.5, 6.0] ...      % Hill slope for time
);

fitCfg.initial = struct( ...
    'Kappa',  1.0, ...
    'n',      2.0, ...
    'm',      2.0 ...
);

% ---- Load Cmax reference ----
CmaxTbl = readtable(cmaxCsv);
normKey = @(s) regexprep(lower(string(s)), '\s|\(.*?\)', '');
CmaxTbl.DrugKey = normKey(CmaxTbl.Drug);

% ---- Sheet list & skips ----
[~, sheetNames] = xlsfinfo(excelFile);
skipSheets = lower(string({'All_Drugs','All_Drugs Smoothed','Smoothed All Data', ...
                           'Smoothed_All_Data','All Data','AllData'}));
excludeKeys = normKey(string({'DMSO','Vioxx','Rosiglitazone','Ibuprofen','Troglitazone'}));

Results = table('Size',[0 14],'VariableTypes', ...
    {'string','double','double','double','double','double','double','double','double','double','double','double','double','double'}, ...
    'VariableNames', {'Drug','O0','Emax','Kappa','Tau','n','m','Cmax_used','CT50_at_tau','CT50_ratio','N_points','SSE','RMSE','R2'});

paramNames = {'O0','Emax','Kappa','Tau','n','m'};

for s = 1:numel(sheetNames)
    sh = string(sheetNames{s});
    if any(lower(sh) == skipSheets), continue; end

    % ---------- Read and reshape (wide -> long) ----------
    try
        Traw = readtable(excelFile, 'Sheet', sh, 'PreserveVariableNames', true);
    catch ME
        warning('Skipping "%s": %s', sh, ME.message);
        continue;
    end
    if isempty(Traw) || width(Traw) < 2
        warning('Sheet "%s": insufficient columns; skipping.', sh);
        continue;
    end

    tcol = toNum(Traw{:,1});
    varNames = string(Traw.Properties.VariableNames);

    Time = []; Conc = []; O2 = [];
    for c = 2:width(Traw)
        concVal = parseConc(varNames(c));
        if isnan(concVal), continue; end
        y = toNum(Traw{:,c});
        nrows = numel(tcol);
        Time = [Time; tcol(:)];
        Conc = [Conc; repmat(concVal, nrows, 1)];
        O2   = [O2; y(:)];
    end

    % ---------- Clean/filter ----------
    ok = isfinite(Time) & isfinite(Conc) & isfinite(O2);
    ok = ok & (Time >= 0) & (Time <= 96) & (O2 < 200);
    Time = Time(ok); Conc = Conc(ok); O2 = O2(ok);

    if numel(O2) < 25
        warning('"%s": not enough clean points; skipping.', sh);
        continue;
    end

    % ---------- Lookup Cmax ----------
    key = normKey(sh);
    if any(strcmpi(key, excludeKeys))
        warning('Skipping "%s": excluded control/drug.', sh);
        continue;
    end
    idx = strcmpi(CmaxTbl.DrugKey, key);
    if ~any(idx)
        core = regexprep(key,'\(.*?\)',''); core = strtrim(core);
        idx = strcmpi(CmaxTbl.DrugKey, core) | startsWith(CmaxTbl.DrugKey, core);
    end

    if any(idx) && isfinite(CmaxTbl.Cmax_uM(find(idx,1,'first')))
        Cmax = CmaxTbl.Cmax_uM(find(idx,1,'first'));
    else
        Cmax = max(Conc);
        warning('"%s": Cmax missing; using data-derived Cmax=%g.', sh, Cmax);
    end
    if ~isfinite(Cmax) || Cmax <= 0
        warning('"%s": invalid Cmax; skipping.', sh);
        continue;
    end

    % ---------- Prepare fitting ----------
    x = Conc ./ Cmax;
    X = [x(:), Time(:)];
    y = O2(:);

    bounds = fitCfg.bounds;

    O0_0 = median(y);
    O0_0 = min(max(O0_0, bounds.O0(1)), bounds.O0(2));

    ymax = max(y);
    Emax0 = max(10, ymax - O0_0);
    Emax0 = min(max(Emax0, bounds.Emax(1)), bounds.Emax(2));

    Kappa0 = fitCfg.initial.Kappa;
    Tau0 = median(Time(Time > 0));
    if isempty(Tau0), Tau0 = 1; end
    Tau0 = min(max(Tau0, bounds.Tau(1)), bounds.Tau(2));

    n0 = fitCfg.initial.n;
    m0 = fitCfg.initial.m;

    p0 = [O0_0, Emax0, Kappa0, Tau0, n0, m0];

    lb = [bounds.O0(1), bounds.Emax(1), bounds.Kappa(1), bounds.Tau(1), bounds.n(1), bounds.m(1)];
    ub = [bounds.O0(2), bounds.Emax(2), bounds.Kappa(2), bounds.Tau(2), bounds.n(2), bounds.m(2)];

    % ---------- Fit ----------
    iterHistory.params = [];
    iterHistory.resnorm = [];
    iterHistory.stageBreaks = [];

    optsCoarse = optimoptions('lsqcurvefit','Display','off','MaxIterations',800, ...
        'FunctionTolerance',1e-9,'StepTolerance',1e-8,'OutputFcn', @recordIteration);
    [pFit, resnormCoarse] = lsqcurvefit(@(p,XX) hill_modified_predict(XX,p), p0, X, y, lb, ub, optsCoarse);
    iterHistory.stageBreaks(end+1) = size(iterHistory.params,1);

    p0_refined = min(max(pFit, lb), ub); % re-clamp within bounds
    optsRefined = optimoptions(optsCoarse, ...
        'MaxIterations',1600, ...
        'FunctionTolerance',1e-12, ...
        'StepTolerance',1e-12, ...
        'OptimalityTolerance',1e-12, ...
        'FiniteDifferenceType','central', ...
        'FiniteDifferenceStepSize',1e-6, ...
        'OutputFcn', @recordIteration);
    [pFitRefined, resnormRefined] = lsqcurvefit(@(p,XX) hill_modified_predict(XX,p), p0_refined, X, y, lb, ub, optsRefined);
    iterHistory.stageBreaks(end+1) = size(iterHistory.params,1);

    deltaVec = pFitRefined - pFit;
    fprintf('Refinement %s: ||Δp||₂=%.3g, max|Δp|=%.3g, resnorm %.3g→%.3g\n', sh, norm(deltaVec), max(abs(deltaVec)), resnormCoarse, resnormRefined);
    pFit = pFitRefined;

    % ---------- Metrics ----------
    yhat = hill_modified_predict(X, pFit);
    SSE  = sum((y - yhat).^2);
    RMSE = sqrt(mean((y - yhat).^2));
    SSY  = sum((y - mean(y)).^2);
    R2   = 1 - SSE/max(SSY, eps);

    % Derived TC50 evaluated at t = tau (optional interpretability)
    kappa = max(pFit(3), bounds.Kappa(1));
    tau   = max(pFit(4), bounds.Tau(1));
    nFit  = max(pFit(5), bounds.n(1));
    CT50_tau = Cmax * (log(2) / max(kappa, eps))^(1/nFit);

    CT50_ratio = CT50_tau / max(Cmax, eps);

    Results = [Results; {
        sh, pFit(1), pFit(2), pFit(3), pFit(4), pFit(5), pFit(6), ...
        Cmax, CT50_tau, CT50_ratio, numel(y), SSE, RMSE, R2
    }];

    % ---------- Convergence diagnostics ----------
    if ~isempty(iterHistory.params)
        plot_convergence_metrics(sh, iterHistory, paramNames);
    end
end

outFile = 'hill_coefficients_modified.csv';
writetable(Results, outFile);
fprintf('Saved modified coefficients to %s\n', outFile);

    function stop = recordIteration(params, optimValues, state)
    % Track parameter/residual evolution for lsqcurvefit iterations.
        stop = false;
        switch state
            case {'init','iter','done'}
                iterHistory.params(end+1,:) = params(:).';
                if isfield(optimValues, 'resnorm')
                    iterHistory.resnorm(end+1,1) = optimValues.resnorm;
                else
                    iterHistory.resnorm(end+1,1) = NaN;
                end
        end
    end

end % main


function plot_convergence_metrics(drugLabel, iterHistory, paramNames)
% Visualize iteration-to-iteration parameter and residual convergence.
    figure('Color','w','Name',sprintf('%s - Modified Hill convergence', drugLabel), ...
        'NumberTitle','off','Position',[90 90 900 600]);

    iterIdx = 1:size(iterHistory.params,1);
    stageBreaks = [];
    if isfield(iterHistory,'stageBreaks')
        stageBreaks = iterHistory.stageBreaks;
    end

    ax1 = subplot(2,1,1);
    plot(iterIdx, iterHistory.params, '-o','LineWidth',1.1);
    grid on;
    xlabel('Iteration');
    ylabel('Parameter value');
    title(sprintf('%s parameter evolution', drugLabel), 'Interpreter','none');
    legend(paramNames, 'Location','bestoutside','Interpreter','tex');
    addStageMarkers(ax1, stageBreaks);

    ax2 = subplot(2,1,2);
    resvals = iterHistory.resnorm;
    resvals(resvals <= 0 | isnan(resvals)) = eps;
    plot(iterIdx, resvals, '-o','LineWidth',1.1);
    grid on;
    set(gca,'YScale','log');
    xlabel('Iteration');
    ylabel('Residual sum of squares');
    title('Residual norm per iteration');
    addStageMarkers(ax2, stageBreaks);
end

function addStageMarkers(ax, breaks)
    if isempty(breaks)
        return;
    end
    total = breaks(end);
    markers = breaks(1:end-1);
    for k = 1:numel(markers)
        if markers(k) >= total
            continue;
        end
        xline(ax, markers(k) + 0.5, ':', sprintf('stage %d', k+1), ...
            'LabelVerticalAlignment','bottom', 'LabelOrientation','horizontal', ...
            'LineWidth',1.0, 'Color',[0.4 0.4 0.4]);
    end
end


%% ===== Helpers =====
function y = hill_modified_predict(X, p)
% X(:,1) = normalized concentration, X(:,2) = time (hours)
% p = [O0, Emax, Kappa, Tau, n, m]
O0    = p(1);
Emax  = p(2);
Kappa = max(p(3), 1e-9);
Tau   = max(p(4), 1e-9);
n     = p(5);
m     = p(6);

x = X(:,1);
t = max(X(:,2), 0);
frac = 1 - exp(-Kappa .* (x.^n) .* ((t./Tau).^m));
y = O0 + Emax .* frac;
y = min(y, 140); % clip to expected physiological ceiling
end

function v = toNum(v)
    if istable(v), v = table2array(v); end
    if iscell(v), v = str2double(string(v)); end
    if isstring(v) || ischar(v), v = str2double(string(v)); end
    v = double(v);
end

function cval = parseConc(vname)
    v = string(vname);
    v = strrep(v,'_','.');
    v = regexprep(v,'[^\d\.]+',' ');
    tok = regexp(v,'(\d+\.?\d*)','match','once');
    if isempty(tok), cval = NaN; else, cval = str2double(tok); end
end

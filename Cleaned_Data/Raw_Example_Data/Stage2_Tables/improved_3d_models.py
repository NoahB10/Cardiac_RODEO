"""
Improved 3D Pharmacodynamic Models for Organoid Drug Screening

This script implements enhanced models that better capture the complex dynamics
of organoid responses to drugs, including:
- Threshold effects (no response until certain concentration/time)
- Logistic decay for death/toxicity processes
- Time-delayed effects
- Concentration-time interactions

Author: Generated for organoid drug screening analysis
Date: 2024
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D
import os
import glob
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def load_drug_data(drug_folder, cmax_dict, response_type='O2_mean'):
    """
    Load time-concentration-response data for a drug.
    
    Parameters:
    -----------
    drug_folder : str
        Path to the drug folder containing CSV files
    cmax_dict : dict
        Dictionary mapping drug names to their Cmax values
    response_type : str
        Type of response data to load ('O2_mean' or 'Amp_std')
    
    Returns:
    --------
    time_array : np.array
        Array of time points
    concentration_array : np.array
        Array of concentrations (normalized by Cmax)
    response_array : np.array
        Array of response values
    drug_name : str
        Name of the drug
    """
    drug_name = Path(drug_folder).name
    
    # Handle drug name variations for Cmax lookup
    cmax_key = drug_name
    if drug_name not in cmax_dict:
        cmax_key = drug_name.split('(')[0].strip()
        if cmax_key not in cmax_dict:
            variations = {
                'DOXOrubicin': 'DOXOrubicin',
                'Doxorubicin (G03)': 'DOXOrubicin',
                'Bortezomib (A09)': 'Bortezomib',
                'Cobimetinib (E03)': 'Cobimetinib',
                'Erlotinib (E09)': 'Erlotinib',
                'Epirubicin (B04)': 'Epirubicin',
                'Ibrutinib (C10)': 'Ibrutinib',
                'Panobinostat (G07)': 'Panobinostat',
                'Sunitinib (H08)': 'Sunitinib',
                'Vandetanib (G11)': 'Vandetanib',
                'Vorinostat (B06)': 'Vorinostat',
                'Daunorubicin (F03)': 'Daunorubicin'
            }
            cmax_key = variations.get(drug_name, cmax_key)
    
    if cmax_key not in cmax_dict:
        return None, None, None, None
    
    cmax = cmax_dict[cmax_key]
    
    # Load the CSV file
    csv_file = os.path.join(drug_folder, f'{response_type}.csv')
    if not os.path.exists(csv_file):
        return None, None, None, None
    
    df = pd.read_csv(csv_file, index_col=0)
    
    # Extract time points
    time_points = []
    valid_indices = []
    for idx in df.index:
        try:
            tp = float(idx)
            time_points.append(tp)
            valid_indices.append(idx)
        except (ValueError, TypeError):
            continue
    
    if len(time_points) == 0:
        return None, None, None, None
    
    time_points = np.array(time_points)
    time_to_idx = {tp: valid_indices[i] for i, tp in enumerate(time_points)}
    df = df.loc[valid_indices]
    
    # Extract concentrations and responses
    concentrations = []
    responses = []
    times = []
    
    for col in df.columns:
        try:
            conc = float(col)
            if np.isnan(conc) or conc < 0:
                continue
                
            # Normalize concentration by Cmax
            conc_normalized = conc / cmax if cmax > 0 else conc
            
            for time in time_points:
                idx_key = time_to_idx[time]
                try:
                    response_val = df.loc[idx_key, col]
                    if pd.notna(response_val) and response_val != '':
                        try:
                            times.append(float(time))
                            concentrations.append(conc_normalized)
                            responses.append(float(response_val))
                        except (ValueError, TypeError):
                            continue
                except (KeyError, IndexError):
                    continue
        except (ValueError, TypeError):
            continue
    
    if len(times) == 0:
        return None, None, None, None
    
    return np.array(times), np.array(concentrations), np.array(responses), drug_name


# ============================================================================
# IMPROVED MODEL EQUATIONS
# ============================================================================

def model_logistic_decay(params, t, c):
    """
    Model 1: Logistic Decay Model (Best for organoid death/toxicity)
    
    R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * [1 / (1 + exp(k*(t - t50)))]
    
    This model captures:
    - Sigmoidal concentration-response (Hill equation)
    - Logistic time-dependent decay (more realistic than exponential for death processes)
    - t50: time at which response reaches 50% of its maximum change
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k, t50) - model parameters
    t : np.array
        Time array (hours)
    c : np.array
        Normalized concentration array (C/Cmax)
    
    Returns:
    --------
    response : np.array
        Predicted response values
    """
    R0, Rmax, EC50, n, k, t50 = params
    
    # Hill equation component (concentration-dependent)
    hill_component = (c**n) / (EC50**n + c**n)
    
    # Logistic decay component (time-dependent)
    # k > 0: decay over time, k < 0: growth over time
    logistic_component = 1.0 / (1.0 + np.exp(k * (t - t50)))
    
    # Combined model
    response = R0 + (Rmax - R0) * hill_component * logistic_component
    
    return response


def model_threshold_logistic(params, t, c):
    """
    Model 2: Threshold + Logistic Decay Model
    
    R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * [1 / (1 + exp(k*(t - t50)))] * H(C - Cthresh)
    
    Where H is Heaviside step function (threshold effect)
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k, t50, Cthresh) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    """
    R0, Rmax, EC50, n, k, t50, Cthresh = params
    
    hill_component = (c**n) / (EC50**n + c**n)
    logistic_component = 1.0 / (1.0 + np.exp(k * (t - t50)))
    
    # Threshold: no effect below Cthresh
    threshold = np.where(c >= Cthresh, 1.0, 0.0)
    
    response = R0 + (Rmax - R0) * hill_component * logistic_component * threshold
    
    return response


def model_interactive_response_surface(params, t, c):
    """
    Model 3: Interactive Response Surface Model (Non-separable)
    
    R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * 
             [1 / (1 + exp(k_t*(t - t50) + k_c*c + k_interaction*t*c))]
    
    This model allows concentration-time interactions (non-separable).
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k_t, t50, k_c, k_interaction) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    """
    R0, Rmax, EC50, n, k_t, t50, k_c, k_interaction = params
    
    hill_component = (c**n) / (EC50**n + c**n)
    
    # Interactive time-concentration component
    interactive_component = 1.0 / (1.0 + np.exp(k_t * (t - t50) + k_c * c + k_interaction * t * c))
    
    response = R0 + (Rmax - R0) * hill_component * interactive_component
    
    return response


def model_delayed_logistic(params, t, c):
    """
    Model 4: Delayed Onset + Logistic Decay Model
    
    R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * 
             [1 / (1 + exp(k*(t - t50 - t_delay))) * H(t - t_delay)]
    
    Models delayed onset of effects after drug administration.
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k, t50, t_delay) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    """
    R0, Rmax, EC50, n, k, t50, t_delay = params
    
    hill_component = (c**n) / (EC50**n + c**n)
    
    # Delayed logistic decay
    logistic_component = 1.0 / (1.0 + np.exp(k * (t - t50 - t_delay)))
    
    # Delay threshold: no effect before t_delay
    delay_threshold = np.where(t >= t_delay, 1.0, 0.0)
    
    response = R0 + (Rmax - R0) * hill_component * logistic_component * delay_threshold
    
    return response


def model_weibull_survival(params, t, c):
    """
    Model 5: Weibull Survival Model (Common in toxicity studies)
    
    R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * exp(-(t/λ)^k * (1 + α*c))
    
    Where λ is scale parameter, k is shape parameter, α is concentration modifier
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, lambda_scale, k_shape, alpha) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    """
    R0, Rmax, EC50, n, lambda_scale, k_shape, alpha = params
    
    hill_component = (c**n) / (EC50**n + c**n)
    
    # Weibull survival function with concentration-dependent rate
    weibull_component = np.exp(-((t / lambda_scale) ** k_shape) * (1 + alpha * c))
    
    response = R0 + (Rmax - R0) * hill_component * weibull_component
    
    return response


# ============================================================================
# FITTING FUNCTIONS
# ============================================================================

def fit_model_robust(time_data, conc_data, response_data, model_func, 
                     method='curve_fit', bounds=None, initial_guess=None):
    """
    Robust fitting function that tries multiple methods.
    
    Parameters:
    -----------
    time_data : np.array
        Time points
    conc_data : np.array
        Concentrations
    response_data : np.array
        Response values
    model_func : function
        Model function to fit
    method : str
        'curve_fit' or 'differential_evolution'
    bounds : tuple of tuples, optional
        Parameter bounds
    initial_guess : tuple, optional
        Initial parameter guess
    
    Returns:
    --------
    popt : np.array or None
        Optimized parameters
    pcov : np.array or None
        Parameter covariance matrix
    """
    def model_wrapper(t_c_data, *params):
        t, c = t_c_data
        return model_func(params, t, c)
    
    def objective(params):
        """Objective function for optimization"""
        try:
            pred = model_func(params, time_data, conc_data)
            # Use robust error metric
            errors = np.abs(response_data - pred)
            return np.sum(errors**2) + 1e-10 * np.sum(np.abs(params))
        except:
            return 1e10
    
    # Default bounds based on model
    if bounds is None:
        if model_func == model_logistic_decay:
            # (R0, Rmax, EC50, n, k, t50)
            bounds = ([0, 0, 0, 0.1, -1, 0], 
                     [np.inf, np.inf, 10, 10, 1, np.max(time_data)*2])
        elif model_func == model_threshold_logistic:
            # (R0, Rmax, EC50, n, k, t50, Cthresh)
            bounds = ([0, 0, 0, 0.1, -1, 0, 0], 
                     [np.inf, np.inf, 10, 10, 1, np.max(time_data)*2, 1])
        elif model_func == model_interactive_response_surface:
            # (R0, Rmax, EC50, n, k_t, t50, k_c, k_interaction)
            bounds = ([0, 0, 0, 0.1, -1, 0, -1, -1], 
                     [np.inf, np.inf, 10, 10, 1, np.max(time_data)*2, 1, 1])
        elif model_func == model_delayed_logistic:
            # (R0, Rmax, EC50, n, k, t50, t_delay)
            bounds = ([0, 0, 0, 0.1, -1, 0, 0], 
                     [np.inf, np.inf, 10, 10, 1, np.max(time_data)*2, np.max(time_data)])
        elif model_func == model_weibull_survival:
            # (R0, Rmax, EC50, n, lambda_scale, k_shape, alpha)
            bounds = ([0, 0, 0, 0.1, 1, 0.1, -1], 
                     [np.inf, np.inf, 10, 10, np.max(time_data)*5, 10, 1])
        else:
            bounds = ([0]*len(initial_guess) if initial_guess else [0]*6, 
                     [np.inf]*len(initial_guess) if initial_guess else [np.inf]*6)
    
    # Default initial guess
    if initial_guess is None:
        R0_guess = np.percentile(response_data, 10)
        Rmax_guess = np.percentile(response_data, 90)
        EC50_guess = np.median(conc_data) if len(conc_data) > 0 else 0.1
        n_guess = 1.0
        k_guess = 0.01
        
        if model_func == model_logistic_decay:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, k_guess, np.median(time_data))
        elif model_func == model_threshold_logistic:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, k_guess, 
                           np.median(time_data), 0.01)
        elif model_func == model_interactive_response_surface:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, k_guess, 
                           np.median(time_data), 0.01, 0.001)
        elif model_func == model_delayed_logistic:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, k_guess, 
                           np.median(time_data), 5.0)
        elif model_func == model_weibull_survival:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, 
                           np.median(time_data), 2.0, 0.1)
    
    if method == 'differential_evolution':
        try:
            result = differential_evolution(
                objective,
                bounds,
                maxiter=1000,
                popsize=15,
                seed=42,
                atol=1e-6
            )
            if result.success:
                popt = result.x
                # Estimate covariance (approximate)
                pcov = np.eye(len(popt)) * 0.01
                return popt, pcov
        except:
            pass
    
    # Fallback to curve_fit
    try:
        popt, pcov = curve_fit(
            model_wrapper,
            (time_data, conc_data),
            response_data,
            p0=initial_guess,
            bounds=bounds,
            maxfev=10000,
            method='trf'  # Trust Region Reflective algorithm
        )
        return popt, pcov
    except Exception as e:
        print(f"Fitting failed: {e}")
        return None, None


def calculate_model_metrics(response_data, predicted, model_name="Model"):
    """
    Calculate comprehensive model fit metrics.
    
    Parameters:
    -----------
    response_data : np.array
        Actual response values
    predicted : np.array
        Predicted response values
    model_name : str
        Name of the model
    
    Returns:
    --------
    metrics : dict
        Dictionary of metrics
    """
    # Remove NaN/inf values
    valid_mask = np.isfinite(response_data) & np.isfinite(predicted)
    if np.sum(valid_mask) == 0:
        return None
    
    y_true = response_data[valid_mask]
    y_pred = predicted[valid_mask]
    
    # R-squared
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    # Mean Absolute Error
    mae = np.mean(np.abs(y_true - y_pred))
    
    # Root Mean Squared Error
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # Mean Absolute Percentage Error
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
    
    # AIC (Akaike Information Criterion) - approximate
    n = len(y_true)
    k = len(y_pred)  # Approximate
    aic = n * np.log(ss_res / n) + 2 * k
    
    metrics = {
        'model': model_name,
        'r_squared': r_squared,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'aic': aic,
        'n_points': n
    }
    
    return metrics


# ============================================================================
# VISUALIZATION
# ============================================================================

def visualize_3d_model_improved(time_data, conc_data, response_data, 
                                model_func, params, drug_name, response_type, 
                                save_path=None):
    """
    Create enhanced 3D visualization of the model and data.
    """
    # Create grid for surface plotting
    t_min, t_max = time_data.min(), time_data.max()
    c_min, c_max = conc_data.min(), conc_data.max()
    
    t_grid = np.linspace(t_min, t_max, 50)
    c_grid = np.linspace(c_min, c_max, 50)
    T_grid, C_grid = np.meshgrid(t_grid, c_grid)
    
    # Predict response on grid
    R_grid = model_func(params, T_grid, C_grid)
    
    # Calculate metrics
    y_pred = model_func(params, time_data, conc_data)
    metrics = calculate_model_metrics(response_data, y_pred, "Model")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(18, 6))
    
    # 3D Surface Plot
    ax1 = fig.add_subplot(131, projection='3d')
    surf = ax1.plot_surface(T_grid, C_grid, R_grid, alpha=0.7, cmap='viridis',
                           linewidth=0, antialiased=True)
    ax1.scatter(time_data, conc_data, response_data, c='red', s=20, 
               alpha=0.6, label='Data')
    ax1.set_xlabel('Time (hours)', fontsize=10)
    ax1.set_ylabel('Concentration (C/Cmax)', fontsize=10)
    ax1.set_zlabel(f'{response_type} Response', fontsize=10)
    title = f'{drug_name} - 3D Model\n'
    if metrics:
        title += f'R² = {metrics["r_squared"]:.3f}'
    ax1.set_title(title, fontsize=11)
    plt.colorbar(surf, ax=ax1, shrink=0.5, aspect=5)
    
    # Contour Plot
    ax2 = fig.add_subplot(132)
    contour = ax2.contourf(T_grid, C_grid, R_grid, levels=20, cmap='viridis')
    scatter = ax2.scatter(time_data, conc_data, c=response_data, s=30, 
                         cmap='viridis', edgecolors='black', linewidths=0.5,
                         vmin=response_data.min(), vmax=response_data.max())
    ax2.set_xlabel('Time (hours)', fontsize=10)
    ax2.set_ylabel('Concentration (C/Cmax)', fontsize=10)
    ax2.set_title(f'{drug_name} - Contour Map', fontsize=11)
    plt.colorbar(scatter, ax=ax2, label='Response')
    
    # Time slices - Concentration-Response curves at different times
    ax3 = fig.add_subplot(133)
    unique_times = np.unique(time_data)
    colors = plt.cm.viridis(np.linspace(0, 1, len(unique_times)))
    
    # Plot data points
    for i, t in enumerate(unique_times[:10]):  # Show first 10 time points
        mask = time_data == t
        if np.sum(mask) > 0:
            ax3.scatter(conc_data[mask], response_data[mask], 
                       label=f't={t:.0f}h', alpha=0.6, c=[colors[i]], s=30)
    
    # Plot model predictions at selected time points
    selected_times = [unique_times[0], 
                     unique_times[len(unique_times)//2] if len(unique_times) > 1 else unique_times[0],
                     unique_times[-1] if len(unique_times) > 1 else unique_times[0]]
    
    for i, t in enumerate(selected_times):
        c_pred = np.linspace(c_min, c_max, 100)
        r_pred = model_func(params, np.full(100, t), c_pred)
        ax3.plot(c_pred, r_pred, '--', color=colors[i*len(colors)//3], 
                linewidth=2, label=f'Model t={t:.0f}h')
    
    ax3.set_xlabel('Concentration (C/Cmax)', fontsize=10)
    ax3.set_ylabel(f'{response_type} Response', fontsize=10)
    ax3.set_title('Concentration-Response Curves', fontsize=11)
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.close()
    
    return metrics


def main():
    """
    Main function to fit multiple models and compare them.
    """
    # Load Cmax data
    cmax_file = r'c:\Users\NoahB\Documents\MATLAB\drug_Cmax.csv'
    cmax_df = pd.read_csv(cmax_file)
    cmax_dict = dict(zip(cmax_df['Drug'], cmax_df['Cmax_uM']))
    
    # Get all drug folders
    base_dir = '.'
    drug_folders = [d for d in os.listdir(base_dir) 
                   if os.path.isdir(os.path.join(base_dir, d)) 
                   and d not in ['__pycache__', 'model_visualizations']]
    
    # Define models to test
    models = {
        'Logistic_Decay': model_logistic_decay,
        'Threshold_Logistic': model_threshold_logistic,
        'Interactive_Surface': model_interactive_response_surface,
        'Delayed_Logistic': model_delayed_logistic,
        'Weibull_Survival': model_weibull_survival
    }
    
    # Store results
    all_results = []
    
    # Process each drug
    for drug_folder in drug_folders:
        drug_path = os.path.join(base_dir, drug_folder)
        drug_name = Path(drug_folder).name
        
        print(f"\n{'='*60}")
        print(f"Processing {drug_name}")
        print(f"{'='*60}")
        
        # Try both response types
        for response_type in ['O2_mean', 'Amp_std']:
            print(f"\n  {response_type}:")
            
            # Load data
            time_data, conc_data, response_data, name = load_drug_data(
                drug_path, cmax_dict, response_type
            )
            
            if time_data is None or len(time_data) < 10:
                print(f"    Insufficient data, skipping...")
                continue
            
            # Test each model
            best_model = None
            best_r2 = -np.inf
            best_params = None
            best_metrics = None
            
            for model_name, model_func in models.items():
                try:
                    print(f"    Fitting {model_name}...", end=' ')
                    popt, pcov = fit_model_robust(
                        time_data, conc_data, response_data,
                        model_func, method='curve_fit'
                    )
                    
                    if popt is not None:
                        # Calculate metrics
                        y_pred = model_func(popt, time_data, conc_data)
                        metrics = calculate_model_metrics(response_data, y_pred, model_name)
                        
                        if metrics and metrics['r_squared'] > best_r2:
                            best_r2 = metrics['r_squared']
                            best_model = model_name
                            best_params = popt
                            best_metrics = metrics
                        
                        print(f"R² = {metrics['r_squared']:.3f}" if metrics else "Failed")
                    else:
                        print("Failed")
                except Exception as e:
                    print(f"Error: {e}")
                    continue
            
            if best_model:
                print(f"\n    Best model: {best_model} (R² = {best_r2:.3f})")
                
                # Store results
                all_results.append({
                    'drug': drug_name,
                    'response_type': response_type,
                    'best_model': best_model,
                    'r_squared': best_r2,
                    'mae': best_metrics['mae'] if best_metrics else None,
                    'rmse': best_metrics['rmse'] if best_metrics else None,
                    'n_points': best_metrics['n_points'] if best_metrics else len(time_data),
                    'params': best_params
                })
                
                # Visualize best model
                os.makedirs('model_visualizations_improved', exist_ok=True)
                save_path = f'model_visualizations_improved/{drug_name}_{response_type}_{best_model}.png'
                visualize_3d_model_improved(
                    time_data, conc_data, response_data,
                    models[best_model], best_params,
                    drug_name, response_type, save_path
                )
    
    # Save summary
    summary_df = pd.DataFrame(all_results)
    summary_df.to_csv('model_comparison_summary.csv', index=False)
    print(f"\n{'='*60}")
    print(f"Summary saved to model_comparison_summary.csv")
    print(f"Total models fitted: {len(all_results)}")
    print(f"\nBest models summary:")
    print(summary_df.groupby('best_model')['r_squared'].agg(['count', 'mean', 'std']))


if __name__ == "__main__":
    main()








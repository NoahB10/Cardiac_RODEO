"""
3D Pharmacodynamic Modeling for Organoid Drug Screening Data

This script models the relationship between time, concentration, and response (O2 or Amplitude)
for drug screening experiments on organoids. The model accounts for:
- Concentration-dependent dose-response relationships
- Time-dependent kinetic effects
- Normalization by Cmax for cross-drug comparison

Author: Generated for organoid drug screening analysis
Date: 2024
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D
import os
import glob
from pathlib import Path


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
        # Try removing parenthetical parts (e.g., "Troglitazone" from "Troglitazone")
        cmax_key = drug_name.split('(')[0].strip()
        if cmax_key not in cmax_dict:
            # Try common variations
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
        print(f"Warning: Cmax not found for {drug_name}, skipping...")
        return None, None, None, None
    
    cmax = cmax_dict[cmax_key]
    
    # Load the CSV file
    csv_file = os.path.join(drug_folder, f'{response_type}.csv')
    if not os.path.exists(csv_file):
        print(f"Warning: {csv_file} not found")
        return None, None, None, None
    
    df = pd.read_csv(csv_file, index_col=0)
    
    # Extract time points (first column as index)
    # Filter out non-numeric indices (like 'baseline')
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
    # Create a mapping from float time to original index
    time_to_idx = {tp: valid_indices[i] for i, tp in enumerate(time_points)}
    
    # Filter dataframe to only include numeric indices
    df = df.loc[valid_indices]
    
    # Extract concentrations (column headers)
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
                # Use the original index value to access dataframe
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


def model_3d_hill_exponential_decay(params, t, c):
    """
    3D Pharmacodynamic Model: Hill Equation with Time-Dependent Exponential Decay
    
    R(t,C) = R0 + (Rmax - R0) * [C^n / (EC50^n + C^n)] * exp(-k*t)
    
    Where:
    - R0: baseline response
    - Rmax: maximum response
    - EC50: concentration at half-maximal effect
    - n: Hill coefficient (sigmoidicity)
    - k: time decay constant
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array (C/Cmax)
    
    Returns:
    --------
    response : np.array
        Predicted response values
    """
    R0, Rmax, EC50, n, k = params
    
    # Hill equation component (concentration-dependent)
    hill_component = (c**n) / (EC50**n + c**n)
    
    # Time-dependent exponential decay
    time_component = np.exp(-k * t)
    
    # Combined model
    response = R0 + (Rmax - R0) * hill_component * time_component
    
    return response


def model_3d_hill_time_growth(params, t, c):
    """
    Alternative 3D Model: Hill Equation with Time-Dependent Growth/Decay
    
    R(t,C) = R0 + (Rmax - R0) * [C^n / (EC50^n + C^n)] * [1 - exp(-k*t)]
    
    This models a gradual onset of effect over time.
    
    Parameters:
    -----------
    params : tuple
        (R0, Rmax, EC50, n, k) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    
    Returns:
    --------
    response : np.array
        Predicted response values
    """
    R0, Rmax, EC50, n, k = params
    
    hill_component = (c**n) / (EC50**n + c**n)
    time_component = 1 - np.exp(-k * t)
    
    response = R0 + (Rmax - R0) * hill_component * time_component
    
    return response


def model_3d_separable_response_surface(params, t, c):
    """
    3D Separable Response Surface Model
    
    R(t,C) = R0 + A_C(C) * A_T(t)
    
    Where concentration and time effects are separable.
    
    Parameters:
    -----------
    params : tuple
        (R0, A_max, EC50, n, k, t_half) - model parameters
    t : np.array
        Time array
    c : np.array
        Normalized concentration array
    
    Returns:
    --------
    response : np.array
        Predicted response values
    """
    R0, A_max, EC50, n, k, t_half = params
    
    # Concentration component (Hill equation)
    conc_component = A_max * (c**n) / (EC50**n + c**n)
    
    # Time component (exponential decay with half-life)
    time_component = np.exp(-k * t / t_half)
    
    response = R0 + conc_component * time_component
    
    return response


def fit_3d_model(time_data, conc_data, response_data, model_func, initial_guess=None):
    """
    Fit a 3D model to the time-concentration-response data.
    
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
    initial_guess : tuple, optional
        Initial parameter guess
    
    Returns:
    --------
    popt : np.array
        Optimized parameters
    pcov : np.array
        Parameter covariance matrix
    """
    # Prepare data for fitting (flatten for scipy)
    def model_wrapper(t_c_data, *params):
        """Wrapper function for curve_fit that expects data as first argument."""
        t, c = t_c_data
        return model_func(params, t, c)
    
    # Default initial guess based on data
    if initial_guess is None:
        R0_guess = np.percentile(response_data, 10)
        Rmax_guess = np.percentile(response_data, 90)
        EC50_guess = np.median(conc_data)
        n_guess = 1.0
        k_guess = 0.1
        
        if model_func == model_3d_separable_response_surface:
            initial_guess = (R0_guess, Rmax_guess - R0_guess, EC50_guess, n_guess, k_guess, np.median(time_data))
        else:
            initial_guess = (R0_guess, Rmax_guess, EC50_guess, n_guess, k_guess)
    
    # Fit the model
    try:
        popt, pcov = curve_fit(
            model_wrapper,
            (time_data, conc_data),
            response_data,
            p0=initial_guess,
            maxfev=10000,
            bounds=([0, 0, 0, 0.1, 0], [np.inf, np.inf, np.inf, 10, np.inf])
            if model_func != model_3d_separable_response_surface
            else ([0, 0, 0, 0.1, 0, 0], [np.inf, np.inf, np.inf, 10, np.inf, np.inf])
        )
        return popt, pcov
    except Exception as e:
        print(f"Fitting failed: {e}")
        return None, None


def visualize_3d_model(time_data, conc_data, response_data, model_func, params, 
                       drug_name, response_type, save_path=None):
    """
    Create 3D visualization of the model and data.
    
    Parameters:
    -----------
    time_data : np.array
        Time points
    conc_data : np.array
        Concentrations
    response_data : np.array
        Response values
    model_func : function
        Model function
    params : np.array
        Fitted parameters
    drug_name : str
        Name of the drug
    response_type : str
        Type of response ('O2_mean' or 'Amp_std')
    save_path : str, optional
        Path to save the figure
    """
    # Create a grid for smooth surface plotting
    t_min, t_max = time_data.min(), time_data.max()
    c_min, c_max = conc_data.min(), conc_data.max()
    
    t_grid = np.linspace(t_min, t_max, 50)
    c_grid = np.linspace(c_min, c_max, 50)
    T_grid, C_grid = np.meshgrid(t_grid, c_grid)
    
    # Predict response on grid
    R_grid = model_func(params, T_grid, C_grid)
    
    # Create figure
    fig = plt.figure(figsize=(15, 5))
    
    # 3D Surface Plot
    ax1 = fig.add_subplot(131, projection='3d')
    surf = ax1.plot_surface(T_grid, C_grid, R_grid, alpha=0.6, cmap='viridis')
    ax1.scatter(time_data, conc_data, response_data, c='red', s=20, alpha=0.5)
    ax1.set_xlabel('Time (hours)')
    ax1.set_ylabel('Concentration (normalized by Cmax)')
    ax1.set_zlabel(f'{response_type} Response')
    ax1.set_title(f'{drug_name} - 3D Model Surface')
    
    # Contour Plot
    ax2 = fig.add_subplot(132)
    contour = ax2.contourf(T_grid, C_grid, R_grid, levels=20, cmap='viridis')
    ax2.scatter(time_data, conc_data, c=response_data, s=30, cmap='viridis', 
               edgecolors='black', linewidths=0.5)
    ax2.set_xlabel('Time (hours)')
    ax2.set_ylabel('Concentration (normalized by Cmax)')
    ax2.set_title(f'{drug_name} - Contour Map')
    plt.colorbar(contour, ax=ax2, label='Response')
    
    # Time slices
    ax3 = fig.add_subplot(133)
    unique_times = np.unique(time_data)
    colors = plt.cm.viridis(np.linspace(0, 1, len(unique_times)))
    
    for i, t in enumerate(unique_times[:10]):  # Show first 10 time points
        mask = time_data == t
        if np.sum(mask) > 0:
            ax3.scatter(conc_data[mask], response_data[mask], 
                       label=f't={t:.0f}h', alpha=0.6, c=[colors[i]])
    
    # Model predictions at selected time points
    for i, t in enumerate([unique_times[0], unique_times[len(unique_times)//2], unique_times[-1]]):
        if i < len(colors):
            c_pred = np.linspace(c_min, c_max, 100)
            r_pred = model_func(params, np.full(100, t), c_pred)
            ax3.plot(c_pred, r_pred, '--', color=colors[i*len(colors)//3], 
                    linewidth=2, label=f'Model t={t:.0f}h')
    
    ax3.set_xlabel('Concentration (normalized by Cmax)')
    ax3.set_ylabel(f'{response_type} Response')
    ax3.set_title('Concentration-Response Curves')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.close()


def main():
    """
    Main function to load data, fit models, and visualize results.
    """
    # Load Cmax data
    cmax_file = r'c:\Users\NoahB\Documents\MATLAB\drug_Cmax.csv'
    cmax_df = pd.read_csv(cmax_file)
    cmax_dict = dict(zip(cmax_df['Drug'], cmax_df['Cmax_uM']))
    
    # Get all drug folders
    base_dir = '.'
    drug_folders = [d for d in os.listdir(base_dir) 
                   if os.path.isdir(os.path.join(base_dir, d)) and d != '__pycache__']
    
    # Process each drug
    results = {}
    
    for drug_folder in drug_folders:
        drug_path = os.path.join(base_dir, drug_folder)
        drug_name = Path(drug_folder).name
        
        print(f"\nProcessing {drug_name}...")
        
        # Try both response types
        for response_type in ['O2_mean', 'Amp_std']:
            print(f"  Fitting {response_type}...")
            
            # Load data
            time_data, conc_data, response_data, name = load_drug_data(
                drug_path, cmax_dict, response_type
            )
            
            if time_data is None:
                continue
            
            # Fit the model
            popt, pcov = fit_3d_model(
                time_data, conc_data, response_data, 
                model_3d_hill_exponential_decay
            )
            
            if popt is not None:
                # Calculate R-squared
                y_pred = model_3d_hill_exponential_decay(popt, time_data, conc_data)
                ss_res = np.sum((response_data - y_pred) ** 2)
                ss_tot = np.sum((response_data - np.mean(response_data)) ** 2)
                r_squared = 1 - (ss_res / ss_tot)
                
                results[f"{drug_name}_{response_type}"] = {
                    'params': popt,
                    'pcov': pcov,
                    'r_squared': r_squared,
                    'time_data': time_data,
                    'conc_data': conc_data,
                    'response_data': response_data
                }
                
                print(f"    R² = {r_squared:.3f}")
                print(f"    Parameters: R0={popt[0]:.2f}, Rmax={popt[1]:.2f}, "
                      f"EC50={popt[2]:.3f}, n={popt[3]:.2f}, k={popt[4]:.3f}")
                
                # Visualize
                os.makedirs('model_visualizations', exist_ok=True)
                save_path = f'model_visualizations/{drug_name}_{response_type}_3d_model.png'
                visualize_3d_model(
                    time_data, conc_data, response_data,
                    model_3d_hill_exponential_decay, popt,
                    drug_name, response_type, save_path
                )
    
    # Save results summary
    summary_df = pd.DataFrame({
        'Drug_Response': list(results.keys()),
        'R0': [results[k]['params'][0] for k in results.keys()],
        'Rmax': [results[k]['params'][1] for k in results.keys()],
        'EC50': [results[k]['params'][2] for k in results.keys()],
        'n': [results[k]['params'][3] for k in results.keys()],
        'k': [results[k]['params'][4] for k in results.keys()],
        'R_squared': [results[k]['r_squared'] for k in results.keys()]
    })
    summary_df.to_csv('model_parameters_summary.csv', index=False)
    print(f"\nResults summary saved to model_parameters_summary.csv")
    print(f"Total models fitted: {len(results)}")


if __name__ == "__main__":
    main()


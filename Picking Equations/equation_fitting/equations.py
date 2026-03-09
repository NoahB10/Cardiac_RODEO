"""
Equation Definitions for Drug Response Modeling

All 12 equations used for fitting drug-response data.
Each equation function takes X = [C_norm, time] and parameters.
"""
import numpy as np

# =============================================================================
# 1. DUAL EXPONENTIAL (Eq1) - 11 parameters
# =============================================================================

def dual_exponential(X, R0, A_benefit, A_tox, kb, kt, tau_b, tau_t, nb, nt, mb, mt):
    """
    R(C,t) = R0 + A_benefit*(1-exp(-kb*C^nb))*(1-exp(-t/tau_b)^mb)
                - A_tox*(1-exp(-kt*C^nt))*(1-exp(-t/tau_t)^mt)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 0)
    tau_b = max(tau_b, 1e-9)
    tau_t = max(tau_t, 1e-9)

    benefit = A_benefit * (1 - np.exp(-kb * np.power(C_norm, nb))) * \
              np.power(1 - np.exp(-t/tau_b), mb)
    toxicity = A_tox * (1 - np.exp(-kt * np.power(C_norm, nt))) * \
               np.power(1 - np.exp(-t/tau_t), mt)
    return R0 + benefit - toxicity


# =============================================================================
# 2. BIVARIATE GAUSSIAN (Eq2) - 13 parameters
# =============================================================================

def bivariate_gaussian(X, R0, A1, A2, muC1, muT1, sigC1, sigT1, rho1,
                       muC2, muT2, sigC2, sigT2, rho2):
    """
    R(C,t) = R0 + A1*G1(C,t) + A2*G2(C,t)
    Where G is a bivariate Gaussian
    """
    C_norm, t = X[0], X[1]

    def gaussian_2d(c, time, mu_c, mu_t, sig_c, sig_t, rho):
        sig_c = max(sig_c, 1e-6)
        sig_t = max(sig_t, 1e-6)
        rho = np.clip(rho, -0.99, 0.99)
        z_c = (c - mu_c) / sig_c
        z_t = (time - mu_t) / sig_t
        exponent = -0.5 / (1 - rho**2) * (z_c**2 + z_t**2 - 2*rho*z_c*z_t)
        return np.exp(np.clip(exponent, -700, 0))

    g1 = gaussian_2d(C_norm, t, muC1, muT1, sigC1, sigT1, rho1)
    g2 = gaussian_2d(C_norm, t, muC2, muT2, sigC2, sigT2, rho2)
    return R0 + A1*g1 + A2*g2


# =============================================================================
# 3. GAUSSIAN-HILL HYBRID (Eq3) - 10 parameters
# =============================================================================

def gaussian_hill_hybrid(X, R0, Emax, mu_c, sigma_c, tau, m, E_tox, n, TC50_norm, tau_tox):
    """
    R(C,t) = R0 + Emax * Gauss(C) * Hill(t) - E_tox * Hill_conc(C) * Exp_time(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    tau = max(tau, 1e-9)
    tau_tox = max(tau_tox, 1e-9)
    sigma_c = max(sigma_c, 1e-6)
    TC50_norm = max(TC50_norm, 1e-9)

    gauss_conc = np.exp(-0.5 * ((C_norm - mu_c) / sigma_c)**2)
    hill_time = (t/tau)**m / (1 + (t/tau)**m)
    benefit = Emax * gauss_conc * hill_time

    toxic_conc = (C_norm**n) / (TC50_norm**n + C_norm**n)
    toxic_time = 1 - np.exp(-t / tau_tox)
    toxic = E_tox * toxic_conc * toxic_time

    return R0 + benefit - toxic


# =============================================================================
# 4. MODIFIED HILL HORMESIS (Eq4) - 9 parameters
# =============================================================================

def modified_hill_hormesis(X, R0, E_benefit, E_tox, EC50_b_norm, TC50_norm, nb, nt, tau_b, tau_t):
    """
    Modified Hill Hormesis Model
    R(C,t) = R0 + E_benefit * Hill_b(C) * Time_b(t) - E_tox * Hill_t(C) * Time_t(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    tau_b = max(tau_b, 1e-9)
    tau_t = max(tau_t, 1e-9)
    EC50_b_norm = max(EC50_b_norm, 1e-9)
    TC50_norm = max(TC50_norm, 1e-9)

    benefit_conc = (C_norm**nb) / (EC50_b_norm**nb + C_norm**nb)
    benefit_time = 1 - np.exp(-t / tau_b)
    benefit = E_benefit * benefit_conc * benefit_time

    toxic_conc = (C_norm**nt) / (TC50_norm**nt + C_norm**nt)
    toxic_time = 1 - np.exp(-t / tau_t)
    toxic = E_tox * toxic_conc * toxic_time

    return R0 + benefit - toxic


# =============================================================================
# 5. GAUSSIAN RIDGE (Eq5) - 11 parameters
# =============================================================================

def gaussian_ridge(X, R0, A, B, mu_c, sigma_c, mu_tox, sigma_tox, kappa, tau, m, lam):
    """
    Gaussian Ridge Model
    R(C,t) = R0 + A*Gauss_benefit(C)*Time_b(t) - B*Gauss_tox(C)*Time_t(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    tau = max(tau, 1e-9)
    sigma_c = max(sigma_c, 1e-6)
    sigma_tox = max(sigma_tox, 1e-6)

    gauss_benefit = np.exp(-0.5 * ((C_norm - mu_c) / sigma_c)**2)
    time_benefit = 1 - np.exp(-kappa * (t/tau)**m)
    benefit = A * gauss_benefit * time_benefit

    gauss_toxic = np.exp(-0.5 * ((C_norm - mu_tox) / sigma_tox)**2)
    time_toxic = 1 - np.exp(-lam * t)
    toxic = B * gauss_toxic * time_toxic

    return R0 + benefit - toxic


# =============================================================================
# 6. ADAPTIVE RESPONSE (Eq6) - 6 parameters
# =============================================================================

def adaptive_response(X, R0, Emax, EC50_norm, n, tau_onset, tau_adapt):
    """
    Adaptive Response Model
    R(C,t) = R0 + Emax * Hill(C) * Onset(t) * Adapt(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    EC50_norm = max(EC50_norm, 1e-9)
    tau_onset = max(tau_onset, 1e-9)
    tau_adapt = max(tau_adapt, 1e-9)

    hill_conc = (C_norm**n) / (EC50_norm**n + C_norm**n)
    time_onset = 1 - np.exp(-t / tau_onset)
    time_adapt = np.exp(-t / tau_adapt)

    return R0 + Emax * hill_conc * time_onset * time_adapt


# =============================================================================
# 7. BIPHASIC RESPONSE (Eq7) - 9 parameters
# =============================================================================

def biphasic_response(X, R0, E_stim, E_inhib, EC50_stim_norm, IC50_norm, n1, n2, tau_stim, tau_inhib):
    """
    Biphasic Response Model
    R(C,t) = R0 + E_stim*Hill1(C)*Time1(t) + E_inhib*Hill2(C)*Time2(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    EC50_stim_norm = max(EC50_stim_norm, 1e-9)
    IC50_norm = max(IC50_norm, 1e-9)
    tau_stim = max(tau_stim, 1e-9)
    tau_inhib = max(tau_inhib, 1e-9)

    stim_conc = (C_norm**n1) / (EC50_stim_norm**n1 + C_norm**n1)
    stim_time = 1 - np.exp(-t / tau_stim)
    stimulation = E_stim * stim_conc * stim_time

    inhib_conc = (C_norm**n2) / (IC50_norm**n2 + C_norm**n2)
    inhib_time = 1 - np.exp(-t / tau_inhib)
    inhibition = E_inhib * inhib_conc * inhib_time

    return R0 + stimulation - inhibition


# =============================================================================
# 8. CUMULATIVE EXPOSURE (Eq8) - 5 parameters
# =============================================================================

def cumulative_exposure(X, R0, E_tox, alpha, TC50_norm, k_elim):
    """
    Cumulative Exposure Model
    R(C0,t) = R0 - E_tox*(1-exp(-alpha*AUC/TC50))
    AUC = C0*(1-exp(-k_elim*t))/k_elim
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 0)
    TC50_norm = max(TC50_norm, 1e-9)
    k_elim = max(k_elim, 1e-9)

    AUC = C_norm * (1 - np.exp(-k_elim * t)) / k_elim
    return R0 - E_tox * (1 - np.exp(-alpha * AUC / TC50_norm))


# =============================================================================
# 9. RECOVERY MODEL (Eq9) - 4 parameters
# =============================================================================

def recovery_model(X, R0, E_damage, k_damage, k_recovery):
    """
    Recovery Model
    R(C,t) = R0 - E_damage*(1-exp(-k_damage*C*t)) * exp(-k_recovery*t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 0)
    k_damage = max(k_damage, 1e-9)
    k_recovery = max(k_recovery, 1e-9)

    damage = 1 - np.exp(-k_damage * C_norm * t)
    recovery = np.exp(-k_recovery * t)

    return R0 - E_damage * damage * recovery


# =============================================================================
# 10. MODIFIED HILL SIMPLE (Eq10) - 6 parameters
# =============================================================================

def modified_hill_simple(X, R0, Emax, kappa, tau, n, m):
    """
    Modified Hill (Simple) Model
    R(C,t) = R0 + Emax*(1-exp(-kappa*C^n*(t/tau)^m))
    """
    C_norm, t = X[0], X[1]
    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)

    driving = kappa * (C_norm**n) * ((t/tau)**m)
    return R0 + Emax * (1 - np.exp(-driving))


# =============================================================================
# 11. PKPD ELIMINATION (Eq11) - 7 parameters
# =============================================================================

def pkpd_elimination(X, R0, Emax, kappa, n, m, tau, k_elim):
    """
    PKPD Elimination Model
    R(C0,t) = R0 + Emax*(1-exp(-kappa*(C0*exp(-k_elim*t))^n*(t/tau)^m))
    """
    C_norm, t = X[0], X[1]
    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)
    k_elim = max(k_elim, 1e-9)
    t = np.maximum(t, 0)

    C_t = C_norm * np.exp(-k_elim * t)
    driving_force = kappa * (C_t ** n) * ((t / tau) ** m)

    return R0 + Emax * (1 - np.exp(-driving_force))


# =============================================================================
# 12. HORMESIS V0 (Eq12) - 9 parameters
# =============================================================================

def hormesis_v0(X, R0, E_benefit, E_tox, EC50_b_norm, TC50_norm, nb, nt, tau_b, tau_t):
    """
    Hormesis V0 Model (Legacy - matches MATLAB)
    R(C,t) = R0 + E_benefit*H_b(C)*T_b(t) - E_tox*H_t(C)*T_t(t)
    """
    C_norm, t = X[0], X[1]
    t = np.maximum(t, 1e-9)
    EC50_b_norm = max(EC50_b_norm, 1e-9)
    TC50_norm = max(TC50_norm, 1e-9)
    tau_b = max(tau_b, 1e-9)
    tau_t = max(tau_t, 1e-9)

    H_b = (C_norm / EC50_b_norm) ** nb / (1 + (C_norm / EC50_b_norm) ** nb)
    H_t = (C_norm / TC50_norm) ** nt / (1 + (C_norm / TC50_norm) ** nt)
    time_benefit = 1 - np.exp(-t / tau_b)
    time_tox = 1 - np.exp(-t / tau_t)

    benefit = E_benefit * H_b * time_benefit
    toxic = E_tox * H_t * time_tox

    return R0 + benefit - toxic


# =============================================================================
# EQUATION REGISTRY
# =============================================================================

EQUATION_FUNCTIONS = {
    'dual_exponential': dual_exponential,
    'bivariate_gaussian': bivariate_gaussian,
    'gaussian_hill_hybrid': gaussian_hill_hybrid,
    'modified_hill_hormesis': modified_hill_hormesis,
    'gaussian_ridge': gaussian_ridge,
    'adaptive_response': adaptive_response,
    'biphasic_response': biphasic_response,
    'cumulative_exposure': cumulative_exposure,
    'recovery_model': recovery_model,
    'modified_hill_simple': modified_hill_simple,
    'pkpd_elimination': pkpd_elimination,
    'hormesis_v0': hormesis_v0
}

def get_equation(name):
    """Get equation function by name."""
    return EQUATION_FUNCTIONS.get(name)

if __name__ == "__main__":
    print("Equation functions loaded:")
    for name in EQUATION_FUNCTIONS:
        print(f"  - {name}")

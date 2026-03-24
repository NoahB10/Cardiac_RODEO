"""
Heart Rate Dose-Response Pattern Search for 5 drugs.
Extracts BPM at all timepoints, then searches for the pattern:
  High conc: starts normal (50-65), jumps high (85+), reduces slightly
  Med conc: starts normal, progressive increase
  Low conc: stays stable
"""
import numpy as np
import pandas as pd
import re
from pathlib import Path
from scipy.signal import welch
from scipy.fft import fft, ifft, fftfreq

RELAXED_DIR = Path('Cleaned_Data/Stage1_Raw_Relaxed')
OUT_DIR = Path('Output/HeartRate_Analysis/DoseResponse')
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP_INITIAL = 5
SKIP_FINAL = 1
HOUR_PATTERN = re.compile(r"_(\d+)h_", re.IGNORECASE)

DRUG_CONFIG = {
    'epirubicin':     {'folder': 'Epirubicin (B04)'},
    'daunorubicin':   {'folder': 'Daunorubicin (F03)'},
    'chlorpromazine': {'folder': 'Chlorpromazine'},
    'cobimetinib':    {'folder': 'Cobimetinib (E03)'},
    'doxorubicin':    {'folder': 'Doxorubicin (G03)'},
}


def get_hour(fname):
    m = HOUR_PATTERN.search(fname)
    return int(m.group(1)) if m else None


def get_well(fname):
    m = re.match(r"^([A-P]\d{2})", fname, re.IGNORECASE)
    return m.group(1).upper() if m else None


def compute_bpm(filepath):
    try:
        df = pd.read_csv(filepath)
        if len(df) > SKIP_INITIAL + SKIP_FINAL:
            df = df.iloc[SKIP_INITIAL:-SKIP_FINAL].reset_index(drop=True)
        if 'time_s' not in df or 'amp1_vpp' not in df or len(df) < 10:
            return np.nan
        time_s = df['time_s'].values
        signal = df['amp1_vpp'].values - np.nanmean(df['amp1_vpp'].values)
        order = np.argsort(time_s)
        dt = np.median(np.diff(time_s[order]))
        if dt <= 0:
            return np.nan
        freqs, power = welch(signal[order], fs=1.0/dt, nperseg=min(256, len(signal)))
        band = (freqs >= 0.5) & (freqs <= 2.0)
        if not band.any():
            return np.nan
        dom_freq = freqs[band][np.argmax(power[band])]
        # Harmonic doubling check
        half = dom_freq / 2.0
        if half >= 0.5:
            hi = np.argmin(np.abs(freqs - half))
            pi = np.argmin(np.abs(freqs - dom_freq))
            if power[pi] > 0 and power[hi] / power[pi] >= 0.7:
                dom_freq = half
        return dom_freq * 60
    except Exception:
        return np.nan


def extract_all_bpm():
    """Step 1: Extract BPM for all wells/timepoints."""
    all_wells = []

    for drug, cfg in DRUG_CONFIG.items():
        drug_dir = RELAXED_DIR / cfg['folder']
        if not drug_dir.exists():
            print(f"  SKIP: {drug} - {drug_dir} not found")
            continue

        conc_dirs = sorted([d for d in drug_dir.iterdir()
                           if d.is_dir() and (d.name.lower().endswith('mm') or d.name.lower().endswith('um'))])
        print(f"\n{drug.upper()} ({cfg['folder']}) - {len(conc_dirs)} concentrations")

        for conc_dir in conc_dirs:
            conc_name = conc_dir.name
            conc_val = float(conc_name.lower().replace('mm', '').replace('um', '').replace('_', '.'))

            files = sorted(conc_dir.glob('*.csv'))
            well_hours = {}
            for f in files:
                w = get_well(f.name)
                h = get_hour(f.name)
                if w and h is not None:
                    well_hours.setdefault(w, {})[h] = f

            for well, hour_files in well_hours.items():
                ts = {}
                for h, fpath in hour_files.items():
                    bpm = compute_bpm(fpath)
                    if not np.isnan(bpm):
                        ts[h] = bpm

                if len(ts) >= 3:
                    all_wells.append({
                        'drug': drug, 'conc': conc_val, 'conc_label': conc_name,
                        'well': well, 'ts': ts
                    })

        n_wells = len([w for w in all_wells if w['drug'] == drug])
        print(f"  -> {n_wells} wells with 3+ timepoints")

    return all_wells


def search_pattern(all_wells):
    """Step 2: Search for dose-dependent pattern."""
    print("\n" + "=" * 80)
    print("PATTERN SEARCH")
    print("=" * 80)

    results = {}

    for drug in DRUG_CONFIG:
        dw = [w for w in all_wells if w['drug'] == drug]
        concs = sorted(set(w['conc'] for w in dw))
        if len(concs) < 3:
            print(f"\n{drug.upper()}: only {len(concs)} concentrations, need 3+")
            continue

        all_hours = sorted(set(h for w in dw for h in w['ts']))
        early_opts = [h for h in all_hours if h <= 6]
        mid_opts = [h for h in all_hours if 9 <= h <= 35]
        late_opts = [h for h in all_hours if 40 <= h <= 96]

        best = None
        best_score = -1

        for t1 in early_opts:
            for t2 in mid_opts:
                for t3 in late_opts:
                    conc_wells = {}
                    for c in concs:
                        cw = [w for w in dw if w['conc'] == c
                              and all(t in w['ts'] for t in [t1, t2, t3])]
                        for w in cw:
                            conc_wells.setdefault(c, []).append(
                                (w['ts'][t1], w['ts'][t2], w['ts'][t3], w['well']))

                    if len(conc_wells) < 3:
                        continue

                    conc_list = sorted(conc_wells.keys())
                    for i_l in range(min(3, len(conc_list))):
                        for i_h in range(max(0, len(conc_list) - 3), len(conc_list)):
                            if i_h <= i_l:
                                continue
                            for i_m in range(i_l + 1, i_h):
                                lc = conc_list[i_l]
                                mc = conc_list[i_m]
                                hc = conc_list[i_h]
                                for lw in conc_wells[lc]:
                                    for mw in conc_wells[mc]:
                                        for hw in conc_wells[hc]:
                                            le, lm, ll = lw[:3]
                                            me, mm, ml = mw[:3]
                                            he, hm, hl = hw[:3]

                                            if not (50 <= le <= 65 and 50 <= me <= 65 and 50 <= he <= 65):
                                                continue

                                            score = 0
                                            # High: jump then reduce
                                            if hm >= 85 and hl < hm and hl >= 70:
                                                score += 3
                                            elif hm > he + 15:
                                                score += 1

                                            # Med: progressive increase
                                            if mm > me + 3 and ml > mm + 3:
                                                score += 3
                                            elif mm > me and ml > me + 10:
                                                score += 2

                                            # Low: stable
                                            if abs(lm - le) < 12 and abs(ll - le) < 12 and 45 <= lm <= 75 and 45 <= ll <= 75:
                                                score += 3
                                            elif abs(ll - le) < 18 and 40 <= ll <= 80:
                                                score += 1

                                            if score > best_score:
                                                best_score = score
                                                best = {
                                                    'drug': drug, 'score': score,
                                                    'times': (t1, t2, t3),
                                                    'high': (hc, he, hm, hl, hw[3]),
                                                    'med': (mc, me, mm, ml, mw[3]),
                                                    'low': (lc, le, lm, ll, lw[3]),
                                                }

        if best:
            results[drug] = best
            b = best
            print(f"\n{b['drug'].upper()} | BEST score={b['score']}/9 | times: {b['times'][0]}h, {b['times'][1]}h, {b['times'][2]}h")
            print(f"  HIGH ({b['high'][0]:.3f} mM, {b['high'][4]}): {b['high'][1]:.0f} -> {b['high'][2]:.0f} -> {b['high'][3]:.0f}")
            print(f"  MED  ({b['med'][0]:.3f} mM, {b['med'][4]}):  {b['med'][1]:.0f} -> {b['med'][2]:.0f} -> {b['med'][3]:.0f}")
            print(f"  LOW  ({b['low'][0]:.3f} mM, {b['low'][4]}):  {b['low'][1]:.0f} -> {b['low'][2]:.0f} -> {b['low'][3]:.0f}")
        else:
            print(f"\n{drug.upper()}: no candidates found with baseline 50-65")

    return results


def export_waveforms(results):
    """Step 3: Export filtered waveforms for each drug's best result."""

    def bandpass_filter(time_s, signal, freq_band=(0.5, 2.0)):
        signal_d = signal - np.nanmean(signal)
        order = np.argsort(time_s)
        dt = np.median(np.diff(time_s[order]))
        sig_fft = fft(signal_d[order])
        freqs = fftfreq(len(signal_d), dt)
        sig_fft[~((np.abs(freqs) >= freq_band[0]) & (np.abs(freqs) <= freq_band[1]))] = 0
        filtered = np.real(ifft(sig_fft))
        result = np.empty_like(filtered)
        result[order] = filtered
        return result

    for drug, best in results.items():
        cfg = DRUG_CONFIG[drug]
        drug_dir = RELAXED_DIR / cfg['folder']
        t1, t2, t3 = best['times']

        # Find the actual files
        file_map = {}
        for level, (conc, _, _, _, well) in [('High', best['high']), ('Med', best['med']), ('Low', best['low'])]:
            # Find the concentration folder
            conc_str = None
            for d in drug_dir.iterdir():
                if d.is_dir():
                    cval = float(d.name.lower().replace('mm', '').replace('um', '').replace('_', '.'))
                    if abs(cval - conc) < 0.001:
                        conc_str = d.name
                        break
            if not conc_str:
                print(f"  WARNING: can't find folder for {drug} conc={conc}")
                continue

            conc_dir = drug_dir / conc_str
            for t in [t1, t2, t3]:
                # Find file with ±1h tolerance
                candidates = []
                for f in conc_dir.glob(f'{well}_*.csv'):
                    h = get_hour(f.name)
                    if h is not None and abs(h - t) <= 1:
                        candidates.append(f)
                if candidates:
                    # Pick the one starting at time_s~0, or largest
                    best_f = max(candidates, key=lambda f: f.stat().st_size)
                    file_map[(level, conc_str, well, t)] = best_f

        # Export to Excel
        out_path = OUT_DIR / f'{drug}_DoseResponse_Waveforms.xlsx'
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            summary_rows = []
            for (level, conc_str, well, t), fpath in sorted(file_map.items()):
                df = pd.read_csv(fpath)
                if len(df) > SKIP_INITIAL + SKIP_FINAL:
                    df = df.iloc[SKIP_INITIAL:-SKIP_FINAL].reset_index(drop=True)

                time_s = df['time_s'].values
                raw = df['amp1_vpp'].values
                filtered = bandpass_filter(time_s, raw)
                bpm = compute_bpm(fpath)

                sheet = f'{level}_{conc_str}_{well}_{t}h'[:31]
                pd.DataFrame({
                    'time_s': time_s,
                    'amp1_vpp_raw': raw,
                    'amp1_vpp_filtered': filtered,
                }).to_excel(writer, sheet_name=sheet, index=False)

                summary_rows.append({
                    'Level': level, 'Concentration': conc_str,
                    'Well': well, 'Timepoint': f'{t}h',
                    'BPM': round(bpm, 1) if not np.isnan(bpm) else 'N/A',
                    'N_points': len(time_s),
                    'Sheet': sheet, 'Source': fpath.name,
                })

            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)

        print(f"  Saved: {out_path.name} ({len(file_map)} sheets)")


if __name__ == '__main__':
    all_wells = extract_all_bpm()
    results = search_pattern(all_wells)
    export_waveforms(results)
    print(f"\nAll done. Outputs in: {OUT_DIR}")

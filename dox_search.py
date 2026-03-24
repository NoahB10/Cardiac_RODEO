"""Search all Doxorubicin wells for dose-dependent HR pattern with proper time spacing."""
import numpy as np, pandas as pd, re
from pathlib import Path
from scipy.signal import welch

RELAXED_DIR = Path('Cleaned_Data/Stage1_Raw_Relaxed/Doxorubicin (G03)')
SKIP_INITIAL = 5
SKIP_FINAL = 1
HOUR_RE = re.compile(r"_(\d+)h_", re.IGNORECASE)

def get_hour(f): m = HOUR_RE.search(f); return int(m.group(1)) if m else None
def get_well(f): m = re.match(r"^([A-P]\d{2})", f, re.IGNORECASE); return m.group(1).upper() if m else None

def compute_bpm(fp):
    try:
        df = pd.read_csv(fp)
        if len(df) > SKIP_INITIAL+SKIP_FINAL: df = df.iloc[SKIP_INITIAL:-SKIP_FINAL].reset_index(drop=True)
        if len(df) < 10: return np.nan
        t = df['time_s'].values; s = df['amp1_vpp'].values - np.nanmean(df['amp1_vpp'].values)
        o = np.argsort(t); dt = np.median(np.diff(t[o]))
        if dt <= 0: return np.nan
        freqs, power = welch(s[o], fs=1.0/dt, nperseg=min(256, len(s)))
        band = (freqs >= 0.5) & (freqs <= 2.0)
        if not band.any(): return np.nan
        dom = freqs[band][np.argmax(power[band])]
        half = dom / 2.0
        if half >= 0.5:
            if power[np.argmin(np.abs(freqs-dom))] > 0 and power[np.argmin(np.abs(freqs-half))] / power[np.argmin(np.abs(freqs-dom))] >= 0.7:
                dom = half
        return dom * 60
    except: return np.nan

# Extract all BPM
print("Extracting BPM for all Doxorubicin wells...")
well_bpm = {}
for cd in sorted(RELAXED_DIR.iterdir()):
    if not cd.is_dir() or not cd.name.lower().endswith('mm'): continue
    cv = float(cd.name.lower().replace('mm','').replace('_','.'))
    wh = {}
    for f in cd.glob('*.csv'):
        w, h = get_well(f.name), get_hour(f.name)
        if w and h is not None: wh.setdefault(w, {})[h] = f
    for w, hf in wh.items():
        bpms = {}
        for h, fp in hf.items():
            b = compute_bpm(fp)
            if not np.isnan(b): bpms[h] = b
        if len(bpms) >= 5:
            well_bpm[(cv, cd.name, w)] = bpms

print(f"  {len(well_bpm)} wells with 5+ timepoints")
concs = sorted(set(k[0] for k in well_bpm))
print(f"  Concentrations: {concs}\n")

# Search: early 0-6, mid 12-35, late 40-96
best_results = []
for t1 in range(0, 7):
    for t2 in range(12, 36):
        for t3 in range(40, 97, 2):
            cw = {}
            for (c, cl, w), bpms in well_bpm.items():
                if all(t in bpms for t in [t1, t2, t3]):
                    cw.setdefault(c, []).append((bpms[t1], bpms[t2], bpms[t3], w, cl))
            if len(cw) < 3: continue
            cls = sorted(cw.keys())
            for il in range(min(4, len(cls))):
                for ih in range(max(0, len(cls)-4), len(cls)):
                    if ih <= il: continue
                    for im in range(il+1, ih):
                        lc, mc, hc = cls[il], cls[im], cls[ih]
                        for lw in cw[lc]:
                            for mw in cw[mc]:
                                for hw in cw[hc]:
                                    le,lm,ll = lw[:3]; me,mm,ml = mw[:3]; he,hm,hl = hw[:3]
                                    if not (40<=le<=75 and 40<=me<=75 and 40<=he<=75): continue
                                    sc = 0
                                    if hm >= 85 and hl < hm and hl >= 65: sc += 3
                                    elif hm > he + 15: sc += 1
                                    if mm > me+3 and ml > mm+3: sc += 3
                                    elif mm > me and ml > me+10: sc += 2
                                    if abs(lm-le)<15 and abs(ll-le)<15 and 35<=lm<=80 and 35<=ll<=80: sc += 3
                                    elif abs(ll-le)<20 and 35<=ll<=85: sc += 1
                                    if sc >= 7:
                                        best_results.append({
                                            'score': sc, 'times': (t1,t2,t3),
                                            'high': (hc, he, hm, hl, hw[3], hw[4]),
                                            'med': (mc, me, mm, ml, mw[3], mw[4]),
                                            'low': (lc, le, lm, ll, lw[3], lw[4]),
                                        })

best_results.sort(key=lambda x: -x['score'])
seen = set()
shown = 0
print(f"Found {len(best_results)} combos with score >= 7\n")
for r in best_results:
    key = (r['times'], r['high'][4], r['med'][4], r['low'][4])
    if key in seen: continue
    seen.add(key)
    print(f"score={r['score']}/9 | {r['times'][0]}h, {r['times'][1]}h, {r['times'][2]}h")
    print(f"  HIGH ({r['high'][0]:.2f}mM {r['high'][5]} {r['high'][4]}): {r['high'][1]:.0f} -> {r['high'][2]:.0f} -> {r['high'][3]:.0f}")
    print(f"  MED  ({r['med'][0]:.2f}mM {r['med'][5]} {r['med'][4]}):  {r['med'][1]:.0f} -> {r['med'][2]:.0f} -> {r['med'][3]:.0f}")
    print(f"  LOW  ({r['low'][0]:.2f}mM {r['low'][5]} {r['low'][4]}):  {r['low'][1]:.0f} -> {r['low'][2]:.0f} -> {r['low'][3]:.0f}")
    print()
    shown += 1
    if shown >= 10: break

print("Done.")

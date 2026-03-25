"""
Shared figure configuration for Cardiac RODEO project.
Import this module at the top of any script that generates matplotlib figures.

Usage:
    import figure_config  # Sets up Helvetica font and consistent sizes
    import matplotlib.pyplot as plt
    # ... create figures as normal

CRITICAL: All font sizes are fixed in absolute points to ensure consistency
across different figure sizes. These values should NOT be changed per-figure.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# Find project root (where fonts folder is)
_current_file = Path(__file__).resolve()
PROJECT_ROOT = _current_file.parent

# Register Helvetica fonts from local fonts folder
_font_dir = PROJECT_ROOT / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))

# =============================================================================
# MANDATORY FONT SETTINGS - Helvetica with fixed sizes for consistency
# =============================================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# NOTE: Font sizes are NOT set globally here — each figure script sets its
# own explicit fontsize= values so that text remains legible when images are
# scaled down in PowerPoint.  Only font family and DPI are configured here.

# Additional publication-quality settings
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 600  # High DPI for publication
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

print(f"[figure_config] Helvetica font configured from {_font_dir}")

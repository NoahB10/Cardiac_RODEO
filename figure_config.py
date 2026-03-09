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

# Fixed font sizes (in points) - MUST be consistent across all figure sizes
FONT_TITLE = 10       # Figure/axes titles
FONT_AXIS_LABEL = 9   # X and Y axis labels
FONT_TICK_LABEL = 8   # Tick labels on axes
FONT_LEGEND = 8       # Legend text
FONT_ANNOTATION = 8   # Text annotations
FONT_PANEL_LABEL = 10 # Panel labels (A, B, C)
FONT_COLORBAR = 8     # Colorbar labels

# Apply to rcParams for automatic consistency
plt.rcParams['axes.titlesize'] = FONT_TITLE
plt.rcParams['axes.labelsize'] = FONT_AXIS_LABEL
plt.rcParams['xtick.labelsize'] = FONT_TICK_LABEL
plt.rcParams['ytick.labelsize'] = FONT_TICK_LABEL
plt.rcParams['legend.fontsize'] = FONT_LEGEND
plt.rcParams['figure.titlesize'] = FONT_TITLE

# Additional publication-quality settings
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 600  # High DPI for publication
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

print(f"[figure_config] Helvetica font configured from {_font_dir}")
print(f"[figure_config] Font sizes: title={FONT_TITLE}pt, label={FONT_AXIS_LABEL}pt, tick={FONT_TICK_LABEL}pt")

"""Theme colors, fonts, window dimensions, and configuration constants."""

# Window
WINDOW_TITLE = "Data Wizard"
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_GEOMETRY = "1280x800"

# Sidebar
SIDEBAR_WIDTH = 220
SIDEBAR_PAD = 10

# Colors (used on top of CustomTkinter theme)
ACCENT_COLOR = "#3B82F6"       # Blue-500
ACCENT_HOVER = "#2563EB"       # Blue-600
SUCCESS_COLOR = "#22C55E"      # Green-500
WARNING_COLOR = "#F59E0B"      # Amber-500
DANGER_COLOR = "#EF4444"       # Red-500
MUTED_TEXT = "#9CA3AF"         # Gray-400
CARD_BG_DARK = "#1F2937"      # Gray-800
CARD_BG_LIGHT = "#F3F4F6"     # Gray-100

# Fonts
FONT_FAMILY = "Segoe UI"
FONT_SIZE_SM = 12
FONT_SIZE_MD = 14
FONT_SIZE_LG = 18
FONT_SIZE_XL = 24

# Data table
TABLE_PAGE_SIZE = 100
TABLE_MAX_COLUMN_WIDTH = 250
TABLE_MIN_COLUMN_WIDTH = 80

# Large dataset threshold
LARGE_DATASET_ROWS = 1_000_000
DEFAULT_ROW_LIMIT = 500_000

# Wizard steps
STEPS = [
    {"key": "load",    "label": "1. Load Data",       "icon": "📂"},
    {"key": "explore", "label": "2. Explore",          "icon": "🔍"},
    {"key": "missing", "label": "3. Missing Values",   "icon": "🩹"},
    {"key": "outlier", "label": "4. Outliers",         "icon": "📊"},
    {"key": "export",  "label": "5. Export",           "icon": "💾"},
    {"key": "ml",      "label": "6. Machine Learning", "icon": "🤖"},
]

# Outlier detection defaults
IQR_MULTIPLIER = 1.5
ZSCORE_THRESHOLD = 3.0

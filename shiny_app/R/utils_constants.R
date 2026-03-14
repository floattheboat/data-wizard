# Constants and configuration values

# Data limits
LARGE_DATASET_ROWS <- 1e6
DEFAULT_ROW_LIMIT <- 500000L
TABLE_PAGE_SIZE <- 100L

# Outlier defaults
IQR_MULTIPLIER <- 1.5
ZSCORE_THRESHOLD <- 3.0

# UI Colors
ACCENT_COLOR <- "#3B82F6"
SUCCESS_COLOR <- "#22C55E"
WARNING_COLOR <- "#F59E0B"
DANGER_COLOR <- "#EF4444"
MUTED_TEXT <- "#9CA3AF"
SIDEBAR_BG <- "#1F2937"
CARD_BG <- "#374151"

# Step definitions
STEPS <- list(
  list(id = 1L, name = "Load Data",       icon = "upload"),
  list(id = 2L, name = "Explore",         icon = "magnifying-glass-chart"),
  list(id = 3L, name = "Missing Values",  icon = "puzzle-piece"),
  list(id = 4L, name = "Outliers",        icon = "triangle-exclamation"),
  list(id = 5L, name = "Export",          icon = "file-export"),
  list(id = 6L, name = "Machine Learning", icon = "brain")
)

# Missing value strategy definitions
MISSING_STRATEGIES <- list(
  drop_rows    = list(label = "Drop Rows",        types = c("numeric", "categorical", "datetime", "boolean", "text", "empty")),
  fill_mean    = list(label = "Fill with Mean",    types = c("numeric")),
  fill_median  = list(label = "Fill with Median",  types = c("numeric")),
  fill_mode    = list(label = "Fill with Mode",    types = c("numeric", "categorical", "datetime", "boolean", "text")),
  fill_custom  = list(label = "Fill with Custom",  types = c("numeric", "categorical", "datetime", "boolean", "text")),
  fill_forward = list(label = "Forward Fill",      types = c("numeric", "categorical", "datetime", "boolean", "text")),
  fill_backward = list(label = "Backward Fill",    types = c("numeric", "categorical", "datetime", "boolean", "text")),
  interpolate  = list(label = "Interpolate",       types = c("numeric")),
  leave        = list(label = "Leave As-Is",       types = c("numeric", "categorical", "datetime", "boolean", "text", "empty"))
)

# Outlier remediation strategies
OUTLIER_STRATEGIES <- list(
  remove = "Remove Outlier Rows",
  cap    = "Cap (Winsorize)",
  log    = "Log Transform",
  leave  = "Leave As-Is"
)

# ML algorithm definitions
ML_CLASSIFICATION_ALGORITHMS <- c(

  "Logistic Regression",
  "Random Forest",
  "Gradient Boosting",
  "KNN",
  "Decision Tree",
  "SVM"
)

ML_REGRESSION_ALGORITHMS <- c(
  "Linear Regression",
  "Random Forest",
  "Gradient Boosting",
  "KNN",
  "Decision Tree",
  "Ridge Regression"
)

# Export formats
EXPORT_FORMATS <- c("CSV", "TSV", "Excel", "JSON", "Parquet")

# Database types
DB_TYPES <- c("SQLite", "PostgreSQL", "MySQL")

DB_DEFAULT_PORTS <- list(
  SQLite = NA_integer_,
  PostgreSQL = 5432L,
  MySQL = 3306L
)

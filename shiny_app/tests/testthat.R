# Test runner for Data Wizard Shiny app

library(testthat)

# Source all utility files
source(file.path("..", "..", "R", "utils_constants.R"))
source(file.path("..", "..", "R", "utils_type_detection.R"))
source(file.path("..", "..", "R", "utils_analyzer.R"))
source(file.path("..", "..", "R", "utils_missing.R"))
source(file.path("..", "..", "R", "utils_outlier.R"))
source(file.path("..", "..", "R", "utils_ml.R"))

test_dir("testthat")

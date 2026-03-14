# Tests for outlier detection and remediation

if (!exists("classify_column")) {
  source(file.path("..", "..", "R", "utils_constants.R"))
  source(file.path("..", "..", "R", "utils_type_detection.R"))
  source(file.path("..", "..", "R", "utils_outlier.R"))
}

test_that("detect_outliers_iqr identifies outliers", {
  x <- c(1, 2, 3, 4, 5, 100)  # 100 is an outlier
  result <- detect_outliers_iqr(x, multiplier = 1.5)

  expect_true(is.logical(result$mask))
  expect_equal(length(result$mask), length(x))
  expect_true(result$mask[6])  # 100 should be flagged
  expect_false(result$mask[1])  # 1 should not be flagged
  expect_true(!is.na(result$lower_bound))
  expect_true(!is.na(result$upper_bound))
})

test_that("detect_outliers_zscore identifies outliers", {
  set.seed(42)
  x <- c(rnorm(100), 100, -100)  # extreme values
  result <- detect_outliers_zscore(x, threshold = 3.0)

  expect_true(is.logical(result$mask))
  expect_true(result$mask[101])  # 100 should be flagged
  expect_true(result$mask[102])  # -100 should be flagged
})

test_that("detect_outliers_zscore handles zero std dev", {
  x <- c(5, 5, 5, 5, 5)
  result <- detect_outliers_zscore(x, threshold = 3.0)
  expect_false(any(result$mask))
})

test_that("detect_outliers_iqr handles empty input", {
  x <- rep(NA_real_, 5)
  result <- detect_outliers_iqr(x)
  expect_false(any(result$mask))
})

test_that("get_outlier_info scans numeric columns", {
  df <- data.frame(
    normal = rnorm(100),
    with_outlier = c(rnorm(99), 1000),
    text_col = rep("a", 100),
    stringsAsFactors = FALSE
  )
  result <- get_outlier_info(df, method = "iqr")

  # Should find outliers in with_outlier column
  names_found <- vapply(result, function(x) x$name, character(1))
  expect_true("with_outlier" %in% names_found)
})

test_that("get_outlier_info returns proper fields", {
  df <- data.frame(x = c(1, 2, 3, 4, 5, 100))
  result <- get_outlier_info(df, method = "iqr")

  expect_true(length(result) > 0)
  info <- result[[1]]
  expect_true(!is.null(info$name))
  expect_true(!is.null(info$outlier_count))
  expect_true(!is.null(info$outlier_pct))
  expect_true(!is.null(info$lower_bound))
  expect_true(!is.null(info$upper_bound))
})

test_that("apply_remediation remove drops outlier rows", {
  df <- data.frame(x = c(1, 2, 3, 4, 5, 100), y = c(10, 20, 30, 40, 50, 60))
  result <- apply_remediation(df, "x", "remove", method = "iqr", threshold = 1.5)
  expect_true(nrow(result) < nrow(df))
  expect_true(max(result$x) < 100)
})

test_that("apply_remediation cap winsorizes values", {
  df <- data.frame(x = c(1, 2, 3, 4, 5, 100))
  result <- apply_remediation(df, "x", "cap", method = "iqr", threshold = 1.5)

  # Row count should be same
  expect_equal(nrow(result), nrow(df))
  # Max should be capped
  expect_true(max(result$x) < 100)
})

test_that("apply_remediation log transforms values", {
  df <- data.frame(x = c(1, 2, 3, 4, 5, 100))
  result <- apply_remediation(df, "x", "log", method = "iqr", threshold = 1.5)

  expect_equal(nrow(result), nrow(df))
  # Log transform should reduce the spread
  expect_true(max(result$x) < 100)
})

test_that("apply_remediation log handles negative values", {
  df <- data.frame(x = c(-5, -1, 0, 1, 5, 100))
  result <- apply_remediation(df, "x", "log", method = "iqr", threshold = 1.5)
  expect_equal(nrow(result), nrow(df))
  expect_true(all(is.finite(result$x)))
})

test_that("apply_remediation leave does nothing", {
  df <- data.frame(x = c(1, 2, 3, 4, 5, 100))
  result <- apply_remediation(df, "x", "leave", method = "iqr", threshold = 1.5)
  expect_equal(result$x, df$x)
})

test_that("apply_remediations_bulk applies multiple", {
  df <- data.frame(a = c(1, 2, 3, 4, 5, 100), b = c(1, 2, 3, 4, 5, 200))
  remediations <- list(
    a = list(strategy = "cap", method = "iqr", threshold = 1.5),
    b = list(strategy = "cap", method = "iqr", threshold = 1.5)
  )
  result <- apply_remediations_bulk(df, remediations)
  expect_true(max(result$a) < 100)
  expect_true(max(result$b) < 200)
})

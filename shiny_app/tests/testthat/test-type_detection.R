# Tests for type detection

# Source utilities (for standalone test runs)
if (!exists("classify_column")) {
  source(file.path("..", "..", "R", "utils_constants.R"))
  source(file.path("..", "..", "R", "utils_type_detection.R"))
}

test_that("classify_column detects numeric vectors", {
  expect_equal(classify_column(c(1, 2, 3, 4, 5)), "numeric")
  expect_equal(classify_column(c(1.5, 2.7, 3.14)), "numeric")
  expect_equal(classify_column(c(1L, 2L, 3L)), "numeric")
})

test_that("classify_column detects numeric strings", {
  # >80% numeric parseable => numeric
  expect_equal(classify_column(c("1", "2", "3", "4", "5")), "numeric")
  expect_equal(classify_column(c("1.5", "2.7", "3.14", "4.0", "5.2")), "numeric")
})

test_that("classify_column detects categorical vectors", {
  # Few unique values relative to total
  vals <- sample(c("A", "B", "C"), 100, replace = TRUE)
  expect_equal(classify_column(vals), "categorical")

  # Factor is always categorical
  expect_equal(classify_column(factor(c("x", "y", "z"))), "categorical")
})

test_that("classify_column detects datetime", {
  dates <- as.Date(c("2023-01-01", "2023-06-15", "2024-01-01"))
  expect_equal(classify_column(dates), "datetime")

  posixct <- as.POSIXct(c("2023-01-01 10:00:00", "2023-06-15 12:00:00"))
  expect_equal(classify_column(posixct), "datetime")
})

test_that("classify_column detects datetime strings", {
  dt_strings <- c("2023-01-01", "2023-06-15", "2024-01-01", "2024-06-15", "2025-01-01")
  expect_equal(classify_column(dt_strings), "datetime")
})

test_that("classify_column detects boolean", {
  expect_equal(classify_column(c(TRUE, FALSE, TRUE, FALSE)), "boolean")
  expect_equal(classify_column(c(TRUE, FALSE, NA)), "boolean")
})

test_that("classify_column detects text", {
  # Many unique values => text
  text_vals <- paste0("unique_text_", seq_len(200))
  expect_equal(classify_column(text_vals), "text")
})

test_that("classify_column detects empty (all NA)", {
  expect_equal(classify_column(c(NA, NA, NA)), "empty")
  expect_equal(classify_column(rep(NA_real_, 5)), "empty")
})

test_that("classify_columns works on data frame", {
  df <- data.frame(
    num = c(1, 2, 3),
    cat = factor(c("a", "b", "a")),
    lgl = c(TRUE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )
  types <- classify_columns(df)
  expect_equal(types[["num"]], "numeric")
  expect_equal(types[["cat"]], "categorical")
  expect_equal(types[["lgl"]], "boolean")
})

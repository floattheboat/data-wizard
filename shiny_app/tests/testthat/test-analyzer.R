# Tests for analyzer utilities

if (!exists("classify_column")) {
  source(file.path("..", "..", "R", "utils_constants.R"))
  source(file.path("..", "..", "R", "utils_type_detection.R"))
  source(file.path("..", "..", "R", "utils_analyzer.R"))
}

test_that("analyze_column returns basic stats for any column", {
  x <- c(1, 2, 3, NA, 5)
  result <- analyze_column(x, "test_col")

  expect_equal(result$name, "test_col")
  expect_equal(result$total, 5)
  expect_equal(result$missing, 1)
  expect_equal(result$present, 4)
  expect_equal(result$missing_pct, 20)
})

test_that("analyze_column computes numeric stats", {
  x <- c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  result <- analyze_column(x, "nums")

  expect_equal(result$inferred_type, "numeric")
  expect_equal(result$min, 1)
  expect_equal(result$max, 10)
  expect_equal(result$mean, 5.5)
  expect_equal(result$median, 5.5)
  expect_true(!is.null(result$std))
  expect_true(!is.null(result$q1))
  expect_true(!is.null(result$q3))
  expect_equal(result$zeros, 0)
  expect_equal(result$negatives, 0)
})

test_that("analyze_column computes skewness and kurtosis", {
  x <- rnorm(100)
  result <- analyze_column(x, "normal")
  expect_true(!is.null(result$skew))
  expect_true(!is.null(result$kurtosis))
})

test_that("analyze_column handles categorical columns", {
  x <- sample(c("A", "B", "C"), 100, replace = TRUE)
  result <- analyze_column(x, "cats")

  expect_equal(result$inferred_type, "categorical")
  expect_true(!is.null(result$top_values))
  expect_true(!is.null(result$most_common))
  expect_true(!is.null(result$most_common_count))
})

test_that("analyze_column handles datetime columns", {
  x <- as.Date(c("2023-01-01", "2023-06-15", "2024-01-01"))
  result <- analyze_column(x, "dates")

  expect_equal(result$inferred_type, "datetime")
  expect_true(!is.null(result$min_date))
  expect_true(!is.null(result$max_date))
  expect_true(!is.null(result$date_range_days))
})

test_that("analyze_dataframe returns overview and columns", {
  df <- data.frame(
    a = c(1, 2, NA, 4),
    b = c("x", "y", "x", "z"),
    stringsAsFactors = FALSE
  )
  result <- analyze_dataframe(df)

  expect_true(!is.null(result$overview))
  expect_true(!is.null(result$columns))
  expect_equal(result$overview$rows, 4)
  expect_equal(result$overview$cols, 2)
  expect_equal(result$overview$total_missing, 1)
  expect_equal(length(result$columns), 2)
})

test_that("compute_correlation returns matrix for numeric data", {
  df <- data.frame(a = rnorm(50), b = rnorm(50), c = rnorm(50))
  cor_mat <- compute_correlation(df)

  expect_true(!is.null(cor_mat))
  expect_equal(nrow(cor_mat), 3)
  expect_equal(ncol(cor_mat), 3)
  # Diagonal should be 1
  expect_equal(diag(cor_mat), c(1, 1, 1))
})

test_that("compute_correlation returns NULL for < 2 numeric cols", {
  df <- data.frame(a = c(1, 2, 3), b = c("x", "y", "z"), stringsAsFactors = FALSE)
  expect_null(compute_correlation(df))
})

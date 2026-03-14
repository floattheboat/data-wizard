# Tests for missing value utilities

if (!exists("classify_column")) {
  source(file.path("..", "..", "R", "utils_constants.R"))
  source(file.path("..", "..", "R", "utils_type_detection.R"))
  source(file.path("..", "..", "R", "utils_missing.R"))
}

test_that("get_missing_columns finds columns with NA", {
  df <- data.frame(a = c(1, NA, 3), b = c("x", "y", "z"), c = c(NA, NA, 1))
  result <- get_missing_columns(df)

  expect_equal(length(result), 2)  # a and c
  names_found <- vapply(result, function(x) x$name, character(1))
  expect_true("a" %in% names_found)
  expect_true("c" %in% names_found)
})

test_that("get_missing_columns returns empty list when no NA", {
  df <- data.frame(a = c(1, 2, 3), b = c("x", "y", "z"))
  result <- get_missing_columns(df)
  expect_equal(length(result), 0)
})

test_that("get_applicable_strategies returns type-appropriate strategies", {
  num_strats <- get_applicable_strategies("numeric")
  expect_true("fill_mean" %in% names(num_strats))
  expect_true("fill_median" %in% names(num_strats))
  expect_true("interpolate" %in% names(num_strats))

  cat_strats <- get_applicable_strategies("categorical")
  expect_false("fill_mean" %in% names(cat_strats))
  expect_false("interpolate" %in% names(cat_strats))
  expect_true("fill_mode" %in% names(cat_strats))
  expect_true("drop_rows" %in% names(cat_strats))
})

test_that("apply_strategy drop_rows removes NA rows", {
  df <- data.frame(a = c(1, NA, 3, NA, 5), b = c(10, 20, 30, 40, 50))
  result <- apply_strategy(df, "a", "drop_rows")
  expect_equal(nrow(result), 3)
  expect_false(any(is.na(result$a)))
})

test_that("apply_strategy fill_mean fills with mean", {
  df <- data.frame(a = c(1, NA, 3, NA, 5))
  result <- apply_strategy(df, "a", "fill_mean")
  expect_false(any(is.na(result$a)))
  expect_equal(result$a[2], mean(c(1, 3, 5)))
})

test_that("apply_strategy fill_median fills with median", {
  df <- data.frame(a = c(1, NA, 3, NA, 5))
  result <- apply_strategy(df, "a", "fill_median")
  expect_false(any(is.na(result$a)))
  expect_equal(result$a[2], median(c(1, 3, 5)))
})

test_that("apply_strategy fill_mode fills with mode", {
  df <- data.frame(a = c("x", NA, "x", "y", NA))
  result <- apply_strategy(df, "a", "fill_mode")
  expect_false(any(is.na(result$a)))
  expect_equal(result$a[2], "x")
})

test_that("apply_strategy fill_custom fills with custom value", {
  df <- data.frame(a = c(1, NA, 3))
  result <- apply_strategy(df, "a", "fill_custom", custom_value = 999)
  expect_equal(result$a[2], 999)
})

test_that("apply_strategy fill_forward carries forward", {
  df <- data.frame(a = c(1, NA, NA, 4))
  result <- apply_strategy(df, "a", "fill_forward")
  expect_equal(result$a, c(1, 1, 1, 4))
})

test_that("apply_strategy fill_backward fills backward", {
  df <- data.frame(a = c(1, NA, NA, 4))
  result <- apply_strategy(df, "a", "fill_backward")
  expect_equal(result$a, c(1, 4, 4, 4))
})

test_that("apply_strategy interpolate performs linear interpolation", {
  df <- data.frame(a = c(1, NA, 3, NA, 5))
  result <- apply_strategy(df, "a", "interpolate")
  expect_equal(result$a, c(1, 2, 3, 4, 5))
})

test_that("apply_strategy leave does not modify data", {
  df <- data.frame(a = c(1, NA, 3))
  result <- apply_strategy(df, "a", "leave")
  expect_equal(result$a, c(1, NA, 3))
})

test_that("apply_strategies_bulk applies multiple strategies", {
  df <- data.frame(a = c(1, NA, 3), b = c(NA, "y", "z"), stringsAsFactors = FALSE)
  strategies <- list(
    a = list(strategy = "fill_mean", custom_value = NULL),
    b = list(strategy = "fill_mode", custom_value = NULL)
  )
  result <- apply_strategies_bulk(df, strategies)
  expect_false(any(is.na(result$a)))
  expect_false(any(is.na(result$b)))
})

test_that("apply_strategy does not modify original data frame", {
  df <- data.frame(a = c(1, NA, 3))
  original_copy <- data.frame(a = c(1, NA, 3))
  apply_strategy(df, "a", "fill_mean")
  expect_equal(df$a, original_copy$a)
})

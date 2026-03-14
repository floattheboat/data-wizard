# Tests for ML utilities

if (!exists("classify_column")) {
  source(file.path("..", "..", "R", "utils_constants.R"))
  source(file.path("..", "..", "R", "utils_type_detection.R"))
  source(file.path("..", "..", "R", "utils_ml.R"))
}

test_that("infer_task_type detects regression for numeric with many unique", {
  x <- rnorm(100)
  expect_equal(infer_task_type(x), "regression")
})

test_that("infer_task_type detects classification for few unique values", {
  x <- sample(c("A", "B", "C"), 100, replace = TRUE)
  expect_equal(infer_task_type(x), "classification")
})

test_that("infer_task_type detects classification for numeric with few unique", {
  x <- sample(1:5, 100, replace = TRUE)
  expect_equal(infer_task_type(x), "classification")
})

test_that("get_algorithms returns correct lists", {
  class_algos <- get_algorithms("classification")
  expect_true("Logistic Regression" %in% class_algos)
  expect_true("Random Forest" %in% class_algos)
  expect_true("SVM" %in% class_algos)
  expect_equal(length(class_algos), 6)

  reg_algos <- get_algorithms("regression")
  expect_true("Linear Regression" %in% reg_algos)
  expect_true("Random Forest" %in% reg_algos)
  expect_true("Ridge Regression" %in% reg_algos)
  expect_equal(length(reg_algos), 6)
})

test_that("prepare_features separates target and features", {
  df <- data.frame(
    x1 = rnorm(50),
    x2 = rnorm(50),
    target = sample(c("A", "B"), 50, replace = TRUE),
    stringsAsFactors = FALSE
  )
  result <- prepare_features(df, "target")

  expect_true("X" %in% names(result))
  expect_true("y" %in% names(result))
  expect_true("info" %in% names(result))
  expect_false("target" %in% names(result$X))
  expect_equal(result$info$task_type, "classification")
  expect_true(is.factor(result$y))
})

test_that("prepare_features drops datetime and text columns", {
  df <- data.frame(
    num = rnorm(50),
    dt = as.Date("2023-01-01") + 1:50,
    target = rnorm(50)
  )
  result <- prepare_features(df, "target")
  expect_false("dt" %in% names(result$X))
})

test_that("prepare_features one-hot encodes categorical features", {
  df <- data.frame(
    num = rnorm(50),
    cat = sample(c("A", "B", "C"), 50, replace = TRUE),
    target = rnorm(50),
    stringsAsFactors = FALSE
  )
  result <- prepare_features(df, "target")
  # Should have dummy columns instead of original 'cat'
  expect_true(result$info$n_features >= 2)  # num + at least 2 dummy cols
})

test_that("train_model runs classification successfully", {
  skip_if_not_installed("ranger")
  skip_if_not_installed("parsnip")

  set.seed(42)
  df <- data.frame(
    x1 = rnorm(100),
    x2 = rnorm(100),
    target = sample(c("A", "B"), 100, replace = TRUE),
    stringsAsFactors = FALSE
  )

  result <- train_model(df, "target", "Random Forest", "classification")

  expect_null(result$error)
  expect_equal(result$task_type, "classification")
  expect_equal(result$algorithm, "Random Forest")
  expect_true(!is.null(result$metrics$accuracy))
  expect_true(!is.null(result$metrics$precision))
  expect_true(!is.null(result$metrics$recall))
  expect_true(!is.null(result$metrics$f1))
  expect_true(result$n_train > 0)
  expect_true(result$n_test > 0)
})

test_that("train_model runs regression successfully", {
  skip_if_not_installed("ranger")
  skip_if_not_installed("parsnip")

  set.seed(42)
  df <- data.frame(
    x1 = rnorm(100),
    x2 = rnorm(100),
    target = rnorm(100)
  )

  result <- train_model(df, "target", "Random Forest", "regression")

  expect_null(result$error)
  expect_equal(result$task_type, "regression")
  expect_true(!is.null(result$metrics$r2))
  expect_true(!is.null(result$metrics$mae))
  expect_true(!is.null(result$metrics$rmse))
  expect_true(!is.null(result$metrics$mse))
})

test_that("train_model returns feature importances for tree models", {
  skip_if_not_installed("ranger")
  skip_if_not_installed("parsnip")

  set.seed(42)
  df <- data.frame(
    x1 = rnorm(100),
    x2 = rnorm(100),
    x3 = rnorm(100),
    target = rnorm(100)
  )

  result <- train_model(df, "target", "Random Forest", "regression")

  expect_null(result$error)
  expect_true(!is.null(result$feature_importances))
  expect_true(length(result$feature_importances) > 0)
})

test_that("train_model handles insufficient data", {
  df <- data.frame(x1 = c(1, 2), target = c("A", "B"), stringsAsFactors = FALSE)
  result <- train_model(df, "target", "Random Forest", "classification")
  expect_true(!is.null(result$error))
})

test_that("all classification algorithms can be built", {
  skip_if_not_installed("parsnip")
  for (algo in ML_CLASSIFICATION_ALGORITHMS) {
    spec <- build_model_spec(algo, "classification")
    expect_true(inherits(spec, "model_spec"))
  }
})

test_that("all regression algorithms can be built", {
  skip_if_not_installed("parsnip")
  for (algo in ML_REGRESSION_ALGORITHMS) {
    spec <- build_model_spec(algo, "regression")
    expect_true(inherits(spec, "model_spec"))
  }
})

test_that("SVM log_loss is N/A (no probability support by default)", {
  skip_if_not_installed("kernlab")
  skip_if_not_installed("parsnip")

  set.seed(42)
  df <- data.frame(
    x1 = rnorm(80),
    x2 = rnorm(80),
    target = sample(c("A", "B"), 80, replace = TRUE),
    stringsAsFactors = FALSE
  )

  result <- train_model(df, "target", "SVM", "classification")

  if (is.null(result$error)) {
    expect_equal(result$metrics$log_loss, "N/A")
  }
})

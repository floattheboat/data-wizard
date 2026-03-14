# Machine learning training, evaluation, and feature importance

#' Infer whether target is classification or regression
#'
#' @param x A vector (target column)
#' @return "classification" or "regression"
infer_task_type <- function(x) {
  if (is.numeric(x) && length(unique(x[!is.na(x)])) > 20) {
    "regression"
  } else {
    "classification"
  }
}

#' Get available algorithms for a task type
#'
#' @param task_type "classification" or "regression"
#' @return Character vector of algorithm names
get_algorithms <- function(task_type) {
  if (task_type == "classification") {
    ML_CLASSIFICATION_ALGORITHMS
  } else {
    ML_REGRESSION_ALGORITHMS
  }
}

#' Prepare features for ML training
#'
#' @param df A data frame
#' @param target_col Target column name
#' @return List with X (features df), y (target), info
prepare_features <- function(df, target_col) {
  y <- df[[target_col]]
  X <- df[, setdiff(names(df), target_col), drop = FALSE]

  # Determine column types and drop datetime/text
  col_types <- classify_columns(X)
  drop_cols <- names(col_types[col_types %in% c("datetime", "text", "empty")])
  if (length(drop_cols) > 0) {
    X <- X[, setdiff(names(X), drop_cols), drop = FALSE]
  }

  # Track initial row count
  n_before <- nrow(X)

  # Build recipe for preprocessing
  train_df <- cbind(X, .target = y)

  # Drop rows with any NA
  complete_mask <- complete.cases(train_df)
  train_df <- train_df[complete_mask, , drop = FALSE]
  rows_dropped <- n_before - nrow(train_df)

  y <- train_df$.target
  X <- train_df[, setdiff(names(train_df), ".target"), drop = FALSE]

  # One-hot encode categorical features
  cat_cols <- names(X)[vapply(X, function(c) is.character(c) || is.factor(c), logical(1))]
  if (length(cat_cols) > 0) {
    for (cc in cat_cols) {
      X[[cc]] <- as.factor(X[[cc]])
    }
    # Use model.matrix for dummy encoding
    formula_str <- paste("~ . - 1")
    mm <- tryCatch({
      model.matrix(as.formula(formula_str), data = X)
    }, error = function(e) {
      # Fallback: just convert factors to numeric
      for (cc in cat_cols) {
        X[[cc]] <- as.numeric(as.factor(X[[cc]]))
      }
      as.matrix(X)
    })
    X <- as.data.frame(mm)
  }

  # Ensure target is factor for classification
  task_type <- infer_task_type(y)
  target_encoded <- FALSE
  if (task_type == "classification") {
    y <- as.factor(y)
    target_encoded <- TRUE
  } else {
    y <- as.numeric(y)
  }

  list(
    X = X,
    y = y,
    info = list(
      n_features = ncol(X),
      rows_dropped = rows_dropped,
      target_encoded = target_encoded,
      task_type = task_type,
      feature_names = names(X)
    )
  )
}

#' Build a parsnip model specification
#'
#' @param algorithm Algorithm name
#' @param task_type "classification" or "regression"
#' @return A parsnip model spec
build_model_spec <- function(algorithm, task_type) {
  mode <- if (task_type == "classification") "classification" else "regression"

  spec <- switch(algorithm,
    "Logistic Regression" = parsnip::logistic_reg() |> parsnip::set_engine("glm"),
    "Linear Regression" = parsnip::linear_reg() |> parsnip::set_engine("lm"),
    "Random Forest" = parsnip::rand_forest(trees = 100) |> parsnip::set_engine("ranger", importance = "impurity"),
    "Gradient Boosting" = parsnip::boost_tree(trees = 100) |> parsnip::set_engine("xgboost"),
    "KNN" = parsnip::nearest_neighbor() |> parsnip::set_engine("kknn"),
    "Decision Tree" = parsnip::decision_tree() |> parsnip::set_engine("rpart"),
    "SVM" = parsnip::svm_rbf() |> parsnip::set_engine("kernlab"),
    "Ridge Regression" = parsnip::linear_reg(penalty = 1, mixture = 0) |> parsnip::set_engine("glmnet"),
    stop(paste("Unknown algorithm:", algorithm))
  )

  spec |> parsnip::set_mode(mode)
}

#' Train a model and return results
#'
#' @param df A data frame
#' @param target_col Target column name
#' @param algorithm Algorithm name
#' @param task_type "classification" or "regression"
#' @param test_size Proportion for test set (default 0.2)
#' @return List with metrics, feature_importances, and metadata
train_model <- function(df, target_col, algorithm, task_type, test_size = 0.2) {
  result <- tryCatch({
    prep <- prepare_features(df, target_col)
    X <- prep$X
    y <- prep$y
    info <- prep$info

    if (nrow(X) < 10) {
      return(list(error = "Not enough data for training (need at least 10 rows after preprocessing)"))
    }

    # Combine for splitting
    train_df <- cbind(X, .target = y)

    # Train/test split
    set.seed(42)
    split <- rsample::initial_split(train_df, prop = 1 - test_size,
                                     strata = if (task_type == "classification") ".target" else NULL)
    train_data <- rsample::training(split)
    test_data <- rsample::testing(split)

    # Build model spec
    model_spec <- build_model_spec(algorithm, task_type)

    # Build recipe
    rec <- recipes::recipe(.target ~ ., data = train_data)

    # Build and fit workflow
    wf <- workflows::workflow() |>
      workflows::add_recipe(rec) |>
      workflows::add_model(model_spec)

    fitted_wf <- parsnip::fit(wf, data = train_data)

    # Predict on test set
    preds <- predict(fitted_wf, test_data)
    test_truth <- test_data$.target

    # Compute metrics
    metrics <- list()

    if (task_type == "classification") {
      pred_classes <- preds$.pred_class
      results_df <- data.frame(.truth = test_truth, .pred_class = pred_classes)
      results_df$.truth <- factor(results_df$.truth, levels = levels(pred_classes))

      metrics$accuracy <- tryCatch({
        yardstick::accuracy_vec(results_df$.truth, results_df$.pred_class)
      }, error = function(e) NA_real_)

      metrics$balanced_accuracy <- tryCatch({
        yardstick::bal_accuracy_vec(results_df$.truth, results_df$.pred_class)
      }, error = function(e) NA_real_)

      # For multiclass, use macro averaging
      metrics$precision <- tryCatch({
        yardstick::precision_vec(results_df$.truth, results_df$.pred_class)
      }, error = function(e) NA_real_)

      metrics$recall <- tryCatch({
        yardstick::recall_vec(results_df$.truth, results_df$.pred_class)
      }, error = function(e) NA_real_)

      metrics$f1 <- tryCatch({
        yardstick::f_meas_vec(results_df$.truth, results_df$.pred_class)
      }, error = function(e) NA_real_)

      # Log loss (requires probability predictions)
      metrics$log_loss <- tryCatch({
        prob_preds <- predict(fitted_wf, test_data, type = "prob")
        prob_df <- cbind(data.frame(.truth = test_truth), prob_preds)
        prob_df$.truth <- factor(prob_df$.truth, levels = levels(pred_classes))
        prob_cols <- names(prob_preds)
        yardstick::mn_log_loss(prob_df, .truth, dplyr::all_of(prob_cols))$.estimate
      }, error = function(e) "N/A")

    } else {
      # Regression metrics
      pred_vals <- preds$.pred
      metrics$r2 <- tryCatch(yardstick::rsq_vec(test_truth, pred_vals), error = function(e) NA_real_)
      metrics$mae <- tryCatch(yardstick::mae_vec(test_truth, pred_vals), error = function(e) NA_real_)
      metrics$rmse <- tryCatch(yardstick::rmse_vec(test_truth, pred_vals), error = function(e) NA_real_)
      metrics$mse <- tryCatch(yardstick::rmse_vec(test_truth, pred_vals)^2, error = function(e) NA_real_)
      metrics$mape <- tryCatch(yardstick::mape_vec(test_truth, pred_vals), error = function(e) "N/A")
      metrics$max_error <- tryCatch(max(abs(test_truth - pred_vals)), error = function(e) NA_real_)
    }

    # Feature importance
    feature_importances <- tryCatch({
      fi <- vip::vi(workflows::extract_fit_parsnip(fitted_wf))
      setNames(as.list(fi$Importance), fi$Variable)
    }, error = function(e) NULL)

    list(
      error = NULL,
      task_type = task_type,
      algorithm = algorithm,
      target_column = target_col,
      n_features = info$n_features,
      n_train = nrow(train_data),
      n_test = nrow(test_data),
      rows_dropped = info$rows_dropped,
      metrics = metrics,
      feature_importances = feature_importances
    )
  }, error = function(e) {
    list(error = paste("Training failed:", e$message))
  })

  result
}

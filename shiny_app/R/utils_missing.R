# Missing value detection and handling strategies

#' Get columns that contain missing values
#'
#' @param df A data frame
#' @return A list of lists with name, missing, missing_pct, total, inferred_type
get_missing_columns <- function(df) {
  result <- list()
  for (cn in names(df)) {
    n_missing <- sum(is.na(df[[cn]]))
    if (n_missing > 0) {
      result[[length(result) + 1]] <- list(
        name = cn,
        missing = n_missing,
        missing_pct = round(n_missing / nrow(df) * 100, 2),
        total = nrow(df),
        inferred_type = classify_column(df[[cn]])
      )
    }
  }
  result
}

#' Get applicable strategies for a column type
#'
#' @param col_type The inferred column type
#' @return Named character vector of strategy_id = label
get_applicable_strategies <- function(col_type) {
  applicable <- list()
  for (sid in names(MISSING_STRATEGIES)) {
    strat <- MISSING_STRATEGIES[[sid]]
    if (col_type %in% strat$types) {
      applicable[[sid]] <- strat$label
    }
  }
  unlist(applicable)
}

#' Apply a missing value strategy to a data frame column
#'
#' @param df A data frame
#' @param col Column name
#' @param strategy Strategy identifier
#' @param custom_value Custom fill value (for fill_custom strategy)
#' @return Modified data frame
apply_strategy <- function(df, col, strategy, custom_value = NULL) {
  switch(strategy,
    drop_rows = {
      df <- df[!is.na(df[[col]]), , drop = FALSE]
    },
    fill_mean = {
      val <- mean(df[[col]], na.rm = TRUE)
      df[[col]][is.na(df[[col]])] <- val
    },
    fill_median = {
      val <- median(df[[col]], na.rm = TRUE)
      df[[col]][is.na(df[[col]])] <- val
    },
    fill_mode = {
      tbl <- table(df[[col]])
      mode_val <- names(sort(tbl, decreasing = TRUE))[1]
      # Convert mode to appropriate type
      if (is.numeric(df[[col]])) {
        mode_val <- as.numeric(mode_val)
      } else if (is.logical(df[[col]])) {
        mode_val <- as.logical(mode_val)
      }
      df[[col]][is.na(df[[col]])] <- mode_val
    },
    fill_custom = {
      val <- custom_value
      if (is.numeric(df[[col]])) {
        val <- suppressWarnings(as.numeric(val))
      }
      df[[col]][is.na(df[[col]])] <- val
    },
    fill_forward = {
      df <- tidyr::fill(df, dplyr::all_of(col), .direction = "down")
    },
    fill_backward = {
      df <- tidyr::fill(df, dplyr::all_of(col), .direction = "up")
    },
    interpolate = {
      if (is.numeric(df[[col]])) {
        df[[col]] <- zoo::na.approx(df[[col]], na.rm = FALSE)
      }
    },
    leave = {
      # No action
    }
  )
  df
}

#' Apply multiple strategies in bulk
#'
#' @param df A data frame
#' @param strategies A named list: list(col_name = list(strategy = "...", custom_value = "..."))
#' @return Modified data frame
apply_strategies_bulk <- function(df, strategies) {
  for (col in names(strategies)) {
    spec <- strategies[[col]]
    df <- apply_strategy(df, col, spec$strategy, spec$custom_value)
  }
  df
}

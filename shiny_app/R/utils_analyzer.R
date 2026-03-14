# Per-column and dataframe-level analysis functions

#' Analyze a single column
#'
#' @param x A vector (column from data frame)
#' @param col_name The column name
#' @return A list of statistics
analyze_column <- function(x, col_name) {
  inferred_type <- classify_column(x)
  n_total <- length(x)
  n_missing <- sum(is.na(x))
  n_present <- n_total - n_missing
  n_unique <- length(unique(x[!is.na(x)]))

  stats <- list(
    name = col_name,
    dtype = class(x)[1],
    inferred_type = inferred_type,
    total = n_total,
    missing = n_missing,
    missing_pct = if (n_total > 0) round(n_missing / n_total * 100, 2) else 0,
    present = n_present,
    unique = n_unique
  )

  non_na <- x[!is.na(x)]

  if (inferred_type == "numeric") {
    numeric_vals <- if (is.numeric(x)) non_na else suppressWarnings(as.numeric(non_na))
    numeric_vals <- numeric_vals[!is.na(numeric_vals)]

    if (length(numeric_vals) > 0) {
      stats$min <- min(numeric_vals)
      stats$max <- max(numeric_vals)
      stats$mean <- mean(numeric_vals)
      stats$median <- median(numeric_vals)
      stats$std <- sd(numeric_vals)
      stats$q1 <- unname(quantile(numeric_vals, 0.25))
      stats$q3 <- unname(quantile(numeric_vals, 0.75))
      stats$zeros <- sum(numeric_vals == 0)
      stats$negatives <- sum(numeric_vals < 0)

      # Skewness and kurtosis (require e1071)
      if (length(numeric_vals) > 2) {
        stats$skew <- tryCatch(e1071::skewness(numeric_vals, na.rm = TRUE), error = function(e) NA_real_)
      } else {
        stats$skew <- NA_real_
      }
      if (length(numeric_vals) > 3) {
        stats$kurtosis <- tryCatch(e1071::kurtosis(numeric_vals, na.rm = TRUE), error = function(e) NA_real_)
      } else {
        stats$kurtosis <- NA_real_
      }
    }
  } else if (inferred_type %in% c("categorical", "text", "boolean")) {
    if (length(non_na) > 0) {
      tbl <- sort(table(non_na), decreasing = TRUE)
      stats$top_values <- as.list(head(tbl, 10))
      stats$most_common <- names(tbl)[1]
      stats$most_common_count <- unname(tbl[1])
    }
  } else if (inferred_type == "datetime") {
    if (length(non_na) > 0) {
      dt_vals <- if (inherits(non_na, "Date") || inherits(non_na, "POSIXct")) {
        non_na
      } else {
        tryCatch(
          lubridate::parse_date_time(non_na, orders = c("ymd", "mdy", "dmy", "ymd HMS", "mdy HMS", "dmy HMS")),
          error = function(e) NULL
        )
      }
      if (!is.null(dt_vals) && length(dt_vals[!is.na(dt_vals)]) > 0) {
        dt_clean <- dt_vals[!is.na(dt_vals)]
        stats$min_date <- as.character(min(dt_clean))
        stats$max_date <- as.character(max(dt_clean))
        stats$date_range_days <- as.numeric(difftime(max(dt_clean), min(dt_clean), units = "days"))
      }
    }
  }

  stats
}

#' Analyze an entire data frame
#'
#' @param df A data frame
#' @return A list with 'columns' (list of per-column stats) and 'overview'
analyze_dataframe <- function(df) {
  col_stats <- lapply(names(df), function(cn) analyze_column(df[[cn]], cn))

  total_missing <- sum(is.na(df))
  total_cells <- nrow(df) * ncol(df)

  overview <- list(
    rows = nrow(df),
    cols = ncol(df),
    total_missing = total_missing,
    missing_pct = if (total_cells > 0) round(total_missing / total_cells * 100, 2) else 0,
    memory_mb = round(as.numeric(object.size(df)) / 1024^2, 2),
    dtypes = table(vapply(df, function(x) class(x)[1], character(1)))
  )

  list(columns = col_stats, overview = overview)
}

#' Compute correlation matrix for numeric columns
#'
#' @param df A data frame
#' @return Correlation matrix or NULL if < 2 numeric columns
compute_correlation <- function(df) {
  numeric_cols <- df[vapply(df, is.numeric, logical(1))]
  if (ncol(numeric_cols) < 2) return(NULL)
  cor(numeric_cols, use = "pairwise.complete.obs")
}

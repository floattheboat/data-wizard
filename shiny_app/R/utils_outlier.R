# Outlier detection and remediation utilities

#' Detect outliers using IQR method
#'
#' @param x A numeric vector
#' @param multiplier IQR multiplier (default 1.5)
#' @return List with mask (logical), lower_bound, upper_bound
detect_outliers_iqr <- function(x, multiplier = IQR_MULTIPLIER) {
  clean <- x[!is.na(x)]
  if (length(clean) == 0) {
    return(list(mask = rep(FALSE, length(x)), lower_bound = NA, upper_bound = NA))
  }
  q1 <- quantile(clean, 0.25, names = FALSE)
  q3 <- quantile(clean, 0.75, names = FALSE)
  iqr_val <- q3 - q1
  lower <- q1 - multiplier * iqr_val
  upper <- q3 + multiplier * iqr_val
  mask <- !is.na(x) & (x < lower | x > upper)
  list(mask = mask, lower_bound = lower, upper_bound = upper)
}

#' Detect outliers using Z-score method
#'
#' @param x A numeric vector
#' @param threshold Z-score threshold (default 3.0)
#' @return List with mask (logical), lower_bound, upper_bound
detect_outliers_zscore <- function(x, threshold = ZSCORE_THRESHOLD) {
  clean <- x[!is.na(x)]
  if (length(clean) == 0) {
    return(list(mask = rep(FALSE, length(x)), lower_bound = NA, upper_bound = NA))
  }
  mu <- mean(clean)
  s <- sd(clean)
  if (is.na(s) || s == 0) {
    return(list(mask = rep(FALSE, length(x)), lower_bound = mu, upper_bound = mu))
  }
  z <- (x - mu) / s
  mask <- !is.na(z) & abs(z) > threshold
  lower <- mu - threshold * s
  upper <- mu + threshold * s
  list(mask = mask, lower_bound = lower, upper_bound = upper)
}

#' Get outlier info for all numeric columns
#'
#' @param df A data frame
#' @param method "iqr" or "zscore"
#' @param threshold The method threshold (IQR multiplier or Z-score threshold)
#' @return List of column outlier summaries
get_outlier_info <- function(df, method = "iqr", threshold = NULL) {
  if (is.null(threshold)) {
    threshold <- if (method == "iqr") IQR_MULTIPLIER else ZSCORE_THRESHOLD
  }

  result <- list()
  for (cn in names(df)) {
    if (!is.numeric(df[[cn]])) next
    clean <- df[[cn]][!is.na(df[[cn]])]
    if (length(clean) == 0) next

    detection <- if (method == "iqr") {
      detect_outliers_iqr(df[[cn]], threshold)
    } else {
      detect_outliers_zscore(df[[cn]], threshold)
    }

    outlier_count <- sum(detection$mask)
    if (outlier_count > 0) {
      result[[length(result) + 1]] <- list(
        name = cn,
        outlier_count = outlier_count,
        outlier_pct = round(outlier_count / length(df[[cn]]) * 100, 2),
        lower_bound = round(detection$lower_bound, 4),
        upper_bound = round(detection$upper_bound, 4),
        min = round(min(clean), 4),
        max = round(max(clean), 4),
        mean = round(mean(clean), 4),
        std = round(sd(clean), 4)
      )
    }
  }
  result
}

#' Apply outlier remediation to a column
#'
#' @param df A data frame
#' @param col Column name
#' @param strategy One of "remove", "cap", "log", "leave"
#' @param method "iqr" or "zscore"
#' @param threshold Detection threshold
#' @return Modified data frame
apply_remediation <- function(df, col, strategy, method = "iqr", threshold = NULL) {
  if (is.null(threshold)) {
    threshold <- if (method == "iqr") IQR_MULTIPLIER else ZSCORE_THRESHOLD
  }

  detection <- if (method == "iqr") {
    detect_outliers_iqr(df[[col]], threshold)
  } else {
    detect_outliers_zscore(df[[col]], threshold)
  }

  switch(strategy,
    remove = {
      df <- df[!detection$mask, , drop = FALSE]
      rownames(df) <- NULL
    },
    cap = {
      df[[col]] <- pmin(pmax(df[[col]], detection$lower_bound), detection$upper_bound)
    },
    log = {
      vals <- df[[col]]
      min_val <- min(vals, na.rm = TRUE)
      if (min_val <= 0) {
        shift <- abs(min_val) + 1
        df[[col]] <- log1p(vals + shift)
      } else {
        df[[col]] <- log1p(vals)
      }
    },
    leave = {
      # No action
    }
  )
  df
}

#' Apply remediations in bulk
#'
#' @param df A data frame
#' @param remediations Named list: list(col = list(strategy, method, threshold))
#' @return Modified data frame
apply_remediations_bulk <- function(df, remediations) {
  for (col in names(remediations)) {
    spec <- remediations[[col]]
    df <- apply_remediation(df, col, spec$strategy, spec$method, spec$threshold)
  }
  df
}

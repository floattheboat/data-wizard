# Column type classification utilities

#' Classify a column's type
#'
#' @param x A vector
#' @return One of "numeric", "categorical", "datetime", "boolean", "text", "empty"
classify_column <- function(x) {
  # Remove attributes that might interfere
  non_na <- x[!is.na(x)]

  # Empty check

  if (length(non_na) == 0) return("empty")

  # Boolean check

  if (is.logical(x)) return("boolean")

  # Numeric check (includes integer)
  if (is.numeric(x)) return("numeric")

  # Datetime check

  if (inherits(x, "Date") || inherits(x, "POSIXct") || inherits(x, "POSIXlt")) {
    return("datetime")
  }

  # Factor check — treat as categorical
  if (is.factor(x)) return("categorical")

  # Character / object type — apply heuristics
  if (is.character(x)) {
    sample_vals <- head(non_na, 100)

    # Try numeric conversion
    numeric_parsed <- suppressWarnings(as.numeric(sample_vals))
    numeric_success_rate <- sum(!is.na(numeric_parsed)) / length(sample_vals)
    if (numeric_success_rate >= 0.8) return("numeric")

    # Try datetime parsing
    datetime_parsed <- tryCatch({
      lubridate::parse_date_time(sample_vals, orders = c("ymd", "mdy", "dmy", "ymd HMS", "mdy HMS", "dmy HMS", "ymd HM", "mdy HM"))
    }, error = function(e) rep(NA, length(sample_vals)),
       warning = function(w) {
      suppressWarnings(lubridate::parse_date_time(sample_vals, orders = c("ymd", "mdy", "dmy", "ymd HMS", "mdy HMS", "dmy HMS", "ymd HM", "mdy HM")))
    })
    datetime_success_rate <- sum(!is.na(datetime_parsed)) / length(sample_vals)
    if (datetime_success_rate >= 0.8) return("datetime")

    # Cardinality heuristic
    n_unique <- length(unique(non_na))
    n_total <- length(non_na)
    unique_ratio <- n_unique / n_total
    if (unique_ratio < 0.5 || n_unique <= 50) return("categorical")

    return("text")
  }

  # Default fallback
  "text"
}

#' Classify all columns in a data frame
#'
#' @param df A data frame
#' @return Named character vector of column types
classify_columns <- function(df) {
  vapply(df, classify_column, character(1))
}

#' Try to convert a character column to a more specific type
#'
#' @param x A character vector
#' @param target_type The target type to convert to
#' @return Converted vector or original if conversion fails
try_convert_column <- function(x, target_type) {
  switch(target_type,
    numeric = {
      converted <- suppressWarnings(as.numeric(x))
      converted
    },
    datetime = {
      converted <- tryCatch(
        lubridate::parse_date_time(x, orders = c("ymd", "mdy", "dmy", "ymd HMS", "mdy HMS", "dmy HMS")),
        error = function(e) x
      )
      converted
    },
    boolean = {
      lower <- tolower(x)
      mapping <- c("true" = TRUE, "false" = FALSE, "1" = TRUE, "0" = FALSE, "yes" = TRUE, "no" = FALSE)
      result <- mapping[lower]
      as.logical(result)
    },
    categorical = {
      as.factor(x)
    },
    x  # return as-is for text or unknown
  )
}

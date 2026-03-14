# File export utility functions

#' Export a data frame to a file
#'
#' @param df A data frame
#' @param file_path Output file path
#' @param format One of "CSV", "TSV", "Excel", "JSON", "Parquet"
#' @return The file path written
export_dataframe <- function(df, file_path, format) {
  # Ensure directory exists
  dir.create(dirname(file_path), recursive = TRUE, showWarnings = FALSE)

  switch(format,
    CSV = {
      readr::write_csv(df, file_path)
    },
    TSV = {
      readr::write_tsv(df, file_path)
    },
    Excel = {
      writexl::write_xlsx(df, file_path)
    },
    JSON = {
      jsonlite::write_json(df, file_path, pretty = TRUE)
    },
    Parquet = {
      arrow::write_parquet(df, file_path)
    },
    stop(paste("Unsupported export format:", format))
  )

  file_path
}

#' Get the file extension for a format
#'
#' @param format Export format name
#' @return File extension including dot
get_format_extension <- function(format) {
  switch(format,
    CSV = ".csv",
    TSV = ".tsv",
    Excel = ".xlsx",
    JSON = ".json",
    Parquet = ".parquet",
    ".csv"
  )
}

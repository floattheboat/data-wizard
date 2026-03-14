# Database connection helper utilities

#' Build a DBI-compatible connection
#'
#' @param db_type One of "SQLite", "PostgreSQL", "MySQL"
#' @param database Database name or file path (SQLite)
#' @param host Host address (not used for SQLite)
#' @param port Port number (not used for SQLite)
#' @param username Username (not used for SQLite)
#' @param password Password (not used for SQLite)
#' @return A DBI connection object
create_db_connection <- function(db_type, database, host = "localhost",
                                  port = NULL, username = "", password = "") {
  if (is.null(port)) {
    port <- DB_DEFAULT_PORTS[[db_type]]
  }

  con <- switch(db_type,
    SQLite = {
      DBI::dbConnect(RSQLite::SQLite(), dbname = database)
    },
    PostgreSQL = {
      DBI::dbConnect(RPostgres::Postgres(),
                     dbname = database, host = host, port = port,
                     user = username, password = password)
    },
    MySQL = {
      DBI::dbConnect(RMySQL::MySQL(),
                     dbname = database, host = host, port = port,
                     user = username, password = password)
    },
    stop(paste("Unsupported database type:", db_type))
  )
  con
}

#' Test a database connection
#'
#' @param db_type Database type
#' @param ... Connection parameters
#' @return List with success (logical) and message (character)
test_db_connection <- function(db_type, ...) {
  tryCatch({
    con <- create_db_connection(db_type, ...)
    on.exit(DBI::dbDisconnect(con))
    # Try listing tables as a connectivity check
    DBI::dbListTables(con)
    list(success = TRUE, message = "Connection successful!")
  }, error = function(e) {
    list(success = FALSE, message = paste("Connection failed:", e$message))
  })
}

#' List tables in a database
#'
#' @param con A DBI connection
#' @return Character vector of table names
list_tables <- function(con) {
  DBI::dbListTables(con)
}

#' Load a table from database
#'
#' @param con A DBI connection
#' @param table_name Table name
#' @param row_limit Optional row limit
#' @return A data frame
load_table <- function(con, table_name, row_limit = NULL) {
  if (!is.null(row_limit)) {
    query <- paste0("SELECT * FROM \"", table_name, "\" LIMIT ", row_limit)
    DBI::dbGetQuery(con, query)
  } else {
    DBI::dbReadTable(con, table_name)
  }
}

#' Write a data frame to a database table
#'
#' @param con A DBI connection
#' @param df A data frame
#' @param table_name Target table name
#' @param overwrite Whether to overwrite existing table
#' @return Number of rows written
write_table <- function(con, df, table_name, overwrite = TRUE) {
  DBI::dbWriteTable(con, table_name, df, overwrite = overwrite)
  nrow(df)
}

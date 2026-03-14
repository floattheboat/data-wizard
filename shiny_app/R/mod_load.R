# Step 1: Load Data Module

mod_load_ui <- function(id) {
  ns <- shiny::NS(id)

  bslib::layout_columns(
    col_widths = c(6, 6),

    # Left: File Upload
    bslib::card(
      bslib::card_header("Upload File"),
      bslib::card_body(
        shiny::fileInput(ns("file_input"), "Choose a file",
                         accept = c(".csv", ".tsv", ".tab", ".xlsx", ".xls", ".json", ".parquet")),
        shiny::verbatimTextOutput(ns("file_info")),
        shiny::hr(),
        shiny::h5("Or Load from Database"),
        shiny::actionButton(ns("db_connect_btn"), "Connect to Database",
                            class = "btn-outline-primary", icon = shiny::icon("database"))
      )
    ),

    # Right: Preview
    bslib::card(
      bslib::card_header("Data Preview"),
      bslib::card_body(
        shiny::uiOutput(ns("preview_info")),
        DT::dataTableOutput(ns("preview_table"))
      )
    ),

    # Bottom: Proceed
    shiny::div(
      class = "d-flex justify-content-end mt-3",
      shiny::actionButton(ns("proceed"), "Proceed to Explore",
                          class = "btn-primary btn-lg", icon = shiny::icon("arrow-right"))
    )
  )
}

mod_load_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # File upload handling
    shiny::observeEvent(input$file_input, {
      req(input$file_input)
      file <- input$file_input

      shiny::withProgress(message = "Loading file...", {
        tryCatch({
          ext <- tolower(tools::file_ext(file$name))
          df <- switch(ext,
            csv = readr::read_csv(file$datapath, show_col_types = FALSE),
            tsv = ,
            tab = readr::read_tsv(file$datapath, show_col_types = FALSE),
            xlsx = ,
            xls = readxl::read_excel(file$datapath),
            json = {
              raw <- jsonlite::fromJSON(file$datapath, flatten = TRUE)
              if (is.data.frame(raw)) raw else as.data.frame(raw)
            },
            parquet = arrow::read_parquet(file$datapath),
            {
              shiny::showNotification("Unsupported file format", type = "error")
              return()
            }
          )

          df <- as.data.frame(df)

          # Row limiting for large datasets
          if (nrow(df) > LARGE_DATASET_ROWS) {
            shiny::showNotification(
              paste0("Large dataset detected (", format(nrow(df), big.mark = ","),
                     " rows). Loading first ", format(DEFAULT_ROW_LIMIT, big.mark = ","), " rows."),
              type = "warning", duration = 10
            )
            df <- df[seq_len(DEFAULT_ROW_LIMIT), , drop = FALSE]
          }

          store$df <- df
          store$original_df <- df
          store$undo_stack <- list()
          store$operations <- list()
          store$source_info <- list(
            type = "file",
            file_type = toupper(ext),
            filename = file$name,
            total_rows = nrow(df),
            total_cols = ncol(df)
          )

          shiny::showNotification(
            paste0("Loaded ", file$name, " (", nrow(df), " rows, ", ncol(df), " columns)"),
            type = "message"
          )
        }, error = function(e) {
          shiny::showNotification(paste("Error loading file:", e$message), type = "error")
        })
      })
    })

    # Database connection modal
    shiny::observeEvent(input$db_connect_btn, {
      shiny::showModal(shiny::modalDialog(
        title = "Database Connection",
        size = "l",
        shiny::selectInput(ns("db_type"), "Database Type", choices = DB_TYPES),
        shiny::conditionalPanel(
          condition = paste0("input['", ns("db_type"), "'] != 'SQLite'"),
          shiny::textInput(ns("db_host"), "Host", value = "localhost"),
          shiny::numericInput(ns("db_port"), "Port", value = 5432),
          shiny::textInput(ns("db_user"), "Username"),
          shiny::passwordInput(ns("db_password"), "Password")
        ),
        shiny::textInput(ns("db_name"), "Database Name / File Path"),
        shiny::actionButton(ns("db_test"), "Test Connection", class = "btn-outline-info me-2"),
        shiny::verbatimTextOutput(ns("db_test_result")),
        shiny::hr(),
        shiny::selectInput(ns("db_table"), "Select Table", choices = NULL),
        footer = shiny::tagList(
          shiny::actionButton(ns("db_load"), "Load Table", class = "btn-primary"),
          shiny::modalButton("Cancel")
        )
      ))
    })

    # Update default port based on DB type
    shiny::observeEvent(input$db_type, {
      port <- DB_DEFAULT_PORTS[[input$db_type]]
      if (!is.na(port)) {
        shiny::updateNumericInput(session, "db_port", value = port)
      }
    })

    # Test DB connection
    shiny::observeEvent(input$db_test, {
      result <- test_db_connection(
        db_type = input$db_type,
        database = input$db_name,
        host = if (input$db_type != "SQLite") input$db_host else "localhost",
        port = if (input$db_type != "SQLite") input$db_port else NULL,
        username = if (input$db_type != "SQLite") input$db_user else "",
        password = if (input$db_type != "SQLite") input$db_password else ""
      )

      output$db_test_result <- shiny::renderPrint({ cat(result$message) })

      if (result$success) {
        tryCatch({
          con <- create_db_connection(
            db_type = input$db_type,
            database = input$db_name,
            host = if (input$db_type != "SQLite") input$db_host else "localhost",
            port = if (input$db_type != "SQLite") input$db_port else NULL,
            username = if (input$db_type != "SQLite") input$db_user else "",
            password = if (input$db_type != "SQLite") input$db_password else ""
          )
          tables <- list_tables(con)
          DBI::dbDisconnect(con)
          shiny::updateSelectInput(session, "db_table", choices = tables)
        }, error = function(e) {
          shiny::showNotification(paste("Error listing tables:", e$message), type = "error")
        })
      }
    })

    # Load table from DB
    shiny::observeEvent(input$db_load, {
      req(input$db_table)
      shiny::withProgress(message = "Loading table...", {
        tryCatch({
          con <- create_db_connection(
            db_type = input$db_type,
            database = input$db_name,
            host = if (input$db_type != "SQLite") input$db_host else "localhost",
            port = if (input$db_type != "SQLite") input$db_port else NULL,
            username = if (input$db_type != "SQLite") input$db_user else "",
            password = if (input$db_type != "SQLite") input$db_password else ""
          )
          df <- load_table(con, input$db_table, row_limit = DEFAULT_ROW_LIMIT)
          DBI::dbDisconnect(con)

          df <- as.data.frame(df)
          store$df <- df
          store$original_df <- df
          store$undo_stack <- list()
          store$operations <- list()
          store$source_info <- list(
            type = "database",
            db_type = input$db_type,
            table_name = input$db_table,
            total_rows = nrow(df),
            total_cols = ncol(df)
          )

          shiny::removeModal()
          shiny::showNotification(
            paste0("Loaded table '", input$db_table, "' (", nrow(df), " rows, ", ncol(df), " columns)"),
            type = "message"
          )
        }, error = function(e) {
          shiny::showNotification(paste("Error loading table:", e$message), type = "error")
        })
      })
    })

    # File info display
    output$file_info <- shiny::renderText({
      req(store$source_info)
      info <- store$source_info
      if (info$type == "file") {
        paste0("File: ", info$filename, "\n",
               "Format: ", info$file_type, "\n",
               "Rows: ", format(info$total_rows, big.mark = ","), "\n",
               "Columns: ", info$total_cols)
      } else {
        paste0("Database: ", info$db_type, "\n",
               "Table: ", info$table_name, "\n",
               "Rows: ", format(info$total_rows, big.mark = ","), "\n",
               "Columns: ", info$total_cols)
      }
    })

    # Preview info
    output$preview_info <- shiny::renderUI({
      req(store$df)
      shiny::tags$p(
        class = "text-muted",
        paste0("Showing ", format(nrow(store$df), big.mark = ","),
               " rows x ", ncol(store$df), " columns")
      )
    })

    # Data preview table
    output$preview_table <- DT::renderDataTable({
      req(store$df)
      DT::datatable(
        store$df,
        options = list(
          pageLength = TABLE_PAGE_SIZE,
          scrollX = TRUE,
          searching = TRUE
        ),
        class = "compact stripe"
      )
    }, server = TRUE)

    # Proceed button
    shiny::observeEvent(input$proceed, {
      req(store$df)
      store$max_unlocked <- max(store$max_unlocked, 2L)
      store$current_step <- 2L
    })
  })
}

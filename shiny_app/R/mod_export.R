# Step 5: Export Module

mod_export_ui <- function(id) {
  ns <- shiny::NS(id)

  shiny::tagList(
    # Cleaning summary
    bslib::card(
      bslib::card_header("Cleaning Summary"),
      bslib::card_body(
        shiny::uiOutput(ns("cleaning_summary"))
      )
    ),

    bslib::layout_columns(
      col_widths = c(6, 6),

      # File export
      bslib::card(
        bslib::card_header("Export to File"),
        bslib::card_body(
          shiny::selectInput(ns("format"), "Export Format", choices = EXPORT_FORMATS),
          shiny::downloadButton(ns("download_btn"), "Download File",
                                class = "btn-primary btn-lg w-100",
                                icon = shiny::icon("download"))
        )
      ),

      # Database export
      bslib::card(
        bslib::card_header("Export to Database"),
        bslib::card_body(
          shiny::actionButton(ns("db_export_btn"), "Connect & Export to Database",
                              class = "btn-outline-primary btn-lg w-100",
                              icon = shiny::icon("database"))
        )
      )
    ),

    shiny::div(
      class = "d-flex justify-content-end mt-3",
      shiny::actionButton(ns("proceed"), "Proceed to Machine Learning",
                          class = "btn-primary btn-lg", icon = shiny::icon("arrow-right"))
    )
  )
}

mod_export_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Cleaning summary
    output$cleaning_summary <- shiny::renderUI({
      req(store$df, store$original_df)

      orig_rows <- nrow(store$original_df)
      orig_cols <- ncol(store$original_df)
      curr_rows <- nrow(store$df)
      curr_cols <- ncol(store$df)
      rows_removed <- orig_rows - curr_rows

      orig_missing <- sum(is.na(store$original_df))
      curr_missing <- sum(is.na(store$df))
      missing_fixed <- orig_missing - curr_missing

      ops <- store$operations

      shiny::tagList(
        bslib::layout_columns(
          col_widths = c(3, 3, 3, 3),
          bslib::value_box(
            title = "Original Shape",
            value = paste0(format(orig_rows, big.mark = ","), " x ", orig_cols),
            theme = bslib::value_box_theme(bg = ACCENT_COLOR),
            showcase = shiny::icon("table")
          ),
          bslib::value_box(
            title = "Current Shape",
            value = paste0(format(curr_rows, big.mark = ","), " x ", curr_cols),
            theme = bslib::value_box_theme(bg = SUCCESS_COLOR),
            showcase = shiny::icon("table")
          ),
          bslib::value_box(
            title = "Rows Removed", value = format(rows_removed, big.mark = ","),
            theme = bslib::value_box_theme(bg = if (rows_removed > 0) WARNING_COLOR else SUCCESS_COLOR),
            showcase = shiny::icon("minus")
          ),
          bslib::value_box(
            title = "Missing Fixed", value = format(missing_fixed, big.mark = ","),
            theme = bslib::value_box_theme(bg = if (missing_fixed > 0) SUCCESS_COLOR else ACCENT_COLOR),
            showcase = shiny::icon("wrench")
          )
        ),

        if (length(ops) > 0) {
          shiny::div(
            class = "mt-3",
            shiny::h6("Operations Performed:"),
            shiny::tags$ul(
              lapply(ops, function(op) {
                n_cols <- length(op$details)
                shiny::tags$li(
                  paste0(tools::toTitleCase(gsub("_", " ", op$type)),
                         " (", n_cols, " column", if (n_cols != 1) "s" else "", ")")
                )
              })
            )
          )
        }
      )
    })

    # File download
    output$download_btn <- shiny::downloadHandler(
      filename = function() {
        ext <- get_format_extension(input$format)
        paste0("data_wizard_export", ext)
      },
      content = function(file) {
        export_dataframe(store$df, file, input$format)
      }
    )

    # Database export modal
    shiny::observeEvent(input$db_export_btn, {
      shiny::showModal(shiny::modalDialog(
        title = "Export to Database",
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
        shiny::textInput(ns("table_name"), "Table Name", value = "exported_data"),
        footer = shiny::tagList(
          shiny::actionButton(ns("db_write"), "Write Table", class = "btn-primary"),
          shiny::modalButton("Cancel")
        )
      ))
    })

    # Update port based on db type
    shiny::observeEvent(input$db_type, {
      port <- DB_DEFAULT_PORTS[[input$db_type]]
      if (!is.na(port)) {
        shiny::updateNumericInput(session, "db_port", value = port)
      }
    })

    # Write to database
    shiny::observeEvent(input$db_write, {
      req(store$df, input$table_name)
      shiny::withProgress(message = "Writing to database...", {
        tryCatch({
          con <- create_db_connection(
            db_type = input$db_type,
            database = input$db_name,
            host = if (input$db_type != "SQLite") input$db_host else "localhost",
            port = if (input$db_type != "SQLite") input$db_port else NULL,
            username = if (input$db_type != "SQLite") input$db_user else "",
            password = if (input$db_type != "SQLite") input$db_password else ""
          )
          rows_written <- write_table(con, store$df, input$table_name)
          DBI::dbDisconnect(con)

          shiny::removeModal()
          shiny::showNotification(
            paste0("Wrote ", format(rows_written, big.mark = ","),
                   " rows to table '", input$table_name, "'"),
            type = "message"
          )
        }, error = function(e) {
          shiny::showNotification(paste("Export failed:", e$message), type = "error")
        })
      })
    })

    # Proceed
    shiny::observeEvent(input$proceed, {
      req(store$df)
      store$max_unlocked <- max(store$max_unlocked, 6L)
      store$current_step <- 6L
    })
  })
}

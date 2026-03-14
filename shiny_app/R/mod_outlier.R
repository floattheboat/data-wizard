# Step 4: Outlier Detection & Remediation Module

mod_outlier_ui <- function(id) {
  ns <- shiny::NS(id)

  shiny::tagList(
    # Detection controls
    bslib::card(
      bslib::card_header("Outlier Detection"),
      bslib::card_body(
        bslib::layout_columns(
          col_widths = c(3, 3, 3, 3),
          shiny::selectInput(ns("method"), "Detection Method",
                             choices = c("IQR" = "iqr", "Z-Score" = "zscore")),
          shiny::sliderInput(ns("threshold"), "Threshold",
                             min = 0.5, max = 5.0, value = 1.5, step = 0.1),
          shiny::div(style = "padding-top: 25px;",
            shiny::actionButton(ns("detect_btn"), "Detect Outliers",
                                class = "btn-primary", icon = shiny::icon("search"))
          ),
          shiny::div(style = "padding-top: 25px;",
            shiny::textOutput(ns("outlier_summary"))
          )
        )
      )
    ),

    # Results
    bslib::layout_columns(
      col_widths = c(5, 7),

      # Left: Column list with remediation
      bslib::card(
        bslib::card_header("Columns with Outliers"),
        bslib::card_body(
          style = "max-height: 450px; overflow-y: auto;",
          shiny::uiOutput(ns("outlier_controls"))
        )
      ),

      # Right: Box plot
      bslib::card(
        bslib::card_header(shiny::textOutput(ns("plot_title"), inline = TRUE)),
        bslib::card_body(
          plotly::plotlyOutput(ns("boxplot"), height = "400px")
        )
      )
    ),

    shiny::div(
      class = "d-flex gap-2 mt-3",
      shiny::actionButton(ns("apply_btn"), "Apply Remediations",
                          class = "btn-primary", icon = shiny::icon("check")),
      shiny::actionButton(ns("undo_btn"), "Undo",
                          class = "btn-outline-warning", icon = shiny::icon("rotate-left")),
      shiny::actionButton(ns("proceed"), "Proceed to Export",
                          class = "btn-success ms-auto", icon = shiny::icon("arrow-right"))
    )
  )
}

mod_outlier_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    outlier_info <- shiny::reactiveVal(list())
    selected_outlier_col <- shiny::reactiveVal(NULL)

    # Update threshold default when method changes
    shiny::observeEvent(input$method, {
      default_val <- if (input$method == "iqr") IQR_MULTIPLIER else ZSCORE_THRESHOLD
      shiny::updateSliderInput(session, "threshold", value = default_val)
    })

    # Detect outliers
    shiny::observeEvent(input$detect_btn, {
      req(store$df)
      shiny::withProgress(message = "Detecting outliers...", {
        info <- get_outlier_info(store$df, method = input$method, threshold = input$threshold)
        outlier_info(info)
      })

      if (length(outlier_info()) == 0) {
        shiny::showNotification("No outliers detected", type = "message")
      }
    })

    # Summary text
    output$outlier_summary <- shiny::renderText({
      info <- outlier_info()
      if (length(info) == 0) return("No outliers detected")
      total <- sum(vapply(info, function(x) x$outlier_count, integer(1)))
      paste0(length(info), " columns, ", total, " total outliers")
    })

    # Outlier controls per column
    output$outlier_controls <- shiny::renderUI({
      info <- outlier_info()
      if (length(info) == 0) {
        return(shiny::div(class = "text-muted text-center p-3",
                          "Click 'Detect Outliers' to scan numeric columns"))
      }

      controls <- lapply(info, function(col_info) {
        col_id <- gsub("[^a-zA-Z0-9]", "_", col_info$name)

        shiny::div(
          class = "card mb-2 p-2",
          style = "border: 1px solid #4B5563; cursor: pointer;",
          shiny::div(
            class = "d-flex justify-content-between align-items-center mb-1",
            shiny::actionLink(ns(paste0("sel_", col_id)), shiny::strong(col_info$name)),
            shiny::span(class = "badge bg-danger",
                        paste0(col_info$outlier_count, " (", col_info$outlier_pct, "%)"))
          ),
          shiny::div(class = "small text-muted",
                     paste0("Bounds: [", col_info$lower_bound, ", ", col_info$upper_bound, "]")),
          shiny::selectInput(ns(paste0("remedy_", col_id)), NULL,
                             choices = OUTLIER_STRATEGIES, selected = "leave",
                             width = "100%")
        )
      })

      # Register click observers
      lapply(info, function(col_info) {
        col_id <- gsub("[^a-zA-Z0-9]", "_", col_info$name)
        shiny::observeEvent(input[[paste0("sel_", col_id)]], {
          selected_outlier_col(col_info$name)
        }, ignoreInit = TRUE)
      })

      shiny::tagList(controls)
    })

    # Plot title
    output$plot_title <- shiny::renderText({
      col <- selected_outlier_col()
      if (is.null(col)) "Select a column to view" else paste("Box Plot:", col)
    })

    # Box plot for selected column
    output$boxplot <- plotly::renderPlotly({
      req(store$df)
      col <- selected_outlier_col()
      req(col, col %in% names(store$df))
      vals <- store$df[[col]]
      req(is.numeric(vals))

      plotly::plot_ly(y = vals[!is.na(vals)], type = "box",
                      marker = list(color = ACCENT_COLOR),
                      line = list(color = ACCENT_COLOR)) |>
        plotly::layout(
          title = paste("Distribution of", col),
          yaxis = list(title = col),
          paper_bgcolor = "rgba(0,0,0,0)",
          plot_bgcolor = "rgba(0,0,0,0)",
          font = list(color = "#E5E7EB")
        )
    })

    # Apply remediations
    shiny::observeEvent(input$apply_btn, {
      req(store$df)
      info <- outlier_info()
      if (length(info) == 0) return()

      remediations <- list()
      for (col_info in info) {
        col_id <- gsub("[^a-zA-Z0-9]", "_", col_info$name)
        remedy <- input[[paste0("remedy_", col_id)]]
        if (!is.null(remedy) && remedy != "leave") {
          remediations[[col_info$name]] <- list(
            strategy = remedy,
            method = input$method,
            threshold = input$threshold
          )
        }
      }

      if (length(remediations) == 0) {
        shiny::showNotification("No remediations selected (all set to 'Leave As-Is')", type = "warning")
        return()
      }

      # Snapshot for undo
      store$undo_stack <- c(list(store$df), store$undo_stack)
      if (length(store$undo_stack) > 10) {
        store$undo_stack <- store$undo_stack[1:10]
      }

      shiny::withProgress(message = "Applying remediations...", {
        store$df <- apply_remediations_bulk(store$df, remediations)
      })

      store$operations <- c(store$operations, list(list(
        type = "outlier_remediation",
        details = remediations,
        timestamp = Sys.time()
      )))

      # Re-detect after remediation
      new_info <- get_outlier_info(store$df, method = input$method, threshold = input$threshold)
      outlier_info(new_info)

      shiny::showNotification(
        paste0("Applied ", length(remediations), " outlier remediations"),
        type = "message"
      )
    })

    # Undo
    shiny::observeEvent(input$undo_btn, {
      if (length(store$undo_stack) == 0) {
        shiny::showNotification("Nothing to undo", type = "warning")
        return()
      }
      store$df <- store$undo_stack[[1]]
      store$undo_stack <- store$undo_stack[-1]
      if (length(store$operations) > 0) {
        store$operations <- store$operations[-length(store$operations)]
      }
      outlier_info(list())
      shiny::showNotification("Undo successful", type = "message")
    })

    # Proceed
    shiny::observeEvent(input$proceed, {
      req(store$df)
      store$max_unlocked <- max(store$max_unlocked, 5L)
      store$current_step <- 5L
    })
  })
}

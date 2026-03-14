# Step 3: Missing Values Module

mod_missing_ui <- function(id) {
  ns <- shiny::NS(id)

  shiny::tagList(
    # Summary bar
    shiny::uiOutput(ns("summary_bar")),

    bslib::card(
      bslib::card_header("Missing Value Strategies"),
      bslib::card_body(
        shiny::uiOutput(ns("no_missing_msg")),
        shiny::div(style = "max-height: 500px; overflow-y: auto;",
          shiny::uiOutput(ns("strategy_controls"))
        ),
        shiny::hr(),
        shiny::div(
          class = "d-flex gap-2",
          shiny::actionButton(ns("apply_btn"), "Apply Strategies",
                              class = "btn-primary", icon = shiny::icon("check")),
          shiny::actionButton(ns("undo_btn"), "Undo",
                              class = "btn-outline-warning", icon = shiny::icon("rotate-left")),
          shiny::actionButton(ns("proceed"), "Proceed to Outliers",
                              class = "btn-success ms-auto", icon = shiny::icon("arrow-right"))
        )
      )
    )
  )
}

mod_missing_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Reactive: columns with missing values
    missing_cols <- shiny::reactive({
      req(store$df)
      get_missing_columns(store$df)
    })

    # Summary bar
    output$summary_bar <- shiny::renderUI({
      req(store$df)
      mc <- missing_cols()
      total_missing <- sum(is.na(store$df))
      total_cells <- nrow(store$df) * ncol(store$df)
      pct <- if (total_cells > 0) round(total_missing / total_cells * 100, 2) else 0

      bslib::layout_columns(
        col_widths = c(4, 4, 4),
        bslib::value_box(
          title = "Columns with Missing", value = length(mc),
          theme = bslib::value_box_theme(bg = if (length(mc) > 0) WARNING_COLOR else SUCCESS_COLOR),
          showcase = shiny::icon("table-columns")
        ),
        bslib::value_box(
          title = "Total Missing Cells", value = format(total_missing, big.mark = ","),
          theme = bslib::value_box_theme(bg = if (total_missing > 0) WARNING_COLOR else SUCCESS_COLOR),
          showcase = shiny::icon("question")
        ),
        bslib::value_box(
          title = "Dataset Shape",
          value = paste0(format(nrow(store$df), big.mark = ","), " x ", ncol(store$df)),
          theme = bslib::value_box_theme(bg = ACCENT_COLOR),
          showcase = shiny::icon("table")
        )
      )
    })

    # No missing message
    output$no_missing_msg <- shiny::renderUI({
      mc <- missing_cols()
      if (length(mc) == 0) {
        shiny::div(
          class = "alert alert-success",
          shiny::icon("check-circle"),
          " No missing values found in the dataset!"
        )
      }
    })

    # Strategy controls per column
    output$strategy_controls <- shiny::renderUI({
      mc <- missing_cols()
      if (length(mc) == 0) return(NULL)

      controls <- lapply(mc, function(col_info) {
        strategies <- get_applicable_strategies(col_info$inferred_type)
        col_id <- gsub("[^a-zA-Z0-9]", "_", col_info$name)

        shiny::div(
          class = "card mb-2 p-3",
          style = "border: 1px solid #4B5563;",
          shiny::div(
            class = "d-flex justify-content-between align-items-center mb-2",
            shiny::strong(col_info$name),
            shiny::span(
              class = "badge bg-warning",
              paste0(col_info$missing, " missing (", col_info$missing_pct, "%)")
            )
          ),
          shiny::div(
            class = "d-flex gap-2 align-items-end",
            shiny::div(
              style = "flex: 1;",
              shiny::selectInput(
                ns(paste0("strategy_", col_id)),
                label = NULL,
                choices = c("Select strategy..." = "", strategies),
                width = "100%"
              )
            ),
            shiny::conditionalPanel(
              condition = paste0("input['", ns(paste0("strategy_", col_id)), "'] == 'fill_custom'"),
              shiny::div(
                style = "flex: 1;",
                shiny::textInput(ns(paste0("custom_", col_id)), label = NULL,
                                 placeholder = "Custom value")
              )
            )
          )
        )
      })

      shiny::tagList(controls)
    })

    # Apply strategies
    shiny::observeEvent(input$apply_btn, {
      req(store$df)
      mc <- missing_cols()
      if (length(mc) == 0) return()

      # Collect strategies
      strategies <- list()
      for (col_info in mc) {
        col_id <- gsub("[^a-zA-Z0-9]", "_", col_info$name)
        strat <- input[[paste0("strategy_", col_id)]]
        if (!is.null(strat) && strat != "" && strat != "leave") {
          custom_val <- input[[paste0("custom_", col_id)]]
          strategies[[col_info$name]] <- list(
            strategy = strat,
            custom_value = if (strat == "fill_custom") custom_val else NULL
          )
        }
      }

      if (length(strategies) == 0) {
        shiny::showNotification("No strategies selected", type = "warning")
        return()
      }

      # Snapshot for undo
      store$undo_stack <- c(list(store$df), store$undo_stack)
      if (length(store$undo_stack) > 10) {
        store$undo_stack <- store$undo_stack[1:10]
      }

      shiny::withProgress(message = "Applying strategies...", {
        store$df <- apply_strategies_bulk(store$df, strategies)
      })

      # Log operations
      store$operations <- c(store$operations, list(list(
        type = "missing_values",
        details = strategies,
        timestamp = Sys.time()
      )))

      shiny::showNotification(
        paste0("Applied ", length(strategies), " missing value strategies"),
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
      shiny::showNotification("Undo successful", type = "message")
    })

    # Proceed
    shiny::observeEvent(input$proceed, {
      req(store$df)
      store$max_unlocked <- max(store$max_unlocked, 4L)
      store$current_step <- 4L
    })
  })
}

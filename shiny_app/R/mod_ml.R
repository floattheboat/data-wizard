# Step 6: Machine Learning Module

mod_ml_ui <- function(id) {
  ns <- shiny::NS(id)

  shiny::tagList(
    bslib::card(
      bslib::card_header("Model Configuration"),
      bslib::card_body(
        bslib::layout_columns(
          col_widths = c(4, 3, 3, 2),
          shiny::selectInput(ns("target_col"), "Target Column", choices = NULL),
          shiny::div(
            shiny::textOutput(ns("task_type_display")),
            shiny::selectInput(ns("algorithm"), "Algorithm", choices = NULL)
          ),
          shiny::div(
            shiny::tags$label("Test Size"),
            shiny::sliderInput(ns("test_size"), NULL, min = 0.1, max = 0.5,
                               value = 0.2, step = 0.05)
          ),
          shiny::div(
            style = "padding-top: 25px;",
            shiny::actionButton(ns("train_btn"), "Train Model",
                                class = "btn-primary btn-lg",
                                icon = shiny::icon("play"))
          )
        )
      )
    ),

    # Results
    shiny::uiOutput(ns("training_status")),

    bslib::layout_columns(
      col_widths = c(5, 7),

      # Metrics table
      bslib::card(
        bslib::card_header("Model Metrics"),
        bslib::card_body(
          shiny::uiOutput(ns("metrics_info")),
          DT::dataTableOutput(ns("metrics_table"))
        )
      ),

      # Feature importance chart
      bslib::card(
        bslib::card_header("Feature Importance"),
        bslib::card_body(
          plotly::plotlyOutput(ns("importance_chart"), height = "400px")
        )
      )
    )
  )
}

mod_ml_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    train_result <- shiny::reactiveVal(NULL)

    # Update target column choices when df changes
    shiny::observe({
      req(store$df)
      cols <- names(store$df)
      shiny::updateSelectInput(session, "target_col", choices = cols)
    })

    # Infer task type and update algorithm list when target changes
    shiny::observe({
      req(store$df, input$target_col)
      req(input$target_col %in% names(store$df))

      task_type <- infer_task_type(store$df[[input$target_col]])
      algos <- get_algorithms(task_type)
      shiny::updateSelectInput(session, "algorithm", choices = algos)
    })

    # Task type display
    output$task_type_display <- shiny::renderText({
      req(store$df, input$target_col)
      req(input$target_col %in% names(store$df))
      task_type <- infer_task_type(store$df[[input$target_col]])
      paste0("Task Type: ", tools::toTitleCase(task_type))
    })

    # Train model
    shiny::observeEvent(input$train_btn, {
      req(store$df, input$target_col, input$algorithm)

      task_type <- infer_task_type(store$df[[input$target_col]])

      shiny::withProgress(message = paste("Training", input$algorithm, "..."), value = 0.3, {
        result <- train_model(
          df = store$df,
          target_col = input$target_col,
          algorithm = input$algorithm,
          task_type = task_type,
          test_size = input$test_size
        )

        shiny::setProgress(1, message = "Training complete!")
        train_result(result)
      })

      if (!is.null(result$error)) {
        shiny::showNotification(paste("Training error:", result$error), type = "error")
      } else {
        shiny::showNotification(
          paste0("Model trained successfully! (",
                 result$n_train, " train / ", result$n_test, " test samples)"),
          type = "message"
        )
      }
    })

    # Training status
    output$training_status <- shiny::renderUI({
      result <- train_result()
      if (is.null(result)) return(NULL)

      if (!is.null(result$error)) {
        shiny::div(class = "alert alert-danger mt-2", shiny::icon("exclamation-triangle"), " ", result$error)
      } else {
        shiny::div(
          class = "alert alert-success mt-2",
          shiny::icon("check-circle"),
          paste0(" ", result$algorithm, " (", result$task_type, ") trained on ",
                 result$n_train, " samples, tested on ", result$n_test, " samples. ",
                 result$rows_dropped, " rows dropped during preprocessing.")
        )
      }
    })

    # Metrics info
    output$metrics_info <- shiny::renderUI({
      result <- train_result()
      if (is.null(result) || !is.null(result$error)) return(NULL)

      shiny::div(class = "text-muted small mb-2",
                 paste0("Algorithm: ", result$algorithm,
                        " | Features: ", result$n_features,
                        " | Target: ", result$target_column))
    })

    # Metrics table
    output$metrics_table <- DT::renderDataTable({
      result <- train_result()
      req(result, is.null(result$error))

      metrics <- result$metrics
      metric_df <- data.frame(
        Metric = names(metrics),
        Value = vapply(metrics, function(v) {
          if (is.character(v)) v
          else if (is.na(v)) "N/A"
          else format(round(as.numeric(v), 4), nsmall = 4)
        }, character(1)),
        stringsAsFactors = FALSE
      )

      DT::datatable(metric_df,
                    options = list(dom = "t", pageLength = 20, ordering = FALSE),
                    rownames = FALSE, class = "compact")
    })

    # Feature importance chart
    output$importance_chart <- plotly::renderPlotly({
      result <- train_result()
      req(result, is.null(result$error), !is.null(result$feature_importances))

      fi <- result$feature_importances
      fi_df <- data.frame(
        Feature = names(fi),
        Importance = as.numeric(fi),
        stringsAsFactors = FALSE
      )

      # Sort by importance and take top 15
      fi_df <- fi_df[order(fi_df$Importance, decreasing = TRUE), ]
      fi_df <- head(fi_df, 15)
      fi_df$Feature <- factor(fi_df$Feature, levels = rev(fi_df$Feature))

      plotly::plot_ly(data = fi_df,
                      x = ~Importance, y = ~Feature,
                      type = "bar", orientation = "h",
                      marker = list(color = ACCENT_COLOR)) |>
        plotly::layout(
          title = "Feature Importance (Top 15)",
          xaxis = list(title = "Importance"),
          yaxis = list(title = ""),
          paper_bgcolor = "rgba(0,0,0,0)",
          plot_bgcolor = "rgba(0,0,0,0)",
          font = list(color = "#E5E7EB"),
          margin = list(l = 150)
        )
    })
  })
}

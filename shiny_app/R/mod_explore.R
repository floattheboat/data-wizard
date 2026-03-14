# Step 2: Explore Data Module

mod_explore_ui <- function(id) {
  ns <- shiny::NS(id)

  shiny::tagList(
    # Overview cards row
    shiny::uiOutput(ns("overview_cards")),

    bslib::layout_columns(
      col_widths = c(4, 8),

      # Left: Column list
      bslib::card(
        bslib::card_header("Columns"),
        bslib::card_body(
          style = "max-height: 600px; overflow-y: auto;",
          shiny::uiOutput(ns("column_cards"))
        )
      ),

      # Right: Charts
      bslib::card(
        bslib::card_header(
          shiny::div(
            class = "d-flex justify-content-between align-items-center",
            shiny::textOutput(ns("chart_title"), inline = TRUE),
            shiny::radioButtons(ns("chart_type"), NULL,
                                choices = c("Histogram" = "histogram",
                                            "Box Plot" = "boxplot",
                                            "Bar Chart" = "bar",
                                            "Correlation" = "correlation"),
                                selected = "histogram", inline = TRUE)
          )
        ),
        bslib::card_body(
          plotly::plotlyOutput(ns("chart"), height = "500px")
        )
      )
    ),

    shiny::div(
      class = "d-flex justify-content-end mt-3",
      shiny::actionButton(ns("proceed"), "Proceed to Missing Values",
                          class = "btn-primary btn-lg", icon = shiny::icon("arrow-right"))
    )
  )
}

mod_explore_server <- function(id, store) {
  shiny::moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Internal reactive for analysis results
    analysis <- shiny::reactive({
      req(store$df)
      analyze_dataframe(store$df)
    })

    selected_col <- shiny::reactiveVal(NULL)

    # Overview cards
    output$overview_cards <- shiny::renderUI({
      req(analysis())
      ov <- analysis()$overview

      bslib::layout_columns(
        col_widths = c(3, 3, 3, 3),
        bslib::value_box(
          title = "Rows", value = format(ov$rows, big.mark = ","),
          theme = bslib::value_box_theme(bg = ACCENT_COLOR),
          showcase = shiny::icon("table")
        ),
        bslib::value_box(
          title = "Columns", value = ov$cols,
          theme = bslib::value_box_theme(bg = SUCCESS_COLOR),
          showcase = shiny::icon("columns")
        ),
        bslib::value_box(
          title = "Missing", value = paste0(format(ov$total_missing, big.mark = ","), " (", ov$missing_pct, "%)"),
          theme = bslib::value_box_theme(bg = if (ov$total_missing > 0) WARNING_COLOR else SUCCESS_COLOR),
          showcase = shiny::icon("question")
        ),
        bslib::value_box(
          title = "Memory", value = paste0(ov$memory_mb, " MB"),
          theme = bslib::value_box_theme(bg = "#6366F1"),
          showcase = shiny::icon("memory")
        )
      )
    })

    # Column cards
    output$column_cards <- shiny::renderUI({
      req(analysis())
      cols <- analysis()$columns

      cards <- lapply(cols, function(cs) {
        type_badge <- switch(cs$inferred_type,
          numeric = shiny::span(class = "badge bg-primary", "Numeric"),
          categorical = shiny::span(class = "badge bg-success", "Categorical"),
          datetime = shiny::span(class = "badge bg-info", "Datetime"),
          boolean = shiny::span(class = "badge bg-warning", "Boolean"),
          text = shiny::span(class = "badge bg-secondary", "Text"),
          shiny::span(class = "badge bg-dark", cs$inferred_type)
        )

        missing_text <- if (cs$missing > 0) {
          shiny::span(class = "text-warning", paste0(cs$missing, " missing (", cs$missing_pct, "%)"))
        } else {
          shiny::span(class = "text-success", "No missing")
        }

        detail_text <- if (cs$inferred_type == "numeric" && !is.null(cs$mean)) {
          paste0("Mean: ", round(cs$mean, 2), " | Median: ", round(cs$median, 2),
                 " | Std: ", round(cs$std, 2))
        } else if (cs$inferred_type %in% c("categorical", "text") && !is.null(cs$most_common)) {
          paste0("Most common: ", cs$most_common, " (", cs$most_common_count, ")")
        } else if (cs$inferred_type == "datetime" && !is.null(cs$min_date)) {
          paste0(cs$min_date, " to ", cs$max_date)
        } else {
          paste0(cs$unique, " unique values")
        }

        shiny::actionLink(
          ns(paste0("col_", cs$name)),
          shiny::div(
            class = "card mb-2 p-2",
            style = "cursor: pointer; border: 1px solid #4B5563;",
            shiny::div(class = "d-flex justify-content-between", shiny::strong(cs$name), type_badge),
            shiny::div(class = "small text-muted", detail_text),
            shiny::div(class = "small", missing_text)
          )
        )
      })

      # Register observers for column clicks
      lapply(cols, function(cs) {
        shiny::observeEvent(input[[paste0("col_", cs$name)]], {
          selected_col(cs$name)
        }, ignoreInit = TRUE)
      })

      shiny::tagList(cards)
    })

    # Chart title
    output$chart_title <- shiny::renderText({
      col <- selected_col()
      if (is.null(col)) "Select a column" else paste("Chart:", col)
    })

    # Main chart
    output$chart <- plotly::renderPlotly({
      req(store$df)

      chart_type <- input$chart_type

      if (chart_type == "correlation") {
        # Correlation heatmap
        cor_mat <- compute_correlation(store$df)
        req(cor_mat)

        plotly::plot_ly(
          x = colnames(cor_mat), y = rownames(cor_mat), z = cor_mat,
          type = "heatmap",
          colorscale = list(c(0, "#EF4444"), c(0.5, "#1F2937"), c(1, "#3B82F6")),
          zmin = -1, zmax = 1
        ) |>
          plotly::layout(
            title = "Correlation Matrix",
            xaxis = list(tickangle = 45),
            paper_bgcolor = "rgba(0,0,0,0)",
            plot_bgcolor = "rgba(0,0,0,0)",
            font = list(color = "#E5E7EB")
          )
      } else {
        col <- selected_col()
        req(col, col %in% names(store$df))
        vals <- store$df[[col]]
        col_type <- classify_column(vals)

        if (chart_type == "histogram") {
          if (col_type == "numeric") {
            numeric_vals <- if (is.numeric(vals)) vals else suppressWarnings(as.numeric(vals))
            plotly::plot_ly(x = numeric_vals[!is.na(numeric_vals)], type = "histogram",
                           marker = list(color = ACCENT_COLOR)) |>
              plotly::layout(title = paste("Distribution of", col),
                             xaxis = list(title = col), yaxis = list(title = "Count"),
                             paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                             font = list(color = "#E5E7EB"))
          } else if (col_type %in% c("categorical", "boolean")) {
            tbl <- sort(table(vals), decreasing = TRUE)
            plotly::plot_ly(x = names(tbl), y = as.numeric(tbl), type = "bar",
                           marker = list(color = ACCENT_COLOR)) |>
              plotly::layout(title = paste("Distribution of", col),
                             xaxis = list(title = col), yaxis = list(title = "Count"),
                             paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                             font = list(color = "#E5E7EB"))
          } else {
            plotly::plotly_empty() |>
              plotly::layout(title = "Histogram not available for this column type",
                             paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                             font = list(color = "#E5E7EB"))
          }

        } else if (chart_type == "boxplot") {
          if (col_type == "numeric") {
            numeric_vals <- if (is.numeric(vals)) vals else suppressWarnings(as.numeric(vals))
            plotly::plot_ly(y = numeric_vals[!is.na(numeric_vals)], type = "box",
                           marker = list(color = ACCENT_COLOR),
                           line = list(color = ACCENT_COLOR)) |>
              plotly::layout(title = paste("Box Plot of", col),
                             yaxis = list(title = col),
                             paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                             font = list(color = "#E5E7EB"))
          } else {
            plotly::plotly_empty() |>
              plotly::layout(title = "Box plot requires numeric column",
                             paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                             font = list(color = "#E5E7EB"))
          }

        } else if (chart_type == "bar") {
          tbl <- sort(table(vals), decreasing = TRUE)
          tbl <- head(tbl, 20)  # Top 20 values
          plotly::plot_ly(x = names(tbl), y = as.numeric(tbl), type = "bar",
                         marker = list(color = ACCENT_COLOR)) |>
            plotly::layout(title = paste("Top Values of", col),
                           xaxis = list(title = col, tickangle = 45),
                           yaxis = list(title = "Count"),
                           paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
                           font = list(color = "#E5E7EB"))
        }
      }
    })

    # Proceed
    shiny::observeEvent(input$proceed, {
      req(store$df)
      store$max_unlocked <- max(store$max_unlocked, 3L)
      store$current_step <- 3L
    })
  })
}

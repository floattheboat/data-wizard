# Data Wizard - R Shiny Port
# Entry point: UI + server + module wiring

# Allow large file uploads (500 MB)
options(shiny.maxRequestSize = 500 * 1024^2)

# Load required packages
library(shiny)
library(bslib)
library(DT)
library(plotly)
library(dplyr)
library(tidyr)
library(readr)
library(readxl)
library(writexl)
library(jsonlite)
library(arrow)
library(DBI)
library(RSQLite)
# Optional DB drivers (loaded on demand by utils_db.R)
# library(RPostgres)  # install if PostgreSQL support needed
# library(RMySQL)     # install if MySQL support needed
library(e1071)
library(zoo)
library(lubridate)
library(parsnip)
library(recipes)
library(workflows)
library(rsample)
library(yardstick)
library(vip)
library(ranger)
library(xgboost)
library(kknn)
library(glmnet)
library(rpart)
library(kernlab)

# Source utility and module files
source("R/utils_constants.R")
source("R/utils_type_detection.R")
source("R/utils_analyzer.R")
source("R/utils_missing.R")
source("R/utils_outlier.R")
source("R/utils_ml.R")
source("R/utils_db.R")
source("R/utils_export.R")
source("R/mod_load.R")
source("R/mod_explore.R")
source("R/mod_missing.R")
source("R/mod_outlier.R")
source("R/mod_export.R")
source("R/mod_ml.R")

# --- UI ---
ui <- bslib::page_sidebar(
  title = "Data Wizard",
  theme = bslib::bs_theme(
    version = 5,
    bootswatch = "darkly",
    primary = ACCENT_COLOR,
    success = SUCCESS_COLOR,
    warning = WARNING_COLOR,
    danger = DANGER_COLOR,
    bg = "#111827",
    fg = "#E5E7EB"
  ),
  tags$head(tags$link(rel = "stylesheet", href = "custom.css")),

  # Sidebar with step navigation
  sidebar = bslib::sidebar(
    width = 250,
    tags$div(class = "sidebar-title", icon("hat-wizard"), " Data Wizard"),
    uiOutput("step_buttons")
  ),

  # Main content: hidden navset with one panel per step
  bslib::navset_hidden(
    id = "wizard_panels",
    bslib::nav_panel_hidden("step_1", mod_load_ui("load")),
    bslib::nav_panel_hidden("step_2", mod_explore_ui("explore")),
    bslib::nav_panel_hidden("step_3", mod_missing_ui("missing")),
    bslib::nav_panel_hidden("step_4", mod_outlier_ui("outlier")),
    bslib::nav_panel_hidden("step_5", mod_export_ui("export")),
    bslib::nav_panel_hidden("step_6", mod_ml_ui("ml"))
  ),

  # Status bar footer
  tags$div(
    class = "status-bar",
    tags$span(class = "status-item", icon("table"), textOutput("status_shape", inline = TRUE)),
    tags$span(class = "status-item", icon("memory"), textOutput("status_memory", inline = TRUE)),
    tags$span(class = "status-item", icon("clock"), textOutput("status_time", inline = TRUE))
  )
)

# --- Server ---
server <- function(input, output, session) {

  # Central reactive state (replaces DataStore singleton)
  store <- reactiveValues(
    df = NULL,
    original_df = NULL,
    undo_stack = list(),
    operations = list(),
    source_info = list(),
    max_unlocked = 1L,
    current_step = 1L
  )

  # Step navigation buttons
  output$step_buttons <- renderUI({
    buttons <- lapply(STEPS, function(step) {
      is_active <- store$current_step == step$id
      is_unlocked <- step$id <= store$max_unlocked
      is_completed <- step$id < store$max_unlocked

      css_class <- paste("step-btn",
                         if (is_active) "step-active" else "",
                         if (!is_unlocked) "step-disabled" else "",
                         if (is_completed) "step-completed" else "")

      actionLink(
        paste0("step_nav_", step$id),
        tagList(
          span(class = "step-number", step$id),
          step$name
        ),
        class = css_class
      )
    })
    tagList(buttons)
  })

  # Step navigation click handlers
  lapply(STEPS, function(step) {
    observeEvent(input[[paste0("step_nav_", step$id)]], {
      if (step$id <= store$max_unlocked) {
        store$current_step <- step$id
      }
    })
  })

  # Switch visible panel when current_step changes
  observeEvent(store$current_step, {
    bslib::nav_select("wizard_panels", paste0("step_", store$current_step), session = session)
  })

  # Status bar outputs
  output$status_shape <- renderText({
    if (is.null(store$df)) "No data loaded"
    else paste0(format(nrow(store$df), big.mark = ","), " rows x ", ncol(store$df), " cols")
  })

  output$status_memory <- renderText({
    if (is.null(store$df)) "0 MB"
    else paste0(round(as.numeric(object.size(store$df)) / 1024^2, 2), " MB")
  })

  output$status_time <- renderText({
    format(Sys.time(), "%H:%M:%S")
  })

  # Wire up module servers
  mod_load_server("load", store)
  mod_explore_server("explore", store)
  mod_missing_server("missing", store)
  mod_outlier_server("outlier", store)
  mod_export_server("export", store)
  mod_ml_server("ml", store)
}

shinyApp(ui, server)

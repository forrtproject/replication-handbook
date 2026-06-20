#!/usr/bin/env Rscript
# Regenerate Figure 1.1 — number of replication studies by publication year —
# from the FORRT Library of Replication Attempts (FLoRA).
#
# Data source: forrtproject/fred-data, output/flora.csv
#   (https://github.com/forrtproject/fred-data). The column `year_r` holds the
#   replication's publication year (`year_o` = the original study's year).
#   We use the full export rather than flora_filtered.csv: as of this snapshot the
#   filtered set under-counts 2023 (96 vs 239 in the full export), which would
#   create a misleading dip. The full export gives the true growth trend.
#
# FLoRA is updated continuously, so this script pins a snapshot by writing the
# aggregated counts to data/flora_replication_counts.csv. The book reads that
# committed CSV (see the R chunk in background.qmd), so rendering is
# deterministic and offline. Re-run this script to refresh the snapshot.
#
# Usage:  Rscript R/fig_replication_growth.R     (run from the repo root)

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(ggplot2)
})

source("R/plot_replication_growth.R")

flora_url <- "https://raw.githubusercontent.com/forrtproject/fred-data/main/output/flora.csv"
out_csv   <- "data/flora_replication_counts.csv"
out_png   <- "images/replication_growth.png"
max_year  <- 2025  # exclude the current, still-incomplete year

flora <- readr::read_csv(flora_url, show_col_types = FALSE)

counts <- flora |>
  dplyr::mutate(year = suppressWarnings(as.integer(substr(year_r, 1, 4)))) |>
  dplyr::filter(!is.na(year), year <= max_year) |>
  dplyr::count(year, name = "n") |>
  dplyr::arrange(year)

readr::write_csv(counts, out_csv)
ggplot2::ggsave(out_png, plot_replication_growth(counts),
                width = 8, height = 6, dpi = 150)

message(sprintf("Snapshot %s: %d replications across %d years (%d-%d). Wrote %s and %s.",
                Sys.Date(), sum(counts$n), nrow(counts),
                min(counts$year), max(counts$year), out_csv, out_png))

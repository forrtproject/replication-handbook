# Plot helper for Figure 1.1 (number of replication studies by publication year).
# Sourced both by R/fig_replication_growth.R (to write images/replication_growth.png)
# and by the R chunk in background.qmd (to render the figure at build time), so the
# figure definition lives in exactly one place.

plot_replication_growth <- function(counts) {
  # The FLoRA snapshot only stores years that actually have replications, so the
  # raw data skips early gap years (e.g. 1971-1975). Fill the gaps with 0 so the
  # x-axis is a continuous, evenly spaced timeline rather than a list of present
  # years squashed together.
  counts <- counts[order(counts$year), ]
  years  <- seq(min(counts$year), max(counts$year))
  full   <- merge(data.frame(year = years), counts, by = "year", all.x = TRUE)
  full$n[is.na(full$n)] <- 0

  ggplot2::ggplot(full, ggplot2::aes(x = year, y = n)) +
    ggplot2::geom_col(fill = "#0079A3", width = 0.85) +
    ggplot2::scale_x_continuous(
      breaks = seq(1950, 2030, by = 10),
      expand = ggplot2::expansion(mult = c(0.01, 0.01))
    ) +
    ggplot2::scale_y_continuous(expand = ggplot2::expansion(mult = c(0, 0.05))) +
    ggplot2::labs(x = "Year of publication", y = "Number of replication studies") +
    ggplot2::theme_minimal(base_size = 13) +
    ggplot2::theme(
      panel.grid.major.x = ggplot2::element_blank(),
      panel.grid.minor   = ggplot2::element_blank(),
      axis.text          = ggplot2::element_text(color = "grey20"),
      axis.title         = ggplot2::element_text(color = "grey20"),
      axis.title.x       = ggplot2::element_text(margin = ggplot2::margin(t = 8)),
      axis.title.y       = ggplot2::element_text(margin = ggplot2::margin(r = 8)),
      plot.background    = ggplot2::element_rect(fill = "#fefdf6", color = NA),
      panel.background   = ggplot2::element_rect(fill = "#fefdf6", color = NA),
      plot.margin        = ggplot2::margin(10, 12, 6, 6)
    )
}

# Plot helper for Figure 1.1 (number of replication studies by publication year).
# Sourced both by R/fig_replication_growth.R (to write images/replication_growth.png)
# and by the R chunk in background.qmd (to render the figure at build time), so the
# figure definition lives in exactly one place.

plot_replication_growth <- function(counts) {
  ggplot2::ggplot(counts, ggplot2::aes(x = factor(year), y = n)) +
    ggplot2::geom_col(fill = "grey40", width = 0.8) +
    ggplot2::labs(x = "Replication Publication Year", y = "Number of Publications") +
    ggplot2::theme_minimal(base_size = 13) +
    ggplot2::theme(
      panel.grid.major.x = ggplot2::element_blank(),
      panel.grid.minor   = ggplot2::element_blank(),
      axis.text.x        = ggplot2::element_text(angle = 90, vjust = 0.5, hjust = 1)
    )
}

"""
Visualization utilities for parqv views.

Provides text-based data visualization functions like ASCII histograms.
"""
import math
from typing import List, Union, Optional

TICK_CHARS = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']


def create_text_histogram(
        data: List[Union[int, float]],
        bins: int = 15,
        width: int = 60,
        height: int = 8,
        title: Optional[str] = None
) -> List[str]:
    """
    Create a professional, text-based histogram from numerical data.

    Args:
        data: List of numerical values.
        bins: The number of bins for the histogram.
        width: The total character width of the output histogram.
        height: The maximum height of the histogram bars in lines.
        title: An optional title for the histogram.

    Returns:
        A list of strings representing the histogram, ready for printing.
    """
    if not data:
        return ["(No data available for histogram)"]

    # 1. Sanitize the input data
    clean_data = [float(val) for val in data if isinstance(val, (int, float)) and math.isfinite(val)]

    if not clean_data:
        return ["(No valid numerical data to plot)"]

    min_val, max_val = min(clean_data), max(clean_data)

    if min_val == max_val:
        return [f"(All values are identical: {_format_number(min_val)})"]

    # 2. Create bins and count frequencies
    # Add a small epsilon to the range to ensure max_val falls into the last bin
    epsilon = (max_val - min_val) / 1e9
    value_range = (max_val - min_val) + epsilon
    bin_width = value_range / bins

    bin_counts = [0] * bins
    for value in clean_data:
        bin_index = int((value - min_val) / bin_width)
        bin_counts[bin_index] += 1

    # 3. Render the histogram
    return _render_histogram(
        bin_counts=bin_counts,
        min_val=min_val,
        max_val=max_val,
        width=width,
        height=height,
        title=title
    )


def _render_histogram(
        bin_counts: List[int],
        min_val: float,
        max_val: float,
        width: int,
        height: int,
        title: Optional[str]
) -> List[str]:
    """
    Internal function to render the histogram components into ASCII art.
    """
    lines = []
    if title:
        lines.append(title.center(width))

    max_count = max(bin_counts) if bin_counts else 0
    if max_count == 0:
        return lines + ["(No data falls within histogram bins)"]

    # --- Layout Calculations ---
    y_axis_width = len(str(max_count))
    plot_width = width - y_axis_width - 3  # Reserve space for "| " and axis
    if plot_width <= 0:
        return ["(Terminal width too narrow to draw histogram)"]

    # Resample the data bins to fit the available plot_width.
    # This stretches or shrinks the histogram to match the screen space.
    display_bins = []
    num_data_bins = len(bin_counts)
    for i in range(plot_width):
        # Find the corresponding data bin for this screen column
        data_bin_index = int(i * num_data_bins / plot_width)
        display_bins.append(bin_counts[data_bin_index])

    # --- Y-Axis and Bars (Top to Bottom) ---
    for row in range(height, -1, -1):
        line = ""
        # Y-axis labels
        if row == height:
            line += f"{max_count:<{y_axis_width}} | "
        elif row == 0:
            line += f"{0:<{y_axis_width}} +-"
        else:
            line += " " * y_axis_width + " | "

        # Bars - now iterate over the resampled display_bins
        for count in display_bins:
            # Scale current count to the available height
            scaled_height = (count / max_count) * height

            # Determine character based on height relative to current row
            if scaled_height >= row:
                line += TICK_CHARS[-1]  # Full block for the solid part of the bar
            elif scaled_height > row - 1:
                # This is the top of the bar, use a partial character
                partial_index = int((scaled_height - row + 1) * (len(TICK_CHARS) - 1))
                line += TICK_CHARS[max(0, partial_index)]
            elif row == 0:
                line += "-"  # X-axis line
            else:
                line += " "  # Empty space above the bar

        lines.append(line)

    # --- X-Axis Labels ---
    x_axis_labels = _create_x_axis_labels(min_val, max_val, plot_width)
    label_line = " " * (y_axis_width + 3) + x_axis_labels
    lines.append(label_line)

    return lines


def _create_x_axis_labels(min_val: float, max_val: float, plot_width: int) -> str:
    """Create a formatted string for the X-axis labels."""
    min_label = _format_number(min_val)
    max_label = _format_number(max_val)

    available_width = plot_width - len(min_label) - len(max_label)

    if available_width < 4:
        return f"{min_label}{' ' * (plot_width - len(min_label) - len(max_label))}{max_label}"

    mid_val = (min_val + max_val) / 2
    mid_label = _format_number(mid_val)

    spacing1 = (plot_width // 2) - len(min_label) - (len(mid_label) // 2)
    spacing2 = (plot_width - (plot_width // 2)) - (len(mid_label) - (len(mid_label) // 2)) - len(max_label)

    if spacing1 < 1 or spacing2 < 1:
        return f"{min_label}{' ' * (plot_width - len(min_label) - len(max_label))}{max_label}"

    return f"{min_label}{' ' * spacing1}{mid_label}{' ' * spacing2}{max_label}"


def _format_number(value: float) -> str:
    """Format a number nicely for display on an axis."""
    if abs(value) < 1e-4 and value != 0:
        return f"{value:.1e}"
    if abs(value) >= 1e5:
        return f"{value:.1e}"
    if math.isclose(value, int(value)):
        return str(int(value))
    if abs(value) < 10:
        return f"{value:.2f}"
    if abs(value) < 100:
        return f"{value:.1f}"
    return str(int(value))


def should_show_histogram(data_type: str, distinct_count: int, total_count: int) -> bool:
    """
    Determine if a histogram should be shown for this data.
    This function uses a set of heuristics to decide if the data is
    continuous enough to warrant a histogram visualization.
    """
    # 1. Type Check: Histograms are only meaningful for numeric data.
    if 'numeric' not in data_type and 'integer' not in data_type and 'float' not in data_type:
        return False

    # 2. Data Volume Check: Don't render if there's too little data or no variation.
    if total_count < 20 or distinct_count <= 1:
        return False

    # 3. Categorical Data Filter: If the number of distinct values is very low,
    #    treat it as categorical data (e.g., ratings from 1-10, months 1-12).
    if distinct_count < 15:
        return False

    # 4. High Cardinality Filter: If almost every value is unique (like an ID or index),
    #    a histogram is not useful as most bars would have a height of 1.
    distinct_ratio = distinct_count / total_count
    if distinct_ratio > 0.95:
        return False

    # 5. Pass: If the data passes all the above filters, it is considered
    #    sufficiently continuous to be visualized with a histogram.
    return True

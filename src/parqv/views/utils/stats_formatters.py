"""
Statistics formatting utilities for parqv views.
"""

from typing import Any, Dict, List, Union

from rich.text import Text


def format_stats_for_display(stats_data: Dict[str, Any]) -> List[Union[str, Text]]:
    """
    Format statistics dictionary for display as lines of rich text.
    
    Args:
        stats_data: Raw statistics dictionary from handler
        
    Returns:
        List of formatted lines ready for display
    """
    if not stats_data:
        return [Text.from_markup("[red]No statistics data available.[/red]")]

    lines: List[Union[str, Text]] = []
    
    # Extract basic column information
    col_name = stats_data.get("column", "N/A")
    col_type = stats_data.get("type", "Unknown")
    nullable_val = stats_data.get("nullable")

    # Format column header
    lines.extend(_format_column_header(col_name, col_type, nullable_val))
    
    # Handle calculation errors
    calc_error = stats_data.get("error")
    if calc_error:
        lines.extend(_format_error_section(calc_error))
    
    # Add informational messages
    message = stats_data.get("message")
    if message:
        lines.extend(_format_message_section(message))
    
    # Format calculated statistics
    calculated = stats_data.get("calculated")
    if calculated:
        lines.extend(_format_calculated_stats(calculated, has_error=bool(calc_error)))
    
    return lines


def format_column_info(column_name: str, column_type: str, nullable: Any) -> List[Union[str, Text]]:
    """
    Format basic column information for display.
    
    Args:
        column_name: Name of the column
        column_type: Type of the column
        nullable: Nullability information
        
    Returns:
        List of formatted lines for column info
    """
    return _format_column_header(column_name, column_type, nullable)


def _format_column_header(col_name: str, col_type: str, nullable_val: Any) -> List[Union[str, Text]]:
    """Format the column header section."""
    # Determine nullability display
    if nullable_val is True:
        nullable_str = "Nullable"
    elif nullable_val is False:
        nullable_str = "Required"
    else:
        nullable_str = "Unknown Nullability"
    
    lines = [
        Text.assemble(("Column: ", "bold"), f"`{col_name}`"),
        Text.assemble(("Type:   ", "bold"), f"{col_type} ({nullable_str})"),
        "─" * (len(col_name) + len(col_type) + 20)
    ]
    
    return lines


def _format_error_section(calc_error: str) -> List[Union[str, Text]]:
    """Format the error section."""
    return [
        Text("Calculation Error:", style="bold red"),
        f"```\n{calc_error}\n```",
        ""
    ]


def _format_message_section(message: str) -> List[Union[str, Text]]:
    """Format the informational message section."""
    return [
        Text(f"Info: {message}", style="italic cyan"),
        ""
    ]


def _format_calculated_stats(calculated: Dict[str, Any], has_error: bool = False) -> List[Union[str, Text]]:
    """Format the calculated statistics section."""
    lines = [Text("Calculated Statistics:", style="bold")]
    
    # Define the order of statistics to display
    stats_order = [
        "Total Count", "Valid Count", "Null Count", "Null Percentage",
        "Distinct Count", "Distinct Values (Approx)",
        "Min", "Max", "Mean", "Median (50%)", "StdDev", "Variance",
        "True Count", "False Count",
        "Value Counts"
    ]
    
    found_stats = False
    
    for key in stats_order:
        if key in calculated:
            found_stats = True
            value = calculated[key]
            lines.extend(_format_single_stat(key, value))
    
    # Add any additional stats not in the predefined order
    for key, value in calculated.items():
        if key not in stats_order:
            found_stats = True
            lines.extend(_format_single_stat(key, value))
    
    # Handle case where no stats were found
    if not found_stats and not has_error:
        lines.append(Text("  (No specific stats calculated for this type)", style="dim"))
    
    return lines


def _format_single_stat(key: str, value: Any) -> List[Union[str, Text]]:
    """Format a single statistic entry."""
    lines = []
    
    if key == "Value Counts" and isinstance(value, dict):
        lines.append(f"  - {key}:")
        for sub_key, sub_val in value.items():
            sub_val_str = _format_stat_value(sub_val)
            lines.append(f"    - {sub_key}: {sub_val_str}")
    else:
        formatted_value = _format_stat_value(value)
        lines.append(f"  - {key}: {formatted_value}")
    
    return lines


def _format_stat_value(value: Any) -> str:
    """Format a single statistic value."""
    if isinstance(value, (int, float)):
        if isinstance(value, int):
            return f"{value:,}"
        else:
            return f"{value:,.4f}"
    else:
        return str(value) 
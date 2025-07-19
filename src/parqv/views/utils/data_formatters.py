"""
Data formatting utilities for parqv views.
"""

from typing import Any, Dict, Union
from rich.text import Text


def format_metadata_for_display(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format metadata dictionary for consistent display.
    
    Args:
        metadata: Raw metadata dictionary from handler
        
    Returns:
        Formatted metadata dictionary ready for display
    """
    if not metadata:
        return {"Error": "No metadata available"}
    
    # Check for error in metadata
    if "error" in metadata:
        return {"Error": metadata["error"]}
    
    formatted = {}
    
    # Format specific known fields with better presentation
    field_formatters = {
        "File Path": lambda x: str(x),
        "Format": lambda x: str(x).upper(),
        "Total Rows": lambda x: _format_number(x),
        "Columns": lambda x: _format_number(x),
        "Size": lambda x: _format_size_if_bytes(x),
        "DuckDB View": lambda x: f"`{x}`" if x else "N/A",
    }
    
    for key, value in metadata.items():
        if key in field_formatters:
            formatted[key] = field_formatters[key](value)
        else:
            formatted[key] = format_value_for_display(value)
    
    return formatted


def format_value_for_display(value: Any) -> str:
    """
    Format a single value for display in the UI.
    
    Args:
        value: The value to format
        
    Returns:
        String representation suitable for display
    """
    if value is None:
        return "N/A"
    
    if isinstance(value, (int, float)):
        return _format_number(value)
    
    if isinstance(value, bool):
        return "Yes" if value else "No"
    
    if isinstance(value, str):
        # Handle empty strings
        if not value.strip():
            return "N/A"
        return value
    
    # For other types, convert to string
    return str(value)


def _format_number(value: Union[str, int, float]) -> str:
    """
    Format numbers with thousand separators.
    
    Args:
        value: Numeric value or string representation
        
    Returns:
        Formatted number string
    """
    if isinstance(value, str):
        # Try to extract number from string like "1,234" or "1234"
        try:
            # Remove existing commas and convert
            clean_str = value.replace(",", "").strip()
            if clean_str.isdigit():
                return f"{int(clean_str):,}"
            elif "." in clean_str:
                return f"{float(clean_str):,.2f}"
            else:
                return value  # Return as-is if not numeric
        except (ValueError, AttributeError):
            return value
    
    if isinstance(value, int):
        return f"{value:,}"
    
    if isinstance(value, float):
        return f"{value:,.2f}"
    
    return str(value)


def _format_size_if_bytes(value: Union[str, int]) -> str:
    """
    Format size values, detecting if they represent bytes.
    
    Args:
        value: Size value that might be in bytes
        
    Returns:
        Formatted size string
    """
    if isinstance(value, str):
        # If it already contains size units, return as-is
        if any(unit in value.lower() for unit in ["kb", "mb", "gb", "tb", "bytes"]):
            return value
        
        # Try to parse as number and format as bytes
        try:
            clean_str = value.replace(",", "").strip()
            if "bytes" in value.lower():
                num_bytes = int(clean_str.split()[0])
                return _format_bytes(num_bytes)
            else:
                return value
        except (ValueError, IndexError):
            return value
    
    if isinstance(value, int):
        # Assume it's bytes if it's a large integer
        if value > 1024:
            return _format_bytes(value)
        else:
            return f"{value:,}"
    
    return str(value)


def _format_bytes(num_bytes: int) -> str:
    """
    Format bytes into human-readable format.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Human-readable size string
    """
    if num_bytes < 1024:
        return f"{num_bytes:,} bytes"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{num_bytes / 1024 ** 3:.1f} GB" 
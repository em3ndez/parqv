"""
Views package for parqv application.

This package contains all UI views and their supporting components and utilities.
"""

# Main views
from .metadata_view import MetadataView
from .data_view import DataView
from .schema_view import SchemaView

# Base classes
from .base import BaseView

# Components (optional, for advanced usage)
from .components import ErrorDisplay, LoadingDisplay, EnhancedDataTable

# Utilities (optional, for advanced usage)
from .utils import format_metadata_for_display, format_stats_for_display

__all__ = [
    # Main views - these are the primary exports
    "MetadataView",
    "DataView", 
    "SchemaView",
    
    # Base class - for extending functionality
    "BaseView",
    
    # Components - for custom view development
    "ErrorDisplay",
    "LoadingDisplay",
    "EnhancedDataTable",
    
    # Utilities - for data formatting
    "format_metadata_for_display",
    "format_stats_for_display",
]

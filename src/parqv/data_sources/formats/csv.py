"""
CSV file handler for parqv data sources.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..base import DataHandler, DataHandlerError


class CsvHandlerError(DataHandlerError):
    """Custom exception for CSV handling errors."""
    pass


class CsvHandler(DataHandler):
    """
    Handles CSV file interactions using pandas.
    
    Provides methods to access metadata, schema, data preview, and column statistics
    for CSV files using pandas DataFrame operations.
    """

    def __init__(self, file_path: Path):
        """
        Initialize the CsvHandler by validating the path and reading the CSV file.

        Args:
            file_path: Path to the CSV file.

        Raises:
            CsvHandlerError: If the file is not found, not a file, or cannot be read.
        """
        super().__init__(file_path)
        self.df: Optional[pd.DataFrame] = None
        self._original_dtypes: Optional[Dict[str, str]] = None

        try:
            # Validate file existence
            if not self.file_path.is_file():
                raise FileNotFoundError(f"CSV file not found or is not a regular file: {self.file_path}")

            # Read the CSV file with pandas
            self._read_csv_file()

            self.logger.info(f"Successfully initialized CsvHandler for: {self.file_path.name}")

        except FileNotFoundError as fnf_e:
            self.logger.error(f"File not found during CsvHandler initialization: {fnf_e}")
            raise CsvHandlerError(str(fnf_e)) from fnf_e
        except pd.errors.EmptyDataError as empty_e:
            self.logger.error(f"CSV file is empty: {empty_e}")
            raise CsvHandlerError(f"CSV file '{self.file_path.name}' is empty") from empty_e
        except pd.errors.ParserError as parse_e:
            self.logger.error(f"CSV parsing error: {parse_e}")
            raise CsvHandlerError(f"Failed to parse CSV file '{self.file_path.name}': {parse_e}") from parse_e
        except Exception as e:
            self.logger.exception(f"Unexpected error initializing CsvHandler for {self.file_path.name}")
            raise CsvHandlerError(f"Failed to initialize CSV handler '{self.file_path.name}': {e}") from e

    def _read_csv_file(self) -> None:
        """Read the CSV file using pandas with appropriate settings."""
        try:
            # Read CSV with automatic type inference
            self.df = pd.read_csv(
                self.file_path,
                # Basic settings
                encoding='utf-8',
                # Handle various separators automatically
                sep=None,  # Let pandas auto-detect
                engine='python',  # More flexible parsing
                # Preserve original string representation for better type info
                dtype=str,  # Read everything as string first
                na_values=['', 'NULL', 'null', 'None', 'N/A', 'n/a', 'NaN', 'nan'],
                keep_default_na=True,
            )

            # Store original dtypes before conversion
            self._original_dtypes = {col: 'string' for col in self.df.columns}

            # Try to infer better types
            self._infer_types()

            self.logger.debug(f"Successfully read CSV with shape: {self.df.shape}")

        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    self.logger.warning(f"Trying encoding: {encoding}")
                    self.df = pd.read_csv(
                        self.file_path,
                        encoding=encoding,
                        sep=None,
                        engine='python',
                        dtype=str,
                        na_values=['', 'NULL', 'null', 'None', 'N/A', 'n/a', 'NaN', 'nan'],
                        keep_default_na=True,
                    )
                    self._original_dtypes = {col: 'string' for col in self.df.columns}
                    self._infer_types()
                    self.logger.info(f"Successfully read CSV with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise CsvHandlerError(f"Could not decode CSV file with any common encoding")

    def _infer_types(self) -> None:
        """Infer appropriate data types for columns."""
        if self.df is None:
            return

        for col in self.df.columns:
            # Try to convert to numeric
            numeric_converted = pd.to_numeric(self.df[col], errors='coerce')
            if not numeric_converted.isna().all():
                # If most values can be converted to numeric, use numeric type
                non_na_original = self.df[col].notna().sum()
                non_na_converted = numeric_converted.notna().sum()

                if non_na_converted / max(non_na_original, 1) > 0.8:  # 80% conversion success
                    self.df[col] = numeric_converted
                    if (numeric_converted == numeric_converted.astype('Int64', errors='ignore')).all():
                        self._original_dtypes[col] = 'integer'
                    else:
                        self._original_dtypes[col] = 'float'
                    continue

            # Try to convert to datetime
            try:
                datetime_converted = pd.to_datetime(self.df[col], errors='coerce', infer_datetime_format=True)
                if not datetime_converted.isna().all():
                    non_na_original = self.df[col].notna().sum()
                    non_na_converted = datetime_converted.notna().sum()

                    if non_na_converted / max(non_na_original, 1) > 0.8:  # 80% conversion success
                        self.df[col] = datetime_converted
                        self._original_dtypes[col] = 'datetime'
                        continue
            except (ValueError, TypeError):
                pass

            # Try to convert to boolean
            bool_values = self.df[col].str.lower().isin(['true', 'false', 't', 'f', '1', '0', 'yes', 'no', 'y', 'n'])
            if bool_values.sum() / len(self.df[col]) > 0.8:
                bool_mapping = {
                    'true': True, 'false': False, 't': True, 'f': False,
                    '1': True, '0': False, 'yes': True, 'no': False,
                    'y': True, 'n': False
                }
                self.df[col] = self.df[col].str.lower().map(bool_mapping)
                self._original_dtypes[col] = 'boolean'
                continue

            # Keep as string
            self._original_dtypes[col] = 'string'

    def close(self) -> None:
        """Close and cleanup resources (CSV data is held in memory)."""
        if self.df is not None:
            self.logger.info(f"Closed CSV handler for: {self.file_path.name}")
            self.df = None
            self._original_dtypes = None

    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Get a summary dictionary of the CSV file's metadata.

        Returns:
            A dictionary containing metadata like file path, format, row count, columns, size.
        """
        if self.df is None:
            return {"error": "CSV data not loaded or handler closed."}

        try:
            file_size = self.file_path.stat().st_size
            size_str = self.format_size(file_size)
        except Exception as e:
            self.logger.warning(f"Could not get file size for {self.file_path}: {e}")
            size_str = "N/A"

        # Create a well-structured metadata summary
        summary = {
            "File Information": {
                "Path": str(self.file_path),
                "Format": "CSV",
                "Size": size_str
            },
            "Data Structure": {
                "Total Rows": f"{len(self.df):,}",
                "Total Columns": f"{len(self.df.columns):,}",
                "Memory Usage": f"{self.df.memory_usage(deep=True).sum():,} bytes"
            },
            "Column Types Summary": self._get_column_types_summary()
        }

        return summary

    def _get_column_types_summary(self) -> Dict[str, int]:
        """Get a summary of column types in the CSV data."""
        if self.df is None or self._original_dtypes is None:
            return {}

        type_counts = {}
        for col_type in self._original_dtypes.values():
            type_counts[col_type] = type_counts.get(col_type, 0) + 1

        # Format for better display
        formatted_summary = {}
        type_labels = {
            'string': 'Text Columns',
            'integer': 'Integer Columns',
            'float': 'Numeric Columns',
            'datetime': 'Date/Time Columns',
            'boolean': 'Boolean Columns'
        }

        for type_key, count in type_counts.items():
            label = type_labels.get(type_key, f'{type_key.title()} Columns')
            formatted_summary[label] = f"{count:,}"

        return formatted_summary

    def get_schema_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the schema of the CSV data.

        Returns:
            A list of dictionaries describing columns (name, type, nullable),
            or None if schema couldn't be determined.
        """
        if self.df is None:
            self.logger.warning("DataFrame is not available for schema data")
            return None

        schema_list = []

        for col in self.df.columns:
            try:
                # Get the inferred type
                col_type = self._original_dtypes.get(col, 'string')

                # Check for null values
                has_nulls = self.df[col].isna().any()

                schema_list.append({
                    "name": str(col),
                    "type": col_type,
                    "nullable": bool(has_nulls)
                })

            except Exception as e:
                self.logger.error(f"Error processing column '{col}' for schema data: {e}")
                schema_list.append({
                    "name": str(col),
                    "type": f"[Error: {e}]",
                    "nullable": None
                })

        return schema_list

    def get_data_preview(self, num_rows: int = 50) -> Optional[pd.DataFrame]:
        """
        Fetch a preview of the data.

        Args:
            num_rows: The maximum number of rows to fetch.

        Returns:
            A pandas DataFrame with preview data, an empty DataFrame if no data,
            or a DataFrame with an 'error' column on failure.
        """
        if self.df is None:
            self.logger.warning("CSV data not available for preview")
            return pd.DataFrame({"error": ["CSV data not loaded or handler closed."]})

        try:
            if self.df.empty:
                self.logger.info("CSV file has no data rows")
                return pd.DataFrame(columns=self.df.columns)

            # Return first num_rows
            preview_df = self.df.head(num_rows).copy()
            self.logger.info(f"Generated preview of {len(preview_df)} rows for {self.file_path.name}")
            return preview_df

        except Exception as e:
            self.logger.exception(f"Error generating data preview from CSV file: {self.file_path.name}")
            return pd.DataFrame({"error": [f"Failed to generate preview: {e}"]})

    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        """
        Calculate and return statistics for a specific column.

        Args:
            column_name: The name of the column.

        Returns:
            A dictionary containing column statistics or error information.
        """
        if self.df is None:
            return self._create_stats_result(
                column_name, "Unknown", {}, error="CSV data not loaded or handler closed."
            )

        if column_name not in self.df.columns:
            return self._create_stats_result(
                column_name, "Unknown", {}, error=f"Column '{column_name}' not found in CSV data."
            )

        try:
            col_series = self.df[column_name]
            col_type = self._original_dtypes.get(column_name, 'string')

            # Basic counts
            total_count = len(col_series)
            null_count = col_series.isna().sum()
            valid_count = total_count - null_count
            null_percentage = (null_count / total_count * 100) if total_count > 0 else 0

            stats = {
                "Total Count": f"{total_count:,}",
                "Valid Count": f"{valid_count:,}",
                "Null Count": f"{null_count:,}",
                "Null Percentage": f"{null_percentage:.2f}%"
            }

            # Type-specific statistics
            if valid_count > 0:
                valid_series = col_series.dropna()

                # Distinct count (always applicable)
                distinct_count = valid_series.nunique()
                stats["Distinct Count"] = f"{distinct_count:,}"

                if col_type in ['integer', 'float']:
                    # Numeric statistics
                    stats.update(self._calculate_numeric_stats_pandas(valid_series))
                elif col_type == 'datetime':
                    # Datetime statistics
                    stats.update(self._calculate_datetime_stats_pandas(valid_series))
                elif col_type == 'boolean':
                    # Boolean statistics
                    stats.update(self._calculate_boolean_stats_pandas(valid_series))
                elif col_type == 'string':
                    # String statistics (min/max by alphabetical order)
                    stats.update(self._calculate_string_stats_pandas(valid_series))

            return self._create_stats_result(column_name, col_type, stats, nullable=null_count > 0)

        except Exception as e:
            self.logger.exception(f"Error calculating stats for column '{column_name}'")
            return self._create_stats_result(
                column_name, "Unknown", {}, error=f"Failed to calculate statistics: {e}"
            )

    def _calculate_numeric_stats_pandas(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate statistics for numeric columns using pandas."""
        stats = {}
        try:
            stats["Min"] = series.min()
            stats["Max"] = series.max()
            stats["Mean"] = f"{series.mean():.4f}"
            stats["Median (50%)"] = series.median()
            stats["StdDev"] = f"{series.std():.4f}"
        except Exception as e:
            self.logger.warning(f"Error calculating numeric stats: {e}")
            stats["Calculation Error"] = str(e)
        return stats

    def _calculate_datetime_stats_pandas(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate statistics for datetime columns using pandas."""
        stats = {}
        try:
            stats["Min"] = series.min()
            stats["Max"] = series.max()
            # Calculate time range
            time_range = series.max() - series.min()
            stats["Range"] = str(time_range)
        except Exception as e:
            self.logger.warning(f"Error calculating datetime stats: {e}")
            stats["Calculation Error"] = str(e)
        return stats

    def _calculate_boolean_stats_pandas(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate statistics for boolean columns using pandas."""
        stats = {}
        try:
            value_counts = series.value_counts()
            stats["True Count"] = f"{value_counts.get(True, 0):,}"
            stats["False Count"] = f"{value_counts.get(False, 0):,}"
            if len(value_counts) > 0:
                true_pct = (value_counts.get(True, 0) / len(series) * 100)
                stats["True Percentage"] = f"{true_pct:.2f}%"
        except Exception as e:
            self.logger.warning(f"Error calculating boolean stats: {e}")
            stats["Calculation Error"] = str(e)
        return stats

    def _calculate_string_stats_pandas(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate statistics for string columns using pandas."""
        stats = {}
        try:
            # Only min/max for strings (alphabetical order)
            stats["Min"] = str(series.min())
            stats["Max"] = str(series.max())

            # Most common values
            value_counts = series.value_counts().head(5)
            if len(value_counts) > 0:
                top_values = {}
                for value, count in value_counts.items():
                    top_values[str(value)] = f"{count:,}"
                stats["Top Values"] = top_values
        except Exception as e:
            self.logger.warning(f"Error calculating string stats: {e}")
            stats["Calculation Error"] = str(e)
        return stats

    def _create_stats_result(
            self,
            column_name: str,
            col_type: str,
            calculated_stats: Dict[str, Any],
            nullable: Optional[bool] = None,
            error: Optional[str] = None,
            message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Package the stats results consistently."""
        return {
            "column": column_name,
            "type": col_type,
            "nullable": nullable if nullable is not None else "Unknown",
            "calculated": calculated_stats or {},
            "error": error,
            "message": message,
        }

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd

from ..base import DataHandler, DataHandlerError


class JsonHandlerError(DataHandlerError):
    """Custom exception for JSON handling errors."""
    pass


class JsonHandler(DataHandler):
    """
    Handles JSON file interactions using DuckDB.

    Leverages DuckDB's `read_json_auto` for parsing standard JSON and JSON Lines (ndjson)
    and `SUMMARIZE` for efficient statistics calculation.

    Attributes:
        file_path (Path): Path to the JSON file.
    """
    DEFAULT_VIEW_NAME = "json_data_view"

    def __init__(self, file_path: Path):
        """
        Initializes the JsonHandler.

        Args:
            file_path: Path to the JSON file.

        Raises:
            JsonHandlerError: If the file doesn't exist, isn't a file, or if
                              initialization fails (e.g., DuckDB connection, view creation).
        """
        super().__init__(file_path)

        self.file_path = self._validate_file_path(file_path)
        self._db_conn: Optional[duckdb.DuckDBPyConnection] = None
        self._view_name: str = self.DEFAULT_VIEW_NAME
        self._schema: Optional[List[Dict[str, Any]]] = None
        self._row_count: Optional[int] = None

        try:
            self._connect_db()
            self._create_duckdb_view()
            self._load_metadata()
            self.logger.info(f"JsonHandler initialized successfully for: {self.file_path}")
        except Exception as e:
            self.logger.exception(f"Error during JsonHandler initialization for {self.file_path}")
            self.close()
            if isinstance(e, JsonHandlerError):
                raise
            raise JsonHandlerError(f"Failed to initialize JSON handler: {e}") from e

    def _validate_file_path(self, file_path: Path) -> Path:
        """Checks if the file path is valid."""
        resolved_path = file_path.resolve()
        if not resolved_path.is_file():
            raise JsonHandlerError(f"JSON file not found or is not a file: {resolved_path}")
        return resolved_path

    def _connect_db(self):
        """Establishes a connection to an in-memory DuckDB database."""
        try:
            self._db_conn = duckdb.connect(database=':memory:', read_only=False)
            self.logger.debug("DuckDB in-memory connection established.")
        except Exception as e:
            self.logger.exception("Failed to initialize DuckDB connection.")
            raise JsonHandlerError(f"DuckDB connection failed: {e}") from e

    def _create_duckdb_view(self):
        """Creates a DuckDB view pointing to the JSON file."""
        if not self._db_conn:
            raise JsonHandlerError("DuckDB connection not available for view creation.")

        file_path_str = str(self.file_path)
        safe_view_name = f'"{self._view_name}"'
        load_query = f"CREATE OR REPLACE VIEW {safe_view_name} AS SELECT * FROM read_json_auto('{file_path_str}');"

        try:
            self._db_conn.sql(load_query)
            self.logger.debug(f"DuckDB view '{self._view_name}' created for file '{file_path_str}'.")
        except duckdb.Error as db_err:
            self.logger.exception(f"DuckDB Error creating view '{self._view_name}' from '{file_path_str}': {db_err}")
            if "Could not open file" in str(db_err):
                raise JsonHandlerError(
                    f"DuckDB could not open file: {file_path_str}. Check permissions or path. Error: {db_err}") from db_err
            elif "JSON Error" in str(db_err) or "Parse Error" in str(db_err):
                raise JsonHandlerError(
                    f"DuckDB failed to parse JSON file: {file_path_str}. Check format. Error: {db_err}") from db_err
            else:
                raise JsonHandlerError(f"DuckDB failed create view for JSON file: {db_err}") from db_err
        except Exception as e:
            self.logger.exception(f"Unexpected error creating DuckDB view '{self._view_name}'.")
            raise JsonHandlerError(f"Failed to create DuckDB view: {e}") from e

    def _load_metadata(self):
        """Fetches schema and row count from the DuckDB view."""
        if not self._db_conn:
            raise JsonHandlerError("Cannot fetch metadata, DuckDB connection not available.")

        try:
            # Fetch Schema
            describe_query = f"DESCRIBE \"{self._view_name}\";"
            schema_result = self._db_conn.sql(describe_query).fetchall()
            self._schema = self._parse_schema(schema_result)
            self.logger.debug(f"Schema fetched for view '{self._view_name}': {len(self._schema)} columns.")

            # Fetch Row Count
            count_query = f"SELECT COUNT(*) FROM \"{self._view_name}\";"
            count_result = self._db_conn.sql(count_query).fetchone()
            self._row_count = count_result[0] if count_result else 0
            self.logger.debug(f"Row count fetched for view '{self._view_name}': {self._row_count}")

        except duckdb.Error as db_err:
            self.logger.exception(f"DuckDB Error fetching metadata for view '{self._view_name}': {db_err}")
            self._schema = None
            self._row_count = None
        except Exception as e:
            self.logger.exception(f"Unexpected error fetching metadata for view '{self._view_name}'")
            self._schema = None
            self._row_count = None

    def _parse_schema(self, describe_output: List[Tuple]) -> List[Dict[str, Any]]:
        """Parses the output of DuckDB's DESCRIBE query."""
        if not describe_output:
            self.logger.warning(f"DESCRIBE query for view '{self._view_name}' returned no schema info.")
            return []

        parsed_schema = []
        for row in describe_output:
            # Handle potential variations in DESCRIBE output columns
            if len(row) >= 3:
                name, type_str, null_str = row[0], row[1], row[2]
                is_nullable = None
                if isinstance(null_str, str):
                    is_nullable = null_str.upper() == 'YES'
                parsed_schema.append({"name": name, "type": type_str, "nullable": is_nullable})
            else:
                self.logger.warning(f"Unexpected format in DESCRIBE output row: {row}")
        return parsed_schema

    def get_schema_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Returns the schema of the JSON data.

        Returns:
            A list of dictionaries describing columns (name, type, nullable),
            or None if schema couldn't be fetched.
        """
        if self._schema is None:
            self.logger.warning("Schema is unavailable. It might not have been fetched successfully.")
        return self._schema

    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Provides a summary dictionary of the JSON file's metadata.

        Returns:
            A dictionary containing metadata like file path, format, row count, columns, size.
        """
        if not self._db_conn:
            return {"error": "DuckDB connection not initialized or closed."}

        row_count_str = "N/A (Error fetching)"
        if self._row_count is not None:
            row_count_str = f"{self._row_count:,}"

        columns_str = "N/A (Error fetching)"
        if self._schema is not None:
            columns_str = f"{len(self._schema):,}"

        summary = {
            "File Path": str(self.file_path),
            "Format": "JSON/JSONL",
            "DuckDB View": self._view_name,
            "Total Rows": row_count_str,
            "Columns": columns_str,
        }
        try:
            summary["Size"] = f"{self.file_path.stat().st_size:,} bytes"
        except Exception as e:
            self.logger.warning(f"Could not get file size for {self.file_path}: {e}")
            summary["Size"] = "N/A"

        return summary

    def get_data_preview(self, num_rows: int = 50) -> pd.DataFrame:
        """
        Fetches a preview of the data.

        Args:
            num_rows: The maximum number of rows to preview.

        Returns:
            A pandas DataFrame containing the first `num_rows` of data,
            an empty DataFrame if the file is empty, or a DataFrame with an
            error message if fetching fails.
        """
        if not self._db_conn:
            self.logger.warning("Data preview unavailable: DuckDB connection is closed or uninitialized.")
            return pd.DataFrame({"error": ["DuckDB connection not available."]})
        if self._schema is None:
            self.logger.warning("Data preview unavailable: Schema couldn't be determined.")
            return pd.DataFrame({"error": ["Schema not available, cannot fetch preview."]})
        if self._row_count == 0:
            self.logger.info("Data preview: Source JSON view is empty.")
            # Return empty DataFrame with correct columns if possible
            if self._schema:
                return pd.DataFrame(columns=[col['name'] for col in self._schema])
            else:
                return pd.DataFrame()  # Fallback

        try:
            limit = max(1, num_rows)
            preview_query = f"SELECT * FROM \"{self._view_name}\" LIMIT {limit};"
            df = self._db_conn.sql(preview_query).df()
            return df
        except duckdb.Error as db_err:
            self.logger.exception(f"DuckDB error getting data preview from '{self._view_name}': {db_err}")
            return pd.DataFrame({"error": [f"DuckDB error fetching preview: {db_err}"]})
        except Exception as e:
            self.logger.exception(f"Unexpected error getting data preview from '{self._view_name}'")
            return pd.DataFrame({"error": [f"Failed to fetch preview: {e}"]})

    def _get_column_info(self, column_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves schema information for a specific column."""
        if self._schema is None:
            return None
        return next((col for col in self._schema if col["name"] == column_name), None)

    def _is_complex_type(self, dtype_str: str) -> bool:
        """Checks if a DuckDB data type string represents a complex type."""
        if not isinstance(dtype_str, str):
            return False
        dtype_upper = dtype_str.upper()
        return any(t in dtype_upper for t in ['STRUCT', 'LIST', 'MAP', 'UNION'])

    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        """
        Calculates statistics for a given column using DuckDB's SUMMARIZE or basic counts.

        Args:
            column_name: The name of the column to analyze.

        Returns:
            A dictionary containing calculated statistics, type information, and
            any errors or messages.
        """
        if not self._db_conn:
            return self._create_stats_result(column_name, "Unknown", {}, error="DuckDB connection not available.")

        col_info = self._get_column_info(column_name)
        if not col_info:
            return self._create_stats_result(column_name, "Unknown", {},
                                             error=f"Column '{column_name}' not found in schema.")

        col_type = col_info["type"]
        col_nullable = col_info["nullable"]  # Already boolean or None
        is_complex = self._is_complex_type(col_type)
        safe_column_name = f'"{column_name}"'  # Quote column name for safety
        stats: Dict[str, Any] = {}
        error_msg: Optional[str] = None
        message: Optional[str] = None

        try:
            if self._row_count == 0:
                message = "Table is empty. No statistics calculated."
                return self._create_stats_result(column_name, col_type, stats, nullable=col_nullable, message=message)

            if is_complex:
                # Use basic counts for complex types as SUMMARIZE is less informative
                self.logger.debug(f"Calculating basic counts for complex type column: {column_name}")
                stats = self._get_basic_column_counts(safe_column_name)
                message = f"Only basic counts calculated for complex type '{col_type}'."
                # Attempt distinct count for complex types (can be slow/error-prone)
                try:
                    distinct_q = f"SELECT COUNT(DISTINCT {safe_column_name}) FROM \"{self._view_name}\" WHERE {safe_column_name} IS NOT NULL;"
                    distinct_res = self._db_conn.sql(distinct_q).fetchone()
                    if distinct_res and distinct_res[0] is not None:
                        stats["Distinct Count"] = f"{distinct_res[0]:,}"
                    else:
                        stats["Distinct Count"] = "N/A"  # Or 0 if appropriate
                except duckdb.Error as distinct_err:
                    self.logger.warning(
                        f"Could not calculate distinct count for complex column '{column_name}': {distinct_err}")
                    stats["Distinct Count"] = "Error"

            else:
                # Use SUMMARIZE for non-complex types
                self.logger.debug(f"Using SUMMARIZE for simple type column: {column_name}")
                summarize_query = f"SUMMARIZE SELECT {safe_column_name} FROM \"{self._view_name}\";"
                summarize_df = self._db_conn.sql(summarize_query).df()

                if summarize_df.empty:
                    message = "SUMMARIZE returned no results (column might be all NULLs or empty)."
                    # Get basic counts as fallback if summarize is empty
                    stats = self._get_basic_column_counts(safe_column_name)
                else:
                    # SUMMARIZE puts results in the first row
                    stats = self._format_summarize_stats(summarize_df.iloc[0])

        except duckdb.Error as db_err:
            self.logger.exception(f"DuckDB Error calculating statistics for column '{column_name}': {db_err}")
            error_msg = f"DuckDB calculation failed: {db_err}"
        except Exception as e:
            self.logger.exception(f"Unexpected error calculating statistics for column '{column_name}'")
            error_msg = f"Calculation failed unexpectedly: {e}"

        return self._create_stats_result(
            column_name, col_type, stats, nullable=col_nullable, error=error_msg, message=message
        )

    def _get_basic_column_counts(self, safe_column_name: str) -> Dict[str, Any]:
        """Helper to get total, null, and valid counts for a column."""
        stats = {}
        if not self._db_conn or self._row_count is None:
            return {"error": "Connection or row count unavailable for basic counts"}

        if self._row_count == 0:
            stats["Total Count"] = "0"
            stats["Valid Count"] = "0"
            stats["Null Count"] = "0"
            stats["Null Percentage"] = "N/A"
            return stats

        try:
            q_counts = f"""
            SELECT
                SUM(CASE WHEN {safe_column_name} IS NULL THEN 1 ELSE 0 END) AS null_count
            FROM "{self._view_name}";
            """
            counts_res = self._db_conn.sql(q_counts).fetchone()

            if counts_res:
                null_count = counts_res[0] if counts_res[0] is not None else 0
                total_count = self._row_count
                valid_count = total_count - null_count
                stats["Total Count"] = f"{total_count:,}"
                stats["Valid Count"] = f"{valid_count:,}"
                stats["Null Count"] = f"{null_count:,}"
                stats["Null Percentage"] = f"{(null_count / total_count * 100):.2f}%" if total_count > 0 else "N/A"
            else:
                stats["Total Count"] = f"{self._row_count:,}"
                stats["Valid Count"] = "Error"
                stats["Null Count"] = "Error"
                stats["Null Percentage"] = "Error"

        except duckdb.Error as db_err:
            self.logger.warning(f"Failed to get basic counts for {safe_column_name}: {db_err}")
            stats["Counts Error"] = str(db_err)
        return stats

    def _format_summarize_stats(self, summarize_row: pd.Series) -> Dict[str, Any]:
        """Formats the output of DuckDB's SUMMARIZE into a stats dictionary."""
        stats = {}
        if 'count' in summarize_row and pd.notna(summarize_row['count']):
            total_count = int(summarize_row['count'])
            stats["Total Count"] = f"{total_count:,}"
            null_count = 0
            if 'null_percentage' in summarize_row and pd.notna(summarize_row['null_percentage']):
                null_perc = summarize_row['null_percentage']
                null_count = int(round(total_count * (null_perc / 100.0)))
                stats["Null Percentage"] = f"{null_perc:.2f}%"
                stats["Null Count"] = f"{null_count:,}"
            else:
                stats["Null Percentage"] = "0.00%"  # Assume 0 if missing
                stats["Null Count"] = "0"

            stats["Valid Count"] = f"{total_count - null_count:,}"
        else:
            stats["Total Count"] = "N/A"
            stats["Valid Count"] = "N/A"
            stats["Null Count"] = "N/A"
            stats["Null Percentage"] = "N/A"

        # Distinct Count
        if 'distinct' in summarize_row and pd.notna(summarize_row['distinct']):
            stats["Distinct Count"] = f"{int(summarize_row['distinct']):,}"

        # Numeric Stats
        if 'min' in summarize_row and pd.notna(summarize_row['min']):
            stats["Min"] = summarize_row['min']
        if 'max' in summarize_row and pd.notna(summarize_row['max']):
            stats["Max"] = summarize_row['max']
        if 'mean' in summarize_row and pd.notna(summarize_row['mean']):
            try:
                stats["Mean"] = f"{float(summarize_row['mean']):.4f}"
            except (ValueError, TypeError):
                stats["Mean"] = str(summarize_row['mean'])
        if 'std' in summarize_row and pd.notna(summarize_row['std']):
            try:
                stats["StdDev"] = f"{float(summarize_row['std']):.4f}"
            except (ValueError, TypeError):
                stats["StdDev"] = str(summarize_row['std'])

        # Quantiles (example for median)
        if '50%' in summarize_row and pd.notna(summarize_row['50%']):
            stats["Median (50%)"] = summarize_row['50%']

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
        """Packages the stats results consistently."""
        return {
            "column": column_name,
            "type": col_type,
            "nullable": nullable if nullable is not None else "Unknown",
            "calculated": calculated_stats or {},
            "basic_metadata_stats": None,
            "metadata_stats_error": None,
            "error": error,
            "message": message,
        }

    def close(self):
        """Closes the DuckDB connection if it's open."""
        if self._db_conn:
            try:
                self._db_conn.close()
                self.logger.info(f"DuckDB connection closed for {self.file_path}.")
                self._db_conn = None
            except Exception as e:
                # Log error but don't raise during close typically
                self.logger.error(f"Error closing DuckDB connection for {self.file_path}: {e}")
                self._db_conn = None  # Assume closed even if error occurred

    def __enter__(self):
        """Enter context management."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context management, ensuring connection closure."""
        self.close()

    def __del__(self):
        """Ensures connection is closed when object is garbage collected (best effort)."""
        self.close()

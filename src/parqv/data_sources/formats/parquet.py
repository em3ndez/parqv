from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..base import DataHandler, DataHandlerError


class ParquetHandlerError(DataHandlerError):
    """Custom exception for Parquet Handler errors."""
    pass


class ParquetHandler(DataHandler):
    """
    Handles Parquet file interactions using PyArrow.

    Provides methods to access metadata, schema, data preview, and column statistics.
    Manages the Parquet file resource lifecycle.
    """

    def __init__(self, file_path: Path):
        """
        Initializes the ParquetHandler by validating the path and opening the Parquet file.

        Args:
            file_path: Path to the Parquet file.

        Raises:
            ParquetHandlerError: If the file is not found, not a file, or cannot be opened/read.
        """
        super().__init__(file_path)
        self.pq_file: Optional[pq.ParquetFile] = None
        self.schema: Optional[pa.Schema] = None
        self.metadata: Optional[pq.FileMetaData] = None

        try:
            # Validate file existence using the path stored by the base class
            if not self.file_path.is_file():
                raise FileNotFoundError(f"Parquet file not found or is not a file: {self.file_path}")

            # Open the Parquet file
            self.pq_file = pq.ParquetFile(self.file_path)
            self.schema = self.pq_file.schema_arrow
            self.metadata = self.pq_file.metadata
            self.logger.info(f"Successfully initialized ParquetHandler for: {self.file_path.name}")

        except FileNotFoundError as fnf_e:
            self.logger.error(f"File not found during ParquetHandler initialization: {fnf_e}")
            raise ParquetHandlerError(str(fnf_e)) from fnf_e
        except pa.lib.ArrowIOError as arrow_io_e:
            self.logger.error(f"Arrow IO Error initializing ParquetHandler for {self.file_path.name}: {arrow_io_e}")
            raise ParquetHandlerError(
                f"Failed to open Parquet file '{self.file_path.name}': {arrow_io_e}") from arrow_io_e
        except Exception as e:
            self.logger.exception(f"Unexpected error initializing ParquetHandler for {self.file_path.name}")
            self.close()
            raise ParquetHandlerError(f"Failed to initialize Parquet handler '{self.file_path.name}': {e}") from e

    # Resource Management
    def close(self) -> None:
        """Closes the Parquet file resource if it's open."""
        if self.pq_file is not None:
            try:
                # ParquetFile might not have a close method depending on source, check first
                if hasattr(self.pq_file, 'close'):
                    self.pq_file.close()
                self.logger.info(f"Closed Parquet file: {self.file_path.name}")
            except Exception as e:
                # Log error during close but don't raise, as we're cleaning up
                self.logger.warning(f"Exception while closing Parquet file {self.file_path.name}: {e}")
            finally:
                self.pq_file = None
                self.schema = None
                self.metadata = None

    def __enter__(self):
        """Enter the runtime context related to this object."""
        if not self.pq_file:
            raise ParquetHandlerError("Parquet file is not open or handler was closed.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context related to this object, ensuring cleanup."""
        self.close()

    def __del__(self):
        """Attempt to close the file when the object is garbage collected (best effort)."""
        self.close()

    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Provides a summary dictionary of the Parquet file's metadata.

        Returns:
            A dictionary containing key metadata attributes, or an error dictionary.
        """
        if not self.metadata or not self.schema:
            self.logger.warning(f"Metadata or schema not available for summary: {self.file_path.name}")
            return {"error": "Metadata or schema not available"}

        try:
            created_by = self._decode_metadata_bytes(self.metadata.created_by) or "N/A"
            file_size = self.file_path.stat().st_size
            summary = {
                "File Path": str(self.file_path.resolve()),
                "Format": "Parquet",
                "Size": self._format_size(file_size),
                "Total Rows": f"{self.metadata.num_rows:,}",
                "Row Groups": self.metadata.num_row_groups,
                "Columns": self.metadata.num_columns,
                "Format Version": self.metadata.format_version,
                "Creator": created_by,
                "Serialization Library": self._decode_metadata_bytes(
                    self.metadata.serialized_size > 0 and self.metadata.created_by) or "N/A",
            }
            kv_meta = self._decode_key_value_metadata(self.metadata.metadata)
            if kv_meta:
                summary["Key Value Metadata"] = kv_meta

            return summary
        except Exception as e:
            self.logger.exception(f"Error generating metadata summary for {self.file_path.name}")
            return {"error": f"Error getting metadata summary: {e}"}

    def get_schema_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Returns a simplified list representation of the Arrow schema.

        Returns:
            A list of dictionaries, each describing a column (name, type string, nullable bool),
            or None if the schema is unavailable.
        """
        if not self.schema:
            self.logger.warning(f"Schema is not available for get_schema_data: {self.file_path.name}")
            return None

        schema_list = []
        for field in self.schema:
            try:
                type_str = self._format_pyarrow_type(field.type)
                schema_list.append({
                    "name": field.name,
                    "type": type_str,
                    "nullable": field.nullable
                })
            except Exception as e:
                self.logger.error(f"Error processing field '{field.name}' for schema data: {e}", exc_info=True)
                schema_list.append({
                    "name": field.name,
                    "type": f"[Error: {e}]",
                    "nullable": None
                })
        return schema_list

    def get_data_preview(self, num_rows: int = 50) -> pd.DataFrame:
        """
        Fetches a preview of the data from the Parquet file using efficient batch iteration.

        Args:
            num_rows: The maximum number of rows to fetch.

        Returns:
            A pandas DataFrame with the preview data, potentially using ArrowDTypes.
            Returns an empty DataFrame if the file is empty or no data is read.
            Returns a DataFrame with an 'error' column on failure.
        """
        if not self.pq_file:
            self.logger.warning(f"ParquetFile handler not available for data preview: {self.file_path.name}")
            return pd.DataFrame({"error": ["Parquet handler not initialized or closed."]})

        if self.metadata and self.metadata.num_rows == 0:
            self.logger.info(f"Parquet file is empty based on metadata: {self.file_path.name}")
            if self.schema:
                return pd.DataFrame(columns=self.schema.names)
            else:
                return pd.DataFrame()

        try:
            # Determine rows to fetch, capped by file total
            num_rows_to_fetch = num_rows
            if self.metadata:
                num_rows_to_fetch = min(num_rows, self.metadata.num_rows)

            # Use iter_batches for memory efficiency
            batches = []
            rows_read = 0
            internal_batch_size = min(max(num_rows_to_fetch // 2, 1024), 65536)

            for batch in self.pq_file.iter_batches(batch_size=internal_batch_size):
                if rows_read >= num_rows_to_fetch:
                    break
                rows_needed_in_batch = num_rows_to_fetch - rows_read
                slice_len = min(len(batch), rows_needed_in_batch)
                batches.append(batch.slice(0, slice_len))
                rows_read += slice_len
                if rows_read >= num_rows_to_fetch:
                    break

            if not batches:
                # Check if file might have rows but reading yielded nothing
                if self.metadata and self.metadata.num_rows > 0:
                    self.logger.warning(
                        f"No batches read for preview, though metadata indicates {self.metadata.num_rows} rows: {self.file_path.name}")
                else:
                    self.logger.info(f"No data read for preview (file likely empty): {self.file_path.name}")
                # Return empty DF with columns if schema available
                if self.schema:
                    return pd.DataFrame(columns=self.schema.names)
                else:
                    return pd.DataFrame()

            # Combine batches and convert to Pandas
            preview_table = pa.Table.from_batches(batches)
            df = preview_table.to_pandas(
                split_blocks=True,
                self_destruct=True,
                types_mapper=pd.ArrowDtype
            )
            self.logger.info(f"Generated preview of {len(df)} rows for {self.file_path.name}")
            return df

        except Exception as e:
            self.logger.exception(f"Error generating data preview from Parquet file: {self.file_path.name}")
            return pd.DataFrame({"error": [f"Failed to fetch preview: {e}"]})

    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        """
        Calculates statistics for a specific column by reading its data.

        Args:
            column_name: The name of the column to analyze.

        Returns:
            A dictionary containing calculated statistics, metadata statistics,
            and potential error or message keys.
        """
        if not self.pq_file or not self.schema:
            self.logger.warning(f"Parquet file/schema unavailable for column stats: {self.file_path.name}")
            return self._create_stats_result(column_name, None, error="File or schema not available")

        try:
            field = self.schema.field(column_name)
        except KeyError:
            self.logger.warning(f"Column '{column_name}' not found in schema: {self.file_path.name}")
            return self._create_stats_result(column_name, None, error=f"Column '{column_name}' not found in schema")

        calculated_stats: Dict[str, Any] = {}
        error_msg: Optional[str] = None
        message: Optional[str] = None
        metadata_stats: Optional[Dict] = None
        metadata_stats_error: Optional[str] = None

        try:
            # Data Reading
            table = self.pq_file.read(columns=[column_name])
            column_data = table.column(0)
            self.logger.debug(
                f"Finished reading column '{column_name}'. Rows: {len(column_data)}, Nulls: {column_data.null_count}")

            # Basic Counts
            total_count = len(column_data)
            if total_count > 0:
                null_count = column_data.null_count
                valid_count = total_count - null_count
                calculated_stats["Total Count"] = f"{total_count:,}"
                calculated_stats["Valid Count"] = f"{valid_count:,}"
                calculated_stats["Null Count"] = f"{null_count:,}"
                calculated_stats["Null Percentage"] = f"{(null_count / total_count * 100):.2f}%"
            else:
                self.logger.info(f"Column '{column_name}' read resulted in 0 rows.")
                message = "Column is empty (0 rows)."
                valid_count = 0  # Ensure valid_count is 0 for later checks

            # Type-Specific Calculations
            if valid_count > 0:
                col_type = field.type
                self.logger.debug(f"Calculating stats for type: {self._format_pyarrow_type(col_type)}")
                try:
                    if pa.types.is_floating(col_type) or pa.types.is_integer(col_type):
                        calculated_stats.update(self._calculate_numeric_stats(column_data))
                    elif pa.types.is_temporal(col_type):
                        calculated_stats.update(self._calculate_temporal_stats(column_data))
                    elif pa.types.is_string(col_type) or pa.types.is_large_string(col_type) \
                            or pa.types.is_binary(col_type) or pa.types.is_large_binary(col_type):
                        calculated_stats.update(self._calculate_string_binary_stats(column_data))
                    elif pa.types.is_boolean(col_type):
                        calculated_stats.update(self._calculate_boolean_stats(column_data))
                    elif pa.types.is_dictionary(col_type):
                        calculated_stats.update(self._calculate_dictionary_stats(column_data, col_type))
                        message = calculated_stats.pop("message", message)
                    elif pa.types.is_struct(col_type) or pa.types.is_list(col_type) or pa.types.is_map(col_type) \
                            or pa.types.is_fixed_size_list(col_type) or pa.types.is_union(col_type):
                        calculated_stats.update(self._calculate_complex_type_stats(column_data, col_type))
                        message = f"Basic aggregate stats (min/max/mean) not applicable for complex type '{self._format_pyarrow_type(col_type)}'."
                    else:
                        self.logger.warning(f"Statistics calculation not fully implemented for type: {col_type}")
                        message = f"Statistics calculation not implemented for type '{self._format_pyarrow_type(col_type)}'."

                except Exception as calc_err:
                    self.logger.exception(f"Error during type-specific calculation for column '{column_name}': {calc_err}")
                    error_msg = f"Calculation error for type {field.type}: {calc_err}"
                    calculated_stats["Calculation Error"] = str(calc_err)  # Add specific error key

            elif total_count > 0:
                message = "Column contains only NULL values."

            # Metadata Statistics ---
            metadata_stats, metadata_stats_error = self._get_stats_from_metadata(column_name)

        except pa.lib.ArrowException as arrow_e:
            self.logger.exception(f"Arrow error during stats processing for column '{column_name}': {arrow_e}")
            error_msg = f"Arrow processing error: {arrow_e}"
        except Exception as e:
            self.logger.exception(f"Unexpected error during stats calculation for column '{column_name}'")
            error_msg = f"Calculation failed unexpectedly: {e}"

        return self._create_stats_result(
            column_name, field, calculated_stats, metadata_stats, metadata_stats_error, error_msg, message
        )

    def _decode_metadata_bytes(self, value: Optional[Union[bytes, str]]) -> Optional[str]:
        """Safely decodes bytes metadata values to UTF-8 strings, replacing errors."""
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='replace')
            except Exception as e:
                self.logger.warning(f"Could not decode metadata bytes: {e}. Value: {value!r}")
                return f"[Decode Error: {value!r}]"
        return str(value) if value is not None else None

    def _decode_key_value_metadata(self, kv_meta: Optional[Dict[Union[str, bytes], Union[str, bytes]]]) -> Optional[
        Dict[str, str]]:
        """Decodes keys and values of the key-value metadata dictionary."""
        if not kv_meta:
            return None
        decoded_kv = {}
        try:
            for k, v in kv_meta.items():
                key_str = self._decode_metadata_bytes(k) or "[Invalid Key]"
                val_str = self._decode_metadata_bytes(v) or "[Invalid Value]"
                decoded_kv[key_str] = val_str
            return decoded_kv
        except Exception as e:
            self.logger.warning(f"Could not decode key-value metadata: {e}")
            return {"error": f"Error decoding key-value metadata: {e}"}

    def _format_pyarrow_type(self, field_type: pa.DataType) -> str:
        """Formats a PyArrow DataType into a readable string, including details."""
        if pa.types.is_timestamp(field_type):
            tz_str = f", tz='{field_type.tz}'" if field_type.tz else ""
            return f"TIMESTAMP(unit='{field_type.unit}'{tz_str})"
        if pa.types.is_time32(field_type) or pa.types.is_time64(field_type):
            return f"TIME(unit='{field_type.unit}')"
        if pa.types.is_duration(field_type):
            return f"DURATION(unit='{field_type.unit}')"
        if pa.types.is_decimal128(field_type) or pa.types.is_decimal256(field_type):
            return f"DECIMAL({field_type.precision}, {field_type.scale})"
        if pa.types.is_fixed_size_binary(field_type):
            return f"FIXED_SIZE_BINARY({field_type.byte_width})"
        if pa.types.is_list(field_type) or pa.types.is_large_list(field_type) or pa.types.is_fixed_size_list(
                field_type):
            prefix = "LIST"
            if pa.types.is_large_list(field_type): prefix = "LARGE_LIST"
            if pa.types.is_fixed_size_list(field_type): prefix = f"FIXED_SIZE_LIST({field_type.list_size})"
            value_type_str = self._format_pyarrow_type(field_type.value_type)
            return f"{prefix}<item: {value_type_str}>"
        if pa.types.is_struct(field_type):
            num_fields_to_show = 3
            field_details = ", ".join(
                f"{f.name}: {self._format_pyarrow_type(f.type)}" for f in field_type[:num_fields_to_show])
            suffix = "..." if field_type.num_fields > num_fields_to_show else ""
            return f"STRUCT<{field_details}{suffix}>"
        if pa.types.is_map(field_type):
            keys_sorted = getattr(field_type, 'keys_sorted', False)
            sorted_str = ", keys_sorted" if keys_sorted else ""
            key_type_str = self._format_pyarrow_type(field_type.key_type)
            item_type_str = self._format_pyarrow_type(field_type.item_type)
            return f"MAP<key: {key_type_str}, value: {item_type_str}{sorted_str}>"
        if pa.types.is_dictionary(field_type):
            index_type_str = self._format_pyarrow_type(field_type.index_type)
            value_type_str = self._format_pyarrow_type(field_type.value_type)
            ordered = getattr(field_type, 'ordered', False)
            return f"DICTIONARY<indices: {index_type_str}, values: {value_type_str}{', ordered' if ordered else ''}>"
        if pa.types.is_union(field_type):
            type_codes = getattr(field_type, 'type_codes', [])
            mode = getattr(field_type, 'mode', 'sparse')
            field_details = ", ".join(
                f"{f.name}: {self._format_pyarrow_type(f.type)}" for f in field_type[:3])  # Show first few fields
            suffix = "..." if field_type.num_fields > 3 else ""
            return f"UNION<{field_details}{suffix}> (mode='{mode}', codes={type_codes[:5]}{'...' if len(type_codes) > 5 else ''})"

        return str(field_type).upper()

    def _safe_compute(self, func, data, *args, **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """Helper to safely execute a pyarrow.compute function and handle errors."""
        if data.null_count == len(data):
            return None, "Input data is all NULL"
        try:
            result_scalar = func(data, *args, **kwargs)
            return result_scalar.as_py() if result_scalar.is_valid else None, None
        except pa.lib.ArrowNotImplementedError as nie:
            return None, "Not Implemented"
        except Exception as e:
            return None, f"Compute Error: {e}"

    def _calculate_numeric_stats(self, column_data: pa.ChunkedArray) -> Dict[str, Any]:
        """Calculates min, max, mean, stddev for numeric columns using _safe_compute."""
        stats: Dict[str, Any] = {}
        min_val, err = self._safe_compute(pc.min, column_data)
        stats["Min"] = min_val if err is None else err
        max_val, err = self._safe_compute(pc.max, column_data)
        stats["Max"] = max_val if err is None else err
        mean_val, err = self._safe_compute(pc.mean, column_data)
        stats["Mean"] = f"{mean_val:.4f}" if mean_val is not None and err is None else (err or "N/A")
        stddev_val, err = self._safe_compute(pc.stddev, column_data, ddof=1)
        stats["StdDev"] = f"{stddev_val:.4f}" if stddev_val is not None and err is None else (err or "N/A")
        if stats["StdDev"] == "Not Implemented":
            variance_val, err_var = self._safe_compute(pc.variance, column_data, ddof=1)
            stats["Variance"] = f"{variance_val:.4f}" if variance_val is not None and err_var is None else (
                    err_var or "N/A")

        return stats

    def _calculate_temporal_stats(self, column_data: pa.ChunkedArray) -> Dict[str, Any]:
        """Calculates min and max for temporal columns using _safe_compute."""
        stats: Dict[str, Any] = {}
        min_val, err = self._safe_compute(pc.min, column_data)
        stats["Min"] = min_val if err is None else err  # .as_py() handles conversion
        max_val, err = self._safe_compute(pc.max, column_data)
        stats["Max"] = max_val if err is None else err
        return stats

    def _calculate_string_binary_stats(self, column_data: pa.ChunkedArray) -> Dict[str, Any]:
        """Calculates distinct count and optionally length stats for string/binary."""
        stats: Dict[str, Any] = {}
        distinct_val, err = self._safe_compute(pc.count_distinct, column_data)
        stats["Distinct Count"] = f"{distinct_val:,}" if distinct_val is not None and err is None else (err or "N/A")

        if pa.types.is_string(column_data.type) or pa.types.is_large_string(column_data.type):
            lengths, err_len = self._safe_compute(pc.binary_length, column_data)
            if err_len is None and lengths is not None:
                min_len, err_min = self._safe_compute(pc.min, lengths)
                stats["Min Length"] = min_len if err_min is None else err_min
                max_len, err_max = self._safe_compute(pc.max, lengths)
                stats["Max Length"] = max_len if err_max is None else err_max
                avg_len, err_avg = self._safe_compute(pc.mean, lengths)
                stats["Avg Length"] = f"{avg_len:.2f}" if avg_len is not None and err_avg is None else (
                        err_avg or "N/A")
            else:
                stats.update({"Min Length": "Error", "Max Length": "Error", "Avg Length": "Error"})
        return stats

    def _calculate_boolean_stats(self, column_data: pa.ChunkedArray) -> Dict[str, Any]:
        """Calculates value counts (True/False) for boolean columns."""
        stats: Dict[str, Any] = {}
        try:
            if column_data.null_count == len(column_data):
                stats["Value Counts"] = "All NULL"
                return stats

            # value_counts returns a StructArray [{values: bool, counts: int64}, ...]
            value_counts_struct = pc.value_counts(column_data)
            counts_dict = {}
            if len(value_counts_struct) > 0:
                for i in range(len(value_counts_struct)):
                    value = value_counts_struct.field("values")[i].as_py()
                    count = value_counts_struct.field("counts")[i].as_py()
                    counts_dict[value] = count  # Keys are True/False

            stats["Value Counts"] = {str(k): f"{v:,}" for k, v in counts_dict.items()}
            # Ensure both True and False are present, even if count is 0
            if 'True' not in stats["Value Counts"]: stats["Value Counts"]['True'] = "0"
            if 'False' not in stats["Value Counts"]: stats["Value Counts"]['False'] = "0"

        except Exception as vc_e:
            self.logger.warning(f"Boolean value count calculation error: {vc_e}", exc_info=True)
            stats["Value Counts"] = "Error calculating"
        return stats

    def _calculate_dictionary_stats(self, column_data: pa.ChunkedArray, col_type: pa.DictionaryType) -> Dict[str, Any]:
        """Calculates stats for dictionary type based on its value type."""
        stats: Dict[str, Any] = {"message": "Stats calculated on dictionary values."}  # Start with message
        try:
            unwrapped_data = column_data.dictionary_decode()
            value_type = col_type.value_type
            self.logger.debug(f"Calculating dictionary stats based on value type: {value_type}")

            # Delegate calculation based on the *value* type
            if pa.types.is_floating(value_type) or pa.types.is_integer(value_type):
                stats.update(self._calculate_numeric_stats(unwrapped_data))
            elif pa.types.is_temporal(value_type):
                stats.update(self._calculate_temporal_stats(unwrapped_data))
            elif pa.types.is_string(value_type) or pa.types.is_large_string(value_type) \
                    or pa.types.is_binary(value_type) or pa.types.is_large_binary(value_type):
                stats.update(self._calculate_string_binary_stats(unwrapped_data))
            # Add other dictionary value types if necessary (boolean, etc.)
            else:
                stats[
                    "message"] += f" (Stats for value type '{self._format_pyarrow_type(value_type)}' not fully implemented)."
                # Calculate distinct count on the original dictionary array (can be faster)
                distinct_val, err = self._safe_compute(pc.count_distinct, column_data)
                stats[
                    "Distinct Values (Approx)"] = f"{distinct_val:,}" if distinct_val is not None and err is None else (
                        err or "N/A")

        except pa.lib.ArrowException as arrow_decode_err:
            self.logger.warning(f"Arrow error decoding dictionary type for stats: {arrow_decode_err}")
            stats["Dictionary Error"] = f"Decode Error: {arrow_decode_err}"
        except Exception as dict_e:
            self.logger.warning(f"Could not process dictionary type for stats: {dict_e}")
            stats["Dictionary Error"] = f"Processing Error: {dict_e}"
        return stats

    def _calculate_complex_type_stats(self, column_data: pa.ChunkedArray, col_type: pa.DataType) -> Dict[str, Any]:
        """Calculates basic stats (like distinct count) for complex types."""
        stats: Dict[str, Any] = {}
        # Distinct count is often the most feasible stat for complex types
        distinct_val, err = self._safe_compute(pc.count_distinct, column_data)
        # Note: Distinct count on complex types can be approximate or may error depending on type
        stats["Distinct Count (Approx)"] = f"{distinct_val:,}" if distinct_val is not None and err is None else (
                err or "N/A")
        return stats

    def _get_stats_from_metadata(self, column_name: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """Retrieves statistics stored within the Parquet file metadata per row group."""
        metadata_stats: Dict[str, Any] = {}
        error_str: Optional[str] = None

        if not self.metadata or not self.schema:
            return {}, "Metadata or Schema not available"

        try:
            col_index = self.schema.get_field_index(column_name)

            for i in range(self.metadata.num_row_groups):
                group_key = f"RG {i}"
                try:
                    rg_meta = self.metadata.row_group(i)
                    metadata_stats[group_key] = self._extract_stats_for_single_group(rg_meta, col_index)
                except IndexError:
                    self.logger.warning(f"Column index {col_index} out of bounds for row group {i}.")
                    metadata_stats[group_key] = "Index Error"
                except Exception as e:
                    self.logger.warning(f"Error processing metadata stats for RG {i}, column '{column_name}': {e}")
                    metadata_stats[group_key] = f"Read Error: {e}"

        except KeyError:
            self.logger.warning(f"Column '{column_name}' not found in schema for metadata stats.")
            error_str = f"Column '{column_name}' not found in schema"
        except Exception as e:
            self.logger.exception(f"Failed to get metadata statistics structure for column '{column_name}'.")
            error_str = f"Error accessing metadata structure: {e}"

        return metadata_stats, error_str

    def _extract_stats_for_single_group(self, rg_meta: pq.RowGroupMetaData, col_index: int) -> Union[
        str, Dict[str, Any]]:
        """Extracts stats from a column chunk's metadata within a row group."""
        try:
            col_chunk_meta = rg_meta.column(col_index)
            stats = col_chunk_meta.statistics
            if not stats: return "No stats in metadata"

            def _format_stat(value, is_present, is_numeric=True):
                if not is_present: return "N/A"
                try:
                    # Attempt to format nicely, fallback to repr for safety
                    return f"{value:,}" if is_numeric else str(value)
                except Exception:
                    return repr(value)

            return {
                "min": _format_stat(stats.min, stats.has_min_max, is_numeric=False),
                "max": _format_stat(stats.max, stats.has_min_max, is_numeric=False),
                "nulls": _format_stat(stats.null_count, stats.has_null_count),
                "distinct": _format_stat(stats.distinct_count, stats.has_distinct_count),
                "size_comp": _format_stat(col_chunk_meta.total_compressed_size,
                                          col_chunk_meta.total_compressed_size is not None),
                "size_uncomp": _format_stat(col_chunk_meta.total_uncompressed_size,
                                            col_chunk_meta.total_uncompressed_size is not None),
            }
        except IndexError:
            self.logger.warning(f"Column index {col_index} out of bounds for row group {rg_meta.num_columns} columns.")
            return "Index Error"
        except Exception as e:
            self.logger.error(f"Error reading column chunk metadata stats for index {col_index}: {e}", exc_info=True)
            return f"Metadata Read Error: {e}"

    def _create_stats_result(
            self,
            column_name: str,
            field: Optional[pa.Field],
            calculated_stats: Optional[Dict] = None,
            metadata_stats: Optional[Dict] = None,
            metadata_stats_error: Optional[str] = None,
            calculation_error: Optional[str] = None,
            message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consistently packages the results of column statistics calculation."""
        calculated_stats_dict = calculated_stats if calculated_stats is not None else {}

        col_type_str = "Unknown"
        col_nullable = None
        if field:
            try:
                col_type_str = self._format_pyarrow_type(field.type)
                col_nullable = field.nullable
            except Exception as e:
                self.logger.error(f"Error formatting type for column {column_name}: {e}")
                col_type_str = f"[Error formatting: {field.type}]"
                col_nullable = None

        return {
            "column": column_name,
            "type": col_type_str,
            "nullable": col_nullable,
            "calculated": calculated_stats_dict,
            "basic_metadata_stats": metadata_stats,
            "metadata_stats_error": metadata_stats_error,
            "error": calculation_error,
            "message": message
        }

    def _format_size(self, num_bytes: int) -> str:
        """Formats bytes into a human-readable string (KB, MB, GB)."""
        if num_bytes < 1024:
            return f"{num_bytes} Bytes"
        elif num_bytes < 1024 ** 2:
            return f"{num_bytes / 1024:.2f} KB"
        elif num_bytes < 1024 ** 3:
            return f"{num_bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{num_bytes / 1024 ** 3:.2f} GB"

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

log = logging.getLogger(__name__)


class ParquetHandlerError(Exception):
    pass


class ParquetHandler:

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.pq_file: Optional[pq.ParquetFile] = None
        self.schema: Optional[pa.Schema] = None
        self.metadata: Optional[pq.FileMetaData] = None
        try:
            self.pq_file = pq.ParquetFile(file_path)
            self.schema = self.pq_file.schema_arrow
            self.metadata = self.pq_file.metadata
        except Exception as e:
            log.exception("Error initializing ParquetHandler")
            raise ParquetHandlerError(f"Failed to open or read Parquet file: {e}") from e

    def get_metadata_summary(self) -> Dict[str, Any]:
        if not self.metadata or not self.schema:
            return {"error": "Metadata or schema not available"}

        created_by = self._decode_metadata_bytes(self.metadata.created_by) or "N/A"
        summary = {
            "File Path": str(self.file_path.resolve()),
            "Size": f"{self.file_path.stat().st_size:,} bytes",
            "Total Rows": f"{self.metadata.num_rows:,}",
            "Row Groups": self.metadata.num_row_groups,
            "Columns": self.metadata.num_columns,
            "Format Version": self.metadata.format_version,
            "Creator": created_by,
            "Schema Fields": len(self.schema.names),
        }
        kv_meta = self._decode_key_value_metadata(self.metadata.metadata)
        if kv_meta:
            summary["Key Value Metadata"] = kv_meta
        return summary

    def get_schema_tree_data(self) -> Optional[Dict[str, Any]]:
        if not self.schema or not self.schema.names:
            log.warning("Schema is not available or has no fields.")
            return None

        root_data: Dict[str, Any] = {}
        for field in self.schema:
            try:
                label, children = self._build_schema_tree_nodes(field)
                root_data[label] = children
            except Exception as field_e:
                log.error(f"Error processing schema field '{field.name}': {field_e}", exc_info=True)
                root_data[f"[red]Error processing: {field.name}[/red]"] = None

        if not root_data:
            log.warning("Processed schema data resulted in an empty dictionary.")
            return None

        return root_data

    def get_data_preview(self, num_rows: int = 50) -> Optional[pd.DataFrame]:
        if not self.pq_file:
            log.warning("ParquetFile handler not available for data preview.")
            return None

        tables_to_concat = []
        rows_accumulated = 0
        for i in range(self.pq_file.num_row_groups):
            rg_meta = self.pq_file.metadata.row_group(i)
            rows_to_read_from_group = min(rg_meta.num_rows, num_rows - rows_accumulated)

            if rows_to_read_from_group <= 0:
                log.debug(f"Limit {num_rows} reached after {i} groups.")
                break

            rg_table = self.pq_file.read_row_group(i)
            tables_to_concat.append(rg_table)
            rows_accumulated += rg_meta.num_rows

        if not tables_to_concat:
            log.warning("No row groups read or file is empty.")
            return pd.DataFrame()

        combined_table = pa.concat_tables(tables_to_concat)
        preview_table = combined_table.slice(0, num_rows)

        df = preview_table.to_pandas(
            split_blocks=True, self_destruct=True, date_as_object=False, types_mapper=pd.ArrowDtype
        )
        return df

    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        if not self.pq_file or not self.schema or not column_name:
            log.warning("Prerequisites not met for get_column_stats.")
            return {"error": "File, schema, or column name not available"}

        error_msg: Optional[str] = None
        field: Optional[pa.Field] = None
        calculated_stats: Dict[str, Any] = {}

        field = self.schema.field(column_name)
        col_type = field.type

        table = self.pq_file.read(columns=[column_name])
        if table.num_rows == 0:
            log.warning(f"Column '{column_name}' is empty.")
            return self._create_stats_result(column_name, field, msg="Column is empty (0 rows).")

        column_data = table.column(column_name)
        # Basic counts
        total_count = len(column_data)
        null_count = column_data.null_count
        valid_count = total_count - null_count
        calculated_stats["Total Count"] = f"{total_count:,}"
        calculated_stats["Valid Count"] = f"{valid_count:,}"
        calculated_stats["Null Count"] = f"{null_count:,}"
        calculated_stats[
            "Null Percentage"] = f"{(null_count / total_count * 100):.2f}%" if total_count > 0 else "N/A"

        # Type-specific calculations
        if valid_count > 0:
            valid_data = column_data.drop_null()
            if pa.types.is_integer(col_type) or pa.types.is_floating(col_type):
                calculated_stats.update(self._calculate_numeric_stats(valid_data))
            elif pa.types.is_temporal(col_type):
                calculated_stats.update(self._calculate_temporal_stats(valid_data))
            elif pa.types.is_string(col_type) or pa.types.is_large_string(col_type):
                calculated_stats.update(self._calculate_string_stats(valid_data))
            elif pa.types.is_boolean(col_type):
                calculated_stats.update(self._calculate_boolean_stats(valid_data))
        else:
            log.debug("No valid data points for calculation.")

        metadata_stats, metadata_stats_error = self._get_stats_from_metadata(column_name)
        return self._create_stats_result(
            column_name, field, calculated_stats, metadata_stats, metadata_stats_error, error_msg
        )

    def get_row_group_info(self) -> List[Dict[str, Any]]:
        if not self.metadata:
            log.warning("Metadata not available for row group info.")
            return []
        groups = []
        num_groups = self.metadata.num_row_groups

        for i in range(num_groups):
            try:
                rg_meta = self.metadata.row_group(i)
                num_rows = getattr(rg_meta, 'num_rows', 'N/A')
                size = getattr(rg_meta, 'total_byte_size', 'N/A')
                comp_size_val = getattr(rg_meta, 'total_compressed_size', -1)
                comp_size = f"{comp_size_val:,}" if isinstance(comp_size_val, int) and comp_size_val > 0 else "N/A"

                groups.append({
                    "Group": i,
                    "Rows": f"{num_rows:,}" if isinstance(num_rows, int) else num_rows,
                    "Size (bytes)": f"{size:,}" if isinstance(size, int) else size,
                    "Size (comp.)": comp_size,
                })
            except Exception as e:
                log.error(f"Error reading metadata for row group {i}", exc_info=True)
                groups.append({"Group": i, "Rows": "Error", "Size (bytes)": "Error", "Size (comp.)": "Error"})
        return groups

    def _decode_metadata_bytes(self, value: Optional[bytes]) -> Optional[str]:
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='replace')
            except Exception as e:
                log.warning(f"Could not decode metadata bytes: {e}")
                return repr(value)
        return value

    def _decode_key_value_metadata(self, kv_meta: Optional[Dict[bytes, bytes]]) -> Optional[Dict[str, str]]:
        if not kv_meta:
            return None
        decoded_kv = {}
        try:
            for k, v in kv_meta.items():
                key_str = self._decode_metadata_bytes(k) or repr(k)
                val_str = self._decode_metadata_bytes(v) or repr(v)
                decoded_kv[key_str] = val_str
            return decoded_kv
        except Exception as e:
            log.warning(f"Could not decode key-value metadata: {e}")
            return {"error": f"Error decoding: {e}"}

    def _format_pyarrow_type(self, field_type: pa.DataType) -> str:
        if pa.types.is_timestamp(field_type):
            return f"TIMESTAMP(unit={field_type.unit}, tz={field_type.tz})"

        if pa.types.is_decimal128(field_type) or pa.types.is_decimal256(field_type):
            return f"DECIMAL({field_type.precision}, {field_type.scale})"

        if pa.types.is_list(field_type) or pa.types.is_large_list(field_type):
            return f"LIST<{self._format_pyarrow_type(field_type.value_type)}>"

        if pa.types.is_struct(field_type):
            return f"STRUCT<{field_type.num_fields} fields>"

        if pa.types.is_map(field_type):
            return f"MAP<{self._format_pyarrow_type(field_type.key_type)}, {self._format_pyarrow_type(field_type.item_type)}>"

        return str(field_type).upper()

    def _build_schema_tree_nodes(self, field: pa.Field) -> Tuple[str, Optional[Dict]]:
        node_label = f"[bold]{field.name}[/] ({self._format_pyarrow_type(field.type)})"
        if not field.nullable:
            node_label += " [red]REQUIRED[/]"

        children_data: Dict[str, Any] = {}
        field_type = field.type

        if pa.types.is_struct(field_type):
            for i in range(field_type.num_fields):
                child_label, grandchild_data = self._build_schema_tree_nodes(field_type.field(i))
                children_data[child_label] = grandchild_data

        elif pa.types.is_list(field_type) or pa.types.is_large_list(field_type):
            element_field = pa.field("item", field_type.value_type, nullable=True)
            child_label, grandchild_data = self._build_schema_tree_nodes(element_field)
            children_data[child_label] = grandchild_data

        elif pa.types.is_map(field_type):
            key_field = pa.field("key", field_type.key_type, nullable=False)
            value_field = pa.field("value", field_type.item_type, nullable=True)
            key_label, _ = self._build_schema_tree_nodes(key_field)
            value_label, value_grandchild = self._build_schema_tree_nodes(value_field)
            children_data[key_label] = None
            children_data[value_label] = value_grandchild

        return node_label, children_data if children_data else None

    def _calculate_numeric_stats(self, valid_data: pa.ChunkedArray) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        try:
            stats["Min"] = pc.min(valid_data).as_py()
        except Exception as e:
            log.warning(f"Min calc error: {e}");
            stats["Min"] = "Error"
        try:
            stats["Max"] = pc.max(valid_data).as_py()
        except Exception as e:
            log.warning(f"Max calc error: {e}");
            stats["Max"] = "Error"
        try:
            stats["Mean"] = f"{pc.mean(valid_data).as_py():.4f}"
        except Exception as e:
            log.warning(f"Mean calc error: {e}");
            stats["Mean"] = "Error"
        try:
            stats["StdDev"] = f"{pc.stddev(valid_data, ddof=1).as_py():.4f}"
        except Exception as e:
            log.warning(f"StdDev calc error: {e}");
            stats["StdDev"] = "Error"
        return stats

    def _calculate_temporal_stats(self, valid_data: pa.ChunkedArray) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        try:
            stats["Min"] = pc.min(valid_data).as_py()
        except Exception as e:
            log.warning(f"Min calc error (temporal): {e}");
            stats["Min"] = "Error"
        try:
            stats["Max"] = pc.max(valid_data).as_py()
        except Exception as e:
            log.warning(f"Max calc error (temporal): {e}");
            stats["Max"] = "Error"
        return stats

    def _calculate_string_stats(self, valid_data: pa.ChunkedArray) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        try:
            stats["Distinct Count"] = f"{pc.count_distinct(valid_data).as_py():,}"
        except Exception as e:
            log.warning(f"Distinct count error: {e}");
            stats["Distinct Count"] = "Error"
        # TopN removed as requested
        return stats

    def _calculate_boolean_stats(self, valid_data: pa.ChunkedArray) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        try:
            value_counts_table = valid_data.value_counts()
            if isinstance(value_counts_table, pa.Table):
                counts_df = value_counts_table.to_pandas()
            elif isinstance(value_counts_table, pa.StructArray):
                try:
                    counts_df = value_counts_table.flatten().to_pandas()
                except NotImplementedError:
                    counts_df = pd.DataFrame(value_counts_table.to_pylist())  # Fallback

            else:
                counts_df = pd.DataFrame(value_counts_table.to_pylist())

            if 'values' in counts_df.columns and 'counts' in counts_df.columns:
                stats["Value Counts"] = counts_df.set_index('values')['counts'].to_dict()
            elif len(counts_df.columns) == 2:  # Assume first is value, second is count
                stats["Value Counts"] = counts_df.set_index(counts_df.columns[0])[counts_df.columns[1]].to_dict()
            else:
                log.warning("Could not parse boolean value counts structure.")
                stats["Value Counts"] = "Could not parse structure"

        except Exception as vc_e:
            log.warning(f"Boolean value count error: {vc_e}");
            stats["Value Counts"] = "Error calculating"
        return stats

    def _extract_stats_for_single_group(
            self, rg_meta: pq.RowGroupMetaData, col_index: int
    ) -> Union[str, Dict[str, Any]]:

        if col_index >= rg_meta.num_columns:
            log.warning(
                f"Column index {col_index} out of bounds for row group "
                f"with {rg_meta.num_columns} columns."
            )
            return "Index Error"

        col_chunk_meta = rg_meta.column(col_index)
        stats = col_chunk_meta.statistics

        if not stats:
            return "No stats"

        has_min_max = getattr(stats, 'has_min_max', False)
        has_distinct = getattr(stats, 'has_distinct_count', False)

        return {
            "min": getattr(stats, 'min', 'N/A') if has_min_max else "N/A",
            "max": getattr(stats, 'max', 'N/A') if has_min_max else "N/A",
            "nulls": getattr(stats, 'null_count', 'N/A'),
            "distinct": getattr(stats, 'distinct_count', 'N/A') if has_distinct else "N/A",
        }

    def _get_stats_from_metadata(self, column_name: str) -> Tuple[Dict[str, Any], Optional[str]]:
        metadata_stats: Dict[str, Any] = {}
        if not self.metadata or not self.schema:
            log.warning("Metadata or Schema not available for _get_stats_from_metadata.")
            return {}, "Metadata or Schema not available"
        col_index = self.schema.get_field_index(column_name)

        for i in range(self.metadata.num_row_groups):
            group_key = f"RG {i}"
            try:
                rg_meta = self.metadata.row_group(i)
                metadata_stats[group_key] = self._extract_stats_for_single_group(
                    rg_meta, col_index
                )
            except Exception as e:
                log.warning(
                    f"Error processing metadata for row group {i}, column '{column_name}': {e}"
                )
                metadata_stats[group_key] = f"Read Error: {e}"

        return metadata_stats, None

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
        return {
            "column": column_name,
            "type": self._format_pyarrow_type(field.type) if field else "Unknown",
            "nullable": field.nullable if field else "Unknown",
            "calculated": calculated_stats if calculated_stats else None,
            "basic_metadata_stats": metadata_stats if metadata_stats else None,
            "metadata_stats_error": metadata_stats_error,
            "error": calculation_error,
            "message": message
        }

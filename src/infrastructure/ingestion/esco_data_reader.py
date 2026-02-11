"""
ESCO data reader for CSV processing.

Provides batch CSV reading with progress tracking and column standardization
for ESCO taxonomy data files.
"""

import os
import logging
from typing import Callable, Optional

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ESCODataReader:
    """Reads and pre-processes ESCO CSV data files in batches."""

    def __init__(self, data_dir: str, batch_size: int = 100):
        """
        Initialize the data reader.

        Args:
            data_dir: Directory containing ESCO CSV files
            batch_size: Number of rows per processing batch
        """
        self.data_dir = data_dir
        self.batch_size = batch_size

    def process_csv_in_batches(
        self,
        filename: str,
        process_func: Callable[[pd.DataFrame], None],
        heartbeat_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """
        Process a CSV file in batches with optional heartbeat updates.

        Args:
            filename: CSV file name (relative to data_dir)
            process_func: Function to process each batch DataFrame
            heartbeat_callback: Optional callback(rows_processed, total_rows)
        """
        file_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path} - skipping.")
            return

        df = pd.read_csv(file_path)
        total_rows = len(df)
        rows_processed = 0

        with tqdm(
            total=total_rows,
            desc=f"Processing {filename}",
            unit="rows",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ) as pbar:
            for start_idx in range(0, total_rows, self.batch_size):
                end_idx = min(start_idx + self.batch_size, total_rows)
                batch = df.iloc[start_idx:end_idx]
                process_func(batch)
                rows_processed += len(batch)
                pbar.update(len(batch))

                if heartbeat_callback and rows_processed % 1000 == 0:
                    heartbeat_callback(rows_processed, total_rows)

    def read_csv(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Read a full CSV file and return as DataFrame.

        Args:
            filename: CSV file name (relative to data_dir)

        Returns:
            DataFrame or None if file doesn't exist
        """
        file_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path} - skipping.")
            return None
        return pd.read_csv(file_path)

    @staticmethod
    def standardize_hierarchy_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename alternative hierarchy column names to broaderUri / narrowerUri.

        Handles variants found in ESCO CSVs such as:
        - broaderConceptUri / narrowerConceptUri
        - parentUri / childUri
        - broaderSkillUri / skillUri
        - Level X URI format
        """
        rename_map = {}

        if "Level 0 URI" in df.columns:
            def get_broader_narrower(row):
                levels = [f"Level {i} URI" for i in range(4)]
                non_empty = [
                    lv for lv in levels
                    if lv in df.columns and pd.notna(row[lv]) and row[lv] != ""
                ]
                if len(non_empty) >= 2:
                    return pd.Series([row[non_empty[-2]], row[non_empty[-1]]])
                return pd.Series([None, None])

            df[["broaderUri", "narrowerUri"]] = df.apply(
                get_broader_narrower, axis=1
            )
            df = df.dropna(subset=["broaderUri", "narrowerUri"])
            df = df[df["broaderUri"] != df["narrowerUri"]]
            return df

        if "broaderUri" not in df.columns:
            for alt in ("broaderConceptUri", "parentUri", "broaderSkillUri"):
                if alt in df.columns:
                    rename_map[alt] = "broaderUri"
                    break

        if "narrowerUri" not in df.columns:
            for alt in (
                "narrowerConceptUri", "childUri", "conceptUri",
                "targetUri", "skillUri"
            ):
                if alt in df.columns:
                    rename_map[alt] = "narrowerUri"
                    break

        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    @staticmethod
    def standardize_collection_relation_columns(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Rename alternative column names for skill-collection relation CSVs
        so downstream code can assume conceptSchemeUri and skillUri.
        """
        rename_map = {}
        if "conceptSchemeUri" not in df.columns:
            for alt in ("collectionUri", "conceptScheme", "schemeUri"):
                if alt in df.columns:
                    rename_map[alt] = "conceptSchemeUri"
                    break
        if "skillUri" not in df.columns:
            for alt in ("conceptUri", "targetUri", "skillID"):
                if alt in df.columns:
                    rename_map[alt] = "skillUri"
                    break
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

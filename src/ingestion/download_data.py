"""
Data Ingestion & Dataset Resolver
Locates or acquires the Brazilian E-Commerce Public Dataset by Olist.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from config.settings import RAW_DATA_DIR, RAW_FILES, CANDIDATE_DATA_DIRS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def check_dataset_status(data_dir: Path = RAW_DATA_DIR) -> Tuple[bool, Dict[str, bool]]:
    """Check which expected dataset CSV files exist in the specified directory."""
    status = {}
    for table_name, filename in RAW_FILES.items():
        file_path = data_dir / filename
        status[table_name] = file_path.exists() and file_path.stat().st_size > 0

    all_present = all(status.values())
    return all_present, status


def locate_existing_dataset() -> Path:
    """Scan candidate directories for existing Olist CSVs."""
    for candidate in CANDIDATE_DATA_DIRS:
        if candidate.exists():
            all_present, _ = check_dataset_status(candidate)
            if all_present:
                logger.info(f"Found complete dataset at: {candidate}")
                return candidate
    return RAW_DATA_DIR


def ensure_dataset(target_dir: Path = RAW_DATA_DIR) -> bool:
    """
    Ensure all 9 dataset files are present.
    If files are located in another candidate directory, copy or link them.
    If missing, output clear instructions for obtaining them.
    """
    all_present, status = check_dataset_status(target_dir)
    if all_present:
        logger.info(f"All 9 Olist dataset files verified at {target_dir}")
        return True

    # Check other candidates
    found_dir = locate_existing_dataset()
    if found_dir != target_dir and found_dir.exists():
        found_complete, _ = check_dataset_status(found_dir)
        if found_complete:
            logger.info(f"Copying missing dataset files from {found_dir} to {target_dir}...")
            target_dir.mkdir(parents=True, exist_ok=True)
            for _, filename in RAW_FILES.items():
                src_file = found_dir / filename
                dst_file = target_dir / filename
                if not dst_file.exists() and src_file.exists():
                    shutil.copy2(src_file, dst_file)
            return True

    missing_files = [RAW_FILES[k] for k, present in status.items() if not present]
    logger.warning(f"Missing {len(missing_files)} dataset files in {target_dir}: {missing_files}")
    print("\n" + "=" * 70)
    print("DATASET ACQUISITION INSTRUCTIONS:")
    print("1. Download the Brazilian E-Commerce Public Dataset by Olist:")
    print("   https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
    print(f"2. Extract all 9 CSV files into:")
    print(f"   {target_dir.resolve()}")
    print("3. Alternatively, if using the Kaggle API:")
    print("   kaggle datasets download -d olistbr/brazilian-ecommerce --unzip -p data/raw")
    print("=" * 70 + "\n")
    return False


if __name__ == "__main__":
    ensure_dataset()

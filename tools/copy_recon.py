# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:04:12 2024

@author: rvimieiro
"""

import os
import shutil
from pathlib import Path


def copy_proc_rot_folders(src_folder, dst_folder):
    """
    Recursively copies all subfolders starting with 'PROC_ROT' from the source directory
    to the destination directory, maintaining the directory structure.

    Parameters:
    - src_folder: Path to the source directory where the folders are located.
    - dst_folder: Path to the destination directory where folders are to be copied.
    """
    src_path = Path(src_folder)
    dst_path = Path(dst_folder)

    # Ensure the source directory exists
    if not src_path.exists():
        print(f"The source directory {src_folder} does not exist.")
        return

    # Ensure the destination directory exists
    if not dst_path.exists():
        dst_path.mkdir(parents=True, exist_ok=True)
        print(f"Created the destination directory {dst_folder}")

    # Walk through all directories and subdirectories
    for dirpath in src_path.rglob('*'):
        if dirpath.is_dir() and dirpath.name.startswith("recon_roi"):
            relative_path = dirpath.relative_to(src_path)
            full_dst_path = dst_path / relative_path

            # Copy the directory tree to the new location
            shutil.copytree(dirpath, full_dst_path)
            print(f"Copied {dirpath} to {full_dst_path}")


# Example usage
source_directory = '/home/rodrigo/Documents/rodrigo/pessoal/lavi/dataset/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/calcifications'#'/media/rodrigo/SSD480/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/' #
destination_directory = '/home/rodrigo/Documents/rodrigo/pessoal/lavi/dataset/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/JND' #'/media/rodrigo/SSD480/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/JND/' #
copy_proc_rot_folders(source_directory, destination_directory)


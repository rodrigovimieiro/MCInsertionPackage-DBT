import os
import pydicom
import numpy as np
import pathlib
import random
import re
import matplotlib.pyplot as plt

def extract_roi_number(path):

    match = re.search(r"roi_(\d+)", path)
    if match:
        return int(match.group(1))
    return None

def augment_dicom_images(contrast_folders, n_rois2reach):


    n3generate =  n_rois2reach - len(contrast_folders)

    idg = 0

    # Iterate through each contrast folder found
    for folder in contrast_folders:

        if idg == n3generate:
            break

        idg += 1

        local_folders = [str(item) for item in pathlib.Path(folder).parent.rglob("*recon_roi_*_contrast_*_ROI_cluster0*") if pathlib.Path(item).is_dir()]

        # Extract all ROI numbers
        roi_numbers = [extract_roi_number(local_folder) for local_folder in local_folders]

        # Find the largest ROI number
        largest_roi = np.max(roi_numbers)

        target_roi = largest_roi + 1

        output_dir = re.sub(r"roi_(\d+)", f"roi_{target_roi:02d}", local_folders[0])

        # Create the output directory if it does not exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.dcm'):
                    # Read the DICOM file
                    dicom_path = os.path.join(root, file)
                    dicom = pydicom.dcmread(dicom_path)

                    # Get the image array
                    image_array = dicom.pixel_array

                    # Perform vertical flip
                    v_flip = np.flipud(image_array)

                    dicom.PixelData = v_flip.tobytes()

                    output_path = os.path.join(output_dir, file)

                    dicom.save_as(output_path)

    print("Generated {} ROIs.".format(idg))

if __name__ == "__main__":

    random.seed(4548)

    path2read_real = '/home/rodrigo/Documents/rodrigo/pessoal/lavi/dataset/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/JND'

    n_rois2reach = 310

    # Find folders matching the pattern
    contrast_folders = [str(item) for item in pathlib.Path(path2read_real).rglob("*recon_roi_*_contrast_*_ROI_cluster0*") if pathlib.Path(item).is_dir()]

    random.shuffle(contrast_folders)

    # Perform data augmentation
    augment_dicom_images(contrast_folders, n_rois2reach)

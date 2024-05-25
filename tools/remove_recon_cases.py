import pathlib
import random
import shutil

if __name__ == "__main__":

    random.seed(4548)

    path2read_real = '/home/rodrigo/Documents/rodrigo/pessoal/lavi/dataset/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/JND'

    n_rois2reach = 310

    cases2remove = [
    '30001808/1815/recon_roi_01_contrast_*_ROI_cluster1',
    '30001808/1837/recon_roi_00_contrast_*_ROI_cluster1',
    '29777557/841/recon_roi_07_contrast_*_ROI_cluster1',
    '30001135/1163/recon_roi_03_contrast_*_ROI_cluster1']

    for case2remove in cases2remove:

        # Find folders matching the pattern
        contrast_folders = [str(item) for item in pathlib.Path(path2read_real).rglob(case2remove) if pathlib.Path(item).is_dir()]

        for contrast_folder in contrast_folders:

            shutil.rmtree(contrast_folder)



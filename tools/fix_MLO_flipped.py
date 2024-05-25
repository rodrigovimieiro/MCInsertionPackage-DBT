import sys
import numpy as np
import pydicom
import pathlib
import pandas as pd
import shutil
import matplotlib.pyplot as plt

from tqdm import tqdm

sys.path.insert(1, '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT')

from libs.utilities import makedir, filesep, writeDicom
from libs.methods import get_XYZ_calc_positions, get_breast_masks, process_dense_mask, \
    get_calc_cluster, get_XYZ_cluster_positions, get_projection_cluster_mask, \
    apply_mtf_mask_projs

# %%

if __name__ == '__main__':

    pathPatientCases = '/media/rodrigo/SSD480/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/'
    pathAuxLibs = 'libs'
    pathPatientDensity = pathPatientCases + '/density'
    pathPatientCalcs = pathPatientCases + '/calcifications'

    # List all patients
    patient_cases = [str(item) for item in pathlib.Path(pathPatientCases).glob("*") if pathlib.Path(item).is_dir()]

    df = pd.DataFrame(columns=['ID', 'PatientOrientation', 'Laterality', 'ViewPosition'])

    for patient_case in tqdm(patient_cases):

        exams = [str(item) for item in pathlib.Path(patient_case).glob("*") if
                 pathlib.Path(item).is_dir() and 'density' not in str(item) and 'calcifications' not in str(item)]

        for exam in exams:

            dcmFiles = [str(item) for item in pathlib.Path(exam).glob("*.dcm")]

            dcmH = pydicom.dcmread(dcmFiles[0])

            new_entry = {
                'PatientOrientation': dcmH.PatientOrientation,
                'Laterality': dcmH.Laterality,
                'ViewPosition': dcmH.ViewPosition,
                'ID': "_".join(exam.split('/')[-2:])}

            df = df.append(new_entry, ignore_index=True)

            if new_entry['Laterality'] == 'L' and new_entry['ViewPosition'] == 'MLO':
                flag_flipud = True
            else:
                flag_flipud = False

            if flag_flipud:

                # for dcmFile in dcmFiles:
                #
                #     dcmH = pydicom.dcmread(dcmFile)
                #
                #     dcmData = dcmH.pixel_array.copy()
                #
                #     dcmData = np.flipud(dcmData)
                #
                #     # Copy the generated data to the original dicom header
                #     dcmH.PixelData = np.ascontiguousarray(dcmData)
                #
                #     # Write dicom
                #     pydicom.dcmwrite(dcmFile,
                #                      dcmH,
                #                      write_like_original=True)
                #
                #     #######################################################################
                #
                #     exam_number = '/' + exam.split('/')[-1] + '/'
                #
                #     dcmFile_proc = dcmFile.replace('ACRIN_CLINICAL_DBT_PROJs_RAW_2016', 'Rod').replace(exam_number, exam_number + 'proc_rody/')
                #
                #     dcmH_proc = pydicom.dcmread(dcmFile_proc)
                #
                #     dcmData = dcmH_proc.pixel_array.copy()
                #
                #     dcmData = np.flipud(dcmData)
                #
                #     # Copy the generated data to the original dicom header
                #     dcmH_proc.PixelData = np.ascontiguousarray(dcmData)
                #
                #     # Write dicom
                #     pydicom.dcmwrite(dcmFile_proc,
                #                      dcmH_proc,
                #                      write_like_original=True)

                path2write_patient_name_density = "{}{}{}".format(pathPatientDensity , filesep(),
                                                                  "/".join(exam.split('/')[-2:]))
                path2write_patient_name_calcs = "{}{}{}".format(pathPatientCalcs, filesep(),
                                                                  "/".join(exam.split('/')[-2:]))
                try:
                    shutil.rmtree(path2write_patient_name_density)
                except OSError as e:
                    print(f"Error: {path2write_patient_name_density} : {e.strerror}")
                try:
                    shutil.rmtree(path2write_patient_name_calcs)
                except OSError as e:
                    print(f"Error: {path2write_patient_name_calcs} : {e.strerror}")


            # df.to_csv('processed_cases.csv', index=False)

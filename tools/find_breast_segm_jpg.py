import sys
import os
import pathlib
import pandas as pd
import shutil
import pydicom

from tqdm import tqdm

sys.path.insert(1, '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT')

from libs.utilities import filesep

# %%

if __name__ == '__main__':

    pathPatientCases = '/media/rodrigo/SSD480/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/'
    pathAuxLibs = 'libs'
    pathPatientDensity = pathPatientCases + '/density'
    pathPatientCalcs = pathPatientCases + '/calcifications'

    path2write = '/tmp/tmi_rod/'

    # List all patients
    patient_cases = [str(item) for item in pathlib.Path(pathPatientCases).glob("*") if pathlib.Path(item).is_dir()]

    df = pd.DataFrame(columns=['ID', 'PatientOrientation', 'Laterality', 'ViewPosition'])

    for patient_case in tqdm(patient_cases):

        exams = [str(item) for item in pathlib.Path(patient_case).glob("*") if
                 pathlib.Path(item).is_dir() and 'density' not in str(item) and 'calcifications' not in str(item)]

        for exam in exams:

            dcmFiles = [str(item) for item in pathlib.Path(exam).glob("*.dcm")]

            dcmH = pydicom.dcmread(dcmFiles[0])

            if dcmH.ViewPosition == 'MLO':

                path2write_patient_name_density = "{}{}{}/Result_Images/".format(pathPatientDensity, filesep(),
                                                                  "/".join(exam.split('/')[-2:]))

                jpgFiles = [str(item) for item in pathlib.Path(path2write_patient_name_density).glob("*density_segmentation.jpg")]

                if not os.path.exists(path2write + "/".join(exam.split('/')[-2:])):
                    os.makedirs(path2write + "/".join(exam.split('/')[-2:]))

                for jpgFile in jpgFiles:
                    shutil.copy(jpgFile, path2write + "/".join(exam.split('/')[-2:]))






#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 10:27:29 2022

@author: rodrigo

This code does the whole thing - it generates artificial clusters,
finds candidate positions depending on the breast density and
insert the lesion in a clinical case.

OBS: This code uses LIBRA to estimate density. Please refer to
https://www.pennmedicine.org/departments-and-centers/department-of-radiology/radiology-research/labs-and-centers/biomedical-imaging-informatics/cbig-computational-breast-imaging-group
for more information.
 
"""

import sys
import numpy as np
import pydicom
import pathlib
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(1, '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT')

from libs.utilities import makedir, filesep, writeDicom
from libs.methods import get_XYZ_calc_positions, get_breast_masks, process_dense_mask, \
    get_calc_cluster, get_XYZ_cluster_positions, get_projection_cluster_mask, \
    apply_mtf_mask_projs

#%%

if __name__ == '__main__':

    np.random.seed(564456)
    
    cluster_dimensions  = (5, 5, 5)              # In mm
    calc_dimensions     = (1, 1, 1)                 # In mm
    
    cluster_pixel_size = 0.048                      # In mm
    detector_size = 0.140                             # In mm
    n_max_calcs = 7
    
    pathPatientCases            = '/media/rodrigo/SSD480/ACRIN_CLINICAL_DBT_PROJs_RAW_2016/'
    pathCalcifications          = '/media/rodrigo/Dados_2TB/Imagens/UPenn/Phantom/VCT/db_calcium/calc'
    pathCalcificationsReport    = '/media/rodrigo/Dados_2TB/Imagens/UPenn/Phantom/VCT/db_calcium/report.xlsx'
    pathMatlab                  = '/usr/local/MATLAB/R2019a/bin/matlab'
    pathLibra                   = 'LIBRA-1.0.4'
    pathAuxLibs                 = 'libs'
    pathBuildDirpyDBT           = '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT/build'
    pathMTF                     = 'data/mtf_function_hologic3d_fourier.npy'
    pathPatientDensity          = pathPatientCases + '/density'
    pathPatientCalcs            = pathPatientCases + '/calcifications'
    
    # Flags
    flags = dict()
    flags['fix_compression_paddle'] = False
    flags['print_debug'] = True
    flags['vct_image'] = False
    flags['delete_masks_folder'] = False
    flags['force_libra'] = False

    cluster_size = [int(x/cluster_pixel_size) for x in cluster_dimensions]
    calc_window  = [int(x/cluster_pixel_size) for x in calc_dimensions]

    contrasts = [0.1]
    for x in range(14):
        contrasts.append(np.round(0.85 * contrasts[x], 3))
    
    # List all patients    
    patient_cases = [str(item) for item in pathlib.Path(pathPatientCases).glob("*") if pathlib.Path(item).is_dir()]
    
    makedir(pathPatientDensity)
    makedir(pathPatientCalcs)

    with open('data/IDs_calc.txt', 'r') as file:
        lines = file.readlines()

    # Assuming each line contains an ID
    ids2run = [line.strip() for line in lines]

    file = pathlib.Path('data/IDs_processed.txt')
    if file.exists():
        with file.open('r') as file:
            lines = file.readlines()
        ids_processed = [line.strip() for line in lines]
    else:
        ids_processed = []

    try:
        df = pd.read_csv('data/status.csv')
    except:
        df = pd.DataFrame({'ID': ids2run, 'nROIsCluster': len(ids2run) * [0], 'nROIsNoCluster': len(ids2run) * [0]})

    n_rois_cluster_total = 0
    n_rois_no_cluster_total = 0

    for patient_case in patient_cases:
        
        exams = [str(item) for item in pathlib.Path(patient_case).glob("*") if pathlib.Path(item).is_dir() and 'density' not in str(item) and 'calcifications' not in str(item)]
        
        for exam in exams:

            current_id = '/'.join(exam.split('/')[-2:])

            # if current_id != '29738414/903':
            #     continue

            # ID read not in ID to run
            if current_id not in ids2run or current_id in ids_processed:
                continue

            with open('data/IDs_processed.txt', 'a') as file:
                file.write(current_id + '\n')

            print("Processing exam: " + current_id)

            #%%

            dcmFiles = [str(item) for item in pathlib.Path(exam).glob("*.dcm")]

            # Run LIBRA
            mask_dense, mask_breast, bdyThick = get_breast_masks(dcmFiles, exam, pathPatientDensity, pathLibra, pathMatlab, pathAuxLibs, flags)

            # Process dense mask
            final_mask, flags = process_dense_mask(mask_dense, mask_breast, cluster_size, dcmFiles, flags)

            del mask_dense

            #%%

            # Reconstruct the dense mask and find the coords for the cluster
            (x_clust, y_clust, z_clust), geo, libFiles, bound_X, slice2check = get_XYZ_cluster_positions(final_mask, mask_breast, bdyThick, pathBuildDirpyDBT, flags)

            del mask_breast

            n_rois = len(x_clust)

            if n_rois_cluster_total < 115:
                n_rois_cluster = n_rois
                n_rois_no_cluster = 0
            else:
                n_rois_cluster = 0
                n_rois_no_cluster = n_rois

            n_rois_cluster_total += n_rois_cluster
            n_rois_no_cluster_total += n_rois_no_cluster

            print("Total number of ROIs (cluster): " + str(n_rois_cluster_total))
            print("Total number of ROIs (NO cluster): " + str(n_rois_no_cluster_total))

            df.loc[df.ID == current_id, 'nROIsCluster'] = n_rois_cluster
            df.loc[df.ID == current_id, 'nROIsNoCluster'] = n_rois_no_cluster

            path2write_patient_name = "{}{}{}".format(pathPatientCalcs, filesep(), "/".join(exam.split('/')[-2:]))

            makedir(path2write_patient_name)

            # Save slice with density
            # plt.imsave("{}{}slice_density.png".format(path2write_patient_name, filesep()),
            #                                             cv2.resize(255*np.uint8(slice2check), (slice2check.shape[1] // 4, slice2check.shape[0] // 4)),
            #                                             cmap='gray')

            df.to_csv('data/status.csv')

            if n_rois == 0:
                continue

            del final_mask

            # %%

            projs_masks = np.zeros((geo.nv, geo.nu, geo.nProj))

            for idr in range(n_rois_cluster):

                if flags['print_debug']:
                    print("Processing ROI {}/{}...".format(idr+1, len(x_clust)))

                number_calc = np.random.randint(5, n_max_calcs+1)

                # Get  X, Y and Z position for each calcification
                (x_calc, y_calc, z_calc), _ = get_XYZ_calc_positions(number_calc, cluster_size, calc_window, flags)

                # Load each calcification and put them on specified position
                roi_3D, contrasts_individual = get_calc_cluster(pathCalcifications, pathCalcificationsReport, number_calc,
                                                                cluster_size, x_calc, y_calc, z_calc, flags)

                # Inserting cluster at position and projecting the cluster mask
                projs_masks += get_projection_cluster_mask(roi_3D, contrasts_individual, geo, x_clust[idr], y_clust[idr], z_clust[idr], cluster_pixel_size, libFiles, flags)

            # Apply the fitted MTF on the mask projections
            projs_masks_mtf = apply_mtf_mask_projs(projs_masks, len(dcmFiles), detector_size, pathMTF, flags)


            cropCoords_file = pathlib.Path('{}{}{}{}Result_Images{}cropCoords.npy'.format(pathPatientDensity , filesep(), "/".join(exam.split('/')[-3:]), filesep(), filesep()))
            if cropCoords_file.is_file():
                cropCoords = np.load(str(cropCoords_file))
                flags['mask_crop'] = True
                flags['cropCoords'] = cropCoords
            else:
                flags['mask_crop'] = False


            flags['calc_coords'] = (x_clust, y_clust, z_clust)
            flags['cluster_flag'] = np.hstack((n_rois_cluster*[1], n_rois_no_cluster*[0]))
            flags['bound_X'] = bound_X
            flags['bdyThick'] = bdyThick

            np.save(path2write_patient_name + '{}flags'.format(filesep()), flags)

            for idc, contrast in enumerate(contrasts):

                if n_rois_cluster == 0 and idc > 0:
                    continue

                path2write_contrast = "{}{}contrast_{:.3f}".format(path2write_patient_name , filesep(), contrast)

                makedir(path2write_contrast)

                for dcmFile in dcmFiles:

                    dcmH = pydicom.dcmread(str(dcmFile))

                    dcmData = dcmH.pixel_array.astype('float32').copy()

                    if flags['mask_crop']:
                        dcmData = dcmData[cropCoords[0]:cropCoords[1], cropCoords[2]:cropCoords[3]]

                    if not flags['right_breast']:
                        dcmData = np.fliplr(dcmData)

                    ind = int(str(dcmFile).split('/')[-1].split('_')[-1].split('.')[0])

                    if n_rois_cluster > 0:
                        tmp_mask = np.abs(projs_masks_mtf[:,:,ind])
                        tmp_mask = (tmp_mask - tmp_mask.min()) / (tmp_mask.max() - tmp_mask.min())
                        tmp_mask[tmp_mask > 0] *= contrast
                        tmp_mask = 1 - tmp_mask

                        dcmData[:,bound_X:] = dcmData[:,bound_X:] * tmp_mask

                    if not flags['right_breast']:
                        dcmData = np.fliplr(dcmData)

                    dcmFile_tmp = path2write_contrast + '{}{}'.format(filesep(), dcmFile.split('/')[-1])

                    writeDicom(dcmFile_tmp, np.uint16(dcmData))

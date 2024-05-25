#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 28 12:37:32 2022

@author: rodrigo
"""

import sys
import numpy as np
import pydicom
import pathlib
import pandas as pd
import matplotlib.pyplot as plt

from scipy.io import loadmat

sys.path.insert(1, '../')
sys.path.insert(1, '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT')

from libs.utilities import makedir, filesep, writeDicom

from pydbt.functions.projection_operators import backprojectionDDb_cuda
from pydbt.parameters.parameterSettings import geometry_settings
from pydbt.functions.initialConfig import initialConfig
from pydbt.functions.dataPreProcess import dataPreProcess


#%%

if __name__ == '__main__':
    
    pathPatientCases            = '/media/rodrigo/Dados_2TB/Imagens/HC_Barretos/mc_insert'
    pathBuildDirpyDBT           = '/home/rodrigo/Documents/Rodrigo/Codigos/pyDBT/build'
    pathPatientDensity          = pathPatientCases + '/density'
    pathPatientCalcs            = pathPatientCases + '/calcifications'

    contrasts = [0.2]
    for x in range(14):
        contrasts.append(np.round(0.85 * contrasts[x], 3))
    
    # List all patients    
    patient_cases = [str(item) for item in pathlib.Path(pathPatientCalcs).glob("*") if pathlib.Path(item).is_dir()]
    
        
    # Call function for initial configurations
    libFiles = initialConfig(buildDir=pathBuildDirpyDBT, createOutFolder=False)
    
    # Create a DBT geometry  
    geo = geometry_settings()
    geo.Hologic()

    file = pathlib.Path('../data/IDs_processed_recon.txt')
    if file.exists():
        with file.open('r') as file:
            lines = file.readlines()
        ids_processed = [line.strip() for line in lines]
    else:
        ids_processed = []

    file = pathlib.Path('../data/to_exclude.txt')
    if file.exists():
        with file.open('r') as file:
            lines = file.readlines()
        to_exclude = [line.strip() for line in lines]
    else:
        to_exclude = []

    df = pd.read_csv('../data/status.csv')
    # Filter cases that have ROIs
    df = df[~((df['nROIsNoCluster'] == 0) & (df['nROIsCluster'] == 0))]

    for patient_case in patient_cases:
        
        exams = [str(item) for item in pathlib.Path(patient_case).glob("*") if pathlib.Path(item).is_dir()]
        
        for exam in exams:

            current_id = '/'.join(exam.split('/')[-2:])

            # if current_id != '29680212/2105':
            #     continue

            # ID read not in ID to run
            if current_id not in df['ID'].values or current_id in ids_processed or current_id in to_exclude:
                continue

            print("Processing exam: " + current_id)

            with open('../data/IDs_processed_recon.txt', 'a') as file:
                file.write(current_id + '\n')

            path2write_patient_name = "{}{}{}".format(pathPatientCalcs , filesep(), "/".join(exam.split('/')[-2:]))

            flags = np.load(path2write_patient_name + '{}flags.npy'.format(filesep()), allow_pickle=True)[()]

            bdyThick = flags['bdyThick']

            nROIsNoCluster = df[df.ID == current_id]['nROIsNoCluster'].iloc[0]
            nROIsCluster = df[df.ID == current_id]['nROIsCluster'].iloc[0]

            for idc, contrast in enumerate(contrasts):

                if idc != 0 and nROIsCluster == 0:
                    break

                bound_X = flags['bound_X']#np.max((int(np.where(np.sum(mask_breast, axis=0) > 1)[0][0]) - 30, 0))

                path2write_contrast = "{}{}recon_contrast_{:.3f}_ROI".format(path2write_patient_name , filesep(), contrast)
                
                path2write_contrast = "{}{}contrast_{:.3f}".format(path2write_patient_name , filesep(), contrast)
    
                dcmFiles = [str(item) for item in pathlib.Path(path2write_contrast).glob("*.dcm")]
                
                dcmData = len(dcmFiles) * [None]
                
                for dcmFile in dcmFiles:
                    
                    dcmH = pydicom.dcmread(str(dcmFile), force=True)
                    
                    ind = int(str(dcmFile).split('/')[-1].split('_')[-1].split('.')[0])
                    
                    dcmData[ind] = dcmH.pixel_array.astype('float32').copy()
                 
                    
                dcmData = np.stack(dcmData, axis=-1) 
                       
                
                if not flags['right_breast']:
                    dcmData = np.fliplr(dcmData)
                    
                if flags['flip_projection_angle']:
                    dcmData = np.flip(dcmData, axis=-1)
                 
                # Crop to save reconstruction time
                dcmData = dcmData[:,bound_X:,:]
                
                
                geo.nx = dcmData.shape[1]      # number of voxels (columns)
                geo.ny = dcmData.shape[0]      # number of voxels (rows)
                geo.nu = dcmData.shape[1]      # number of pixels (columns)
                geo.nv = dcmData.shape[0]      # number of pixels (rows)
                geo.nz = np.ceil(bdyThick/geo.dz).astype(int)

                geo.dy = 0.14
                geo.dx = 0.14
                
                # dcmData, _ = dataPreProcess(dcmData, geo,  flagCropProj=False)

                geo.detAngle = 0

                vol = backprojectionDDb_cuda(np.float64(dcmData), geo, -1, libFiles)
                
                vol[vol < 0 ] = 0
                
                vol = (vol / vol.max()) * (2**12-1)
                
                vol = np.uint16(vol)
                    
                
                # The cluster origin is located at the same as the DBT systemes, i.e., right midle. Z is at the half
                cluster_pixel_size = int(20/0.140)

                (x_clust, y_clust, z_clust) = flags['calc_coords']

                cluster_flag = flags['cluster_flag']

                for idr in range(len(x_clust)):

                    ind_x = int(x_clust[idr] - (cluster_pixel_size / 2))
                    ind_y = int(y_clust[idr] - (cluster_pixel_size / 2))
                    ind_z = z_clust[idr]
                    # plt.imshow(vol[ind_y:ind_y+cluster_pixel_size,
                    #                 ind_x:ind_x+cluster_pixel_size,
                    #                 ind_z], 'gray')
                    # plt.show()

                    if cluster_flag[idr] == 0 and idc > 0:
                        continue

                    path2write_contrast = "{}{}recon_roi_{:02d}_contrast_{:.3f}_ROI_{}".format(path2write_patient_name ,
                                                                                               filesep(),
                                                                                               idr,
                                                                                               contrast,
                                                                                               'cluster1' if cluster_flag[idr] else 'cluster0')

                    makedir(path2write_contrast)

                    for z in range(-7, 8):

                        dcmFile_tmp = path2write_contrast + '{}{}.dcm'.format(filesep(), ind_z + z)

                        writeDicom(dcmFile_tmp, np.uint16(vol[ind_y:ind_y+cluster_pixel_size,
                                                              ind_x:ind_x+cluster_pixel_size,
                                                              ind_z + z]))
                
                

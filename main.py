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

import cv2
import sys
import subprocess
import pydicom
import numpy as np
import pathlib
import matplotlib.pyplot as plt

from scipy.io import loadmat

from libs.utilities import makedir, removedir, filesep
from libs.getXYZpositions import getXYZpositions

sys.path.insert(1, '/home/rodrigo/Documents/rodrigo/codes/pyDBT')

from pydbt.parameters.parameterSettings import geometry_settings
from pydbt.functions.initialConfig import initialConfig
from pydbt.functions.dataPreProcess import dataPreProcess
from pydbt.functions.backprojectionDDb import backprojectionDDb
from pydbt.functions.projectionDDb import projectionDDb
from pydbt.functions.phantoms import phantom3d

#%%

if __name__ == '__main__':
    
    
    cluster_size = (200,200,28)
    calc_window = (80,80,10)
    number_calc = 8
        
    contrasts = [0.4]
    for x in range(14):
        contrasts.append(0.85 * contrasts[x])

    
    pathPatientCases ='/media/rodrigo/Data/images/UPenn/Phantom/VCT/VCT_Bruno_500/GE-projs'
    pathMatlab = '/usr/local/R2019a/bin/matlab'
    pathDensityMask = pathPatientCases + '/PatientDensity'
    path2write = 'outputs'
    pathLibra = 'LIBRA-1.0.4'
    
    
    makedir(path2write)
    makedir(pathPatientCases + '/density')
    
    patient_cases = [str(item) for item in pathlib.Path(pathPatientCases).glob("*") if pathlib.Path(item).is_dir()]
    
    for patient_case in patient_cases:
        
        patient_name = patient_case.split('/')[-1]
        
        path2write_patient_name = "{}{}{}".format(pathPatientCases + '/density' , filesep(),patient_name)
        
        makedir(path2write_patient_name)
                
        dcmFiles = [str(item) for item in pathlib.Path(patient_case).glob("*.dcm")]
        
        mask_dense = len(dcmFiles) * [None]
        mask_breast = len(dcmFiles) * [None]
        
        dcmHdrs = len(dcmFiles) * [None]
        
        for idX, dcmFile in enumerate(dcmFiles):
            
            dcmH = pydicom.dcmread(str(dcmFile))
            
            dcmHdrs[idX] = dcmH
            
            ind = int(str(dcmFile).split('/')[-1].split('.')[0][1:])
            
            dcmH.ImagesInAcquisition = '1'
            dcmH.Manufacturer = 'GE MEDICAL'
            # ViewPosition
            dcmH.add_new((0x0018,0x5101),'CS', 'CC')
            # BodyPartThickness
            dcmH.add_new((0x0018,0x11A0),'DS', 60)
            # CompressionForce
            dcmH.add_new((0x0018,0x11A2),'DS', 119.5)
            # ExposureTime
            dcmH.add_new((0x0018,0x1150),'DS', 770)
            # XrayTubeCurrent
            dcmH.add_new((0x0018,0x1151),'DS', 100)
            # Exposure
            dcmH.add_new((0x0018,0x1152),'DS', 87)
            # ExposureInuAs
            dcmH.add_new((0x0018,0x1153),'DS', 86800)
            # kvP
            dcmH.add_new((0x0018,0x0060),'DS', 29)
            
            
            dcmFile_tmp = path2write_patient_name + '{}{}'.format(filesep(), dcmFile.split('/')[-1])
            
            pydicom.dcmwrite(dcmFile_tmp,
                             dcmH, 
                             write_like_original=True) 
            
            
            subprocess.run("{} -r \"addpath(genpath('{}'));addpath('libs');run('libra_startup');libra('{}', '{}', 1);exit\" -nodisplay -nosplash".format(pathMatlab,
                                                          pathLibra,
                                                          dcmFile_tmp,
                                                          path2write_patient_name), shell=True)
        
            res = loadmat('{}{}Result_Images{}Masks__{}.mat'.format(path2write_patient_name, filesep(), filesep(), ind))['res']
            mask_dense[ind] = res['DenseMask'][0][0]
            mask_breast[ind] = res['BreastMask'][0][0]
                        
        removedir(path2write_patient_name)
                
        del res

        #%%
    
        mask_dense = np.stack(mask_dense, axis=-1)
        mask_breast = np.stack(mask_breast, axis=-1)
        
        # Crop
        mask_dense = mask_dense[:,1500:,:]
        mask_breast = mask_breast[:,1500:,:]
        
        # Mask erosion to avoid regions too close to the skin, chest-wall and
        # pectoral muscle
        mask_breast[:,-1,:] = 0
        mask_breast[:,0,:] = 0
        
        element = cv2.getStructuringElement(shape=cv2.MORPH_ELLIPSE, ksize=(cluster_size[0]//2,cluster_size[1]//2))
        # Removes isolated pixels
        element1 = cv2.getStructuringElement(cv2.MORPH_RECT, (6,6))
        element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
        
        final_mask = np.empty_like(mask_breast)
        
        for z in range(mask_dense.shape[-1]):
    
            # Mask erosion 
            mask_breast[:,:,z] = cv2.erode(mask_breast[:,:,z], element)
            
            # Removes isolated pixels
            clean_dense_mask = cv2.morphologyEx(mask_dense[:,:,z], cv2.MORPH_CLOSE, element1)
            clean_dense_mask = cv2.morphologyEx(clean_dense_mask, cv2.MORPH_OPEN, element2)
    
            mask_dense[:,:,z] = clean_dense_mask * mask_dense[:,:,z]        

                
        # Map of possible positions
        final_mask = mask_breast * mask_dense
        
        del mask_dense, mask_breast, clean_dense_mask

        
        #%%
          
        # Call function for initial configurations
        libFiles = initialConfig(buildDir='/home/rodrigo/Documents/rodrigo/codes/pyDBT/build', createOutFolder=False)
        
        # Create a DBT geometry  
        geo = geometry_settings()
        geo.GE()
        
        geo.nu = final_mask.shape[1]      # number of pixels (columns)
        geo.nv = final_mask.shape[0]      # number of pixels (rows)
        geo.nu = final_mask.shape[1]      # Number of pixels (columns)
        geo.nz = 127                      # Breast -> 63.3m
        
        
        vol = backprojectionDDb(np.float64(final_mask), geo, libFiles)
        
        del final_mask
        
        # Avoid cluster on top or bottom 
        vol[:,:,-(cluster_size[-1]+2):] = 0
        vol[:,:,:(cluster_size[-1]+2)] = 0
                
        # Ramdomly selects one of the possible points
        i,j,k = np.where(vol>0.5)
        randInt = np.random.randint(0,i.shape[0])
        coords = (i[randInt],j[randInt],k[randInt])

        # Insert the MC Cluster
        # inserted = insertMC(dcmData, maskMC[:,:,mcNum], coords, contrast, angle)
        
        
#%%      
        (x_pos, y_pos, z_pos), _ = getXYZpositions(number_calc, cluster_size, calc_window)
        
        calc_3d = phantom3d('',
                            n=10,
                            phantom_matrix=np.array([[1.0, 0.69, 0.92, 0.81, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]))
        
        
        calcs_3D = number_calc * [calc_3d]
        
        ROI_3D = np.zeros(cluster_size)
        
        contrasts = np.hstack((1, np.linspace(0.5,1,100,endpoint=False)[np.random.randint(0,99,number_calc-1)]))
        
        StackROI=[];
        
        for idX, (calc_3D, contrast) in enumerate(zip(calcs_3D, contrasts)):
            
            calc_3D = contrast * (calc_3D / calc_3D.max())
            
            ROI_3D[x_pos[idX]-(calc_3D.shape[0]//2):x_pos[idX]-(calc_3D.shape[0]//2)+calc_3D.shape[0],
                   y_pos[idX]-(calc_3D.shape[1]//2):y_pos[idX]-(calc_3D.shape[1]//2)+calc_3D.shape[1],
                   z_pos[idX]-(calc_3D.shape[2]//2):z_pos[idX]-(calc_3D.shape[2]//2)+calc_3D.shape[2]] +=  calc_3D
            
        del  calcs_3D, calc_3d
        
#%% 
        
        vol[:] = 0
        vol[coords[0]-(ROI_3D.shape[0]//2):coords[0]-(ROI_3D.shape[0]//2)+ROI_3D.shape[0],
            coords[1]-(ROI_3D.shape[1]//2):coords[1]-(ROI_3D.shape[1]//2)+ROI_3D.shape[1],
            coords[2]-(ROI_3D.shape[2]//2):coords[2]-(ROI_3D.shape[2]//2)+ROI_3D.shape[2]] += ROI_3D
        
        
        projs_masks = projectionDDb(np.float64(vol), geo, libFiles)
        
        makedir(path2write_patient_name)
        
        for idX, dcmHdr in enumerate(dcmHdrs):
            
            ind = int(str(dcmFiles[idX]).split('/')[-1].split('.')[0][1:])
            
            dcmData = dcmHdr.pixel_array.astype('float32').copy()
                        
            tmp_mask = np.abs(projs_masks[:,:,ind])
            tmp_mask = (tmp_mask - tmp_mask.min()) / (tmp_mask.max() - tmp_mask.min())
            tmp_mask[tmp_mask > 0] *= 0.3
            tmp_mask = 1 - tmp_mask
            
            dcmData[:,1500:] = dcmData[:,1500:] * tmp_mask
                        
            dcmHdr.PixelData = np.uint16(dcmData).copy()
            
            dcmFile_tmp = path2write_patient_name + '{}{}'.format(filesep(), dcmFiles[idX].split('/')[-1])
            
            pydicom.dcmwrite(dcmFile_tmp,
                             dcmHdr, 
                             write_like_original=True) 
            
            
            
            
            
        




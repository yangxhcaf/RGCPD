#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 18 16:00:12 2018

@author: semvijverberg
"""
import time
start_time = time.time()
import numpy as np
import cartopy.crs as ccrs
import os, sys

import inspect
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
script_dir = os.path.join(curr_dir, '..', 'RGCPD')
# To link modules in RGCPD folder to this script
os.chdir(script_dir)
sys.path.append(script_dir)

filename_exp = os.path.join(curr_dir,
                'Data_ERAint/ex_t2mmax_sst_30day_pcA_set1a_ac0.01_at0.2.npy')

ex = np.load(filename_exp, encoding='latin1').item()

central_lon_plots = 240
map_proj = ccrs.LambertCylindrical(central_longitude=central_lon_plots)
#%%
# *****************************************************************************
# *****************************************************************************
# Part 3 Start RGCPD python script (settings stored in dictionary 'ex')
# *****************************************************************************
# *****************************************************************************
import wrapper_RGCPD_tig3
# =============================================================================
# Find precursor fields (potential precursors)
# =============================================================================
ex, outdic_actors = wrapper_RGCPD_tig3.calculate_corr_maps(ex, map_proj)
#%%
# =============================================================================
# Run tigramite to extract causal precursors
# =============================================================================
parents_RV, var_names = wrapper_RGCPD_tig3.run_PCMCI(ex, outdic_actors, map_proj)
#%%
# =============================================================================
# Plot final results
# =============================================================================
wrapper_RGCPD_tig3.plottingfunction(ex, parents_RV, var_names, outdic_actors, map_proj)
print("--- {:.2} minutes ---".format((time.time() - start_time)/60))
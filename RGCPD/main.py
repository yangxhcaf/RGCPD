#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  9 17:48:31 2018

@author: semvijverberg
"""
import time
start_time = time.time()
import inspect, os, sys
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
script_dir = "/Users/semvijverberg/surfdrive/Scripts/RGCPD/RGCPD" # script directory
# To link modules in RGCPD folder to this script
os.chdir(script_dir)
sys.path.append(script_dir)
#if sys.version[:1] == '3':
#    from importlib import reload as rel
import numpy as np
import pandas as pd
import functions_pp
import wrapper_RGCPD_tig
import plot_maps
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
copy_stdout = sys.stdout

# *****************************************************************************
# *****************************************************************************
# Part 1 Downloading (opt), preprocessing(opt), choosing general experiment settings
# *****************************************************************************
# *****************************************************************************
# We will be discriminating between precursors and the Response Variable
# (what you want to predict).

# this will be your basepath, all raw_input and output will stored in subfolder
# which will be made when running the code
base_path = "/Users/semvijverberg/surfdrive/"
dataset   = 'era5' # choose 'era5' or 'ERAint'
exp_folder = 'RGCPD_mcKinnon'
path_raw = os.path.join(base_path, 'Data_{}/' 
                        'input_raw'.format(dataset))
path_pp  = os.path.join(base_path, 'Data_{}/' 
                        'input_pp'.format(dataset))
if os.path.isdir(path_raw) == False : os.makedirs(path_raw)
if os.path.isdir(path_pp) == False: os.makedirs(path_pp)

# *****************************************************************************
# Step 1 Create dictionary and variable class (and optionally download ncdfs)
# *****************************************************************************
# The dictionary is used as a container with all information for the experiment
# The dic is saved after the post-processes step, so you can continue the experiment
# from this point onward with different configurations. It also stored as a log
# in the final output.
#
ex = dict(
     {'dataset'     :       dataset,
     'grid_res'     :       1.0,
     'startyear'    :       1979, # download startyear
     'endyear'      :       2018, # download endyear
     'input_freq'   :       'daily',
     'months'       :       list(range(1,12+1)), # downoad months
     # if dealing with daily data, give string as 'month-day', i.e. '07-01'
     # if dealing with monthly data, the day of month is neglected 
     'startperiod'  :       '06-22', # RV period, period you want to predict
     'endperiod'    :       '08-24', # RV period
     'sstartdate'   :       '01-01', # extended data period loaded (for lags)
     'senddate'     :       '09-30', # extended data period loaded
     'tfreqlist'    :       [10],
     'selbox'       :       {'la_min':-10, # select domain in degrees east
                             'la_max':80,
                             'lo_min':-180,
                             'lo_max':360}, 
     'anomaly'      :       True, # use absolute or anomalies?
     'verbosity'    :       0, # higher verbosity gives more feedback in terminal
     'base_path'    :       base_path,
     'path_raw'     :       path_raw,
     'path_pp'      :       path_pp}
     )



if ex['dataset'] == 'ERAint':
    import download_ERA_interim_API as ECMWF
elif ex['dataset'] == 'era5':
    import download_ERA5_API as ECMWF

# =============================================================================
# What is the data you want to load / download (4 options)
# =============================================================================
# Option 1:
ECMWFdownload = True
# Option 2:
import_precursor_ncdf = True
# Option 3:
import_RV_ncdf = False
# Option 4:
importRV_1dts = True
# Option 5:
ex['import_prec_ts'] = False


# Option 1111111111111111111111111111111111111111111111111111111111111111111111
# Download ncdf fields (in ex['vars']) through ECMWF API?
# 11111111111111111111111111111111111111111111111111111111111111111111111111111
# only analytical fields

# Info to download ncdf from ECMWF, atm only analytical fields (no forecasts)
# You need the ecmwf-api-client package for this option. See http://apps.ecmwf.int/datasets/.
if ECMWFdownload == True:
    if ex['input_freq'] == 'daily':
        # select hours you want to download from analysis
        ex['time']      =       pd.date_range(start='00:00', end='23:00', 
                                freq=(pd.Timedelta(6, unit='h')))
        

    ex['vars']      =       [['sst'],
                               ['sea_surface_temperature'],
                               ['sfc'], [0]]

#    ex['vars']     =   [
#                        ['sst', 'u'],                                          # list of shortnames
#                        ['sea_surface_temperature', 'u_component_of_wind'],    # list of ECMWF var_names
#                        ['sfc', 'pl'],                                         # list of Levtypes
#                        [0, 500],                                              # list Vertical levels
#                        ]
else:
    ex['vars']      =       [[]]

# Option 2222222222222222222222222222222222222222222222222222222222222222222222
# Import ncdf lonlat fields to be precursors.
# 22222222222222222222222222222222222222222222222222222222222222222222222222222
# Must have same period, daily data and on same grid
if import_precursor_ncdf == True:
    # var names may not contain underscores, data is assumed to be in path_pp 
    # or path_raw (if now detrended yet)
    ex['precursor_ncdf'] = [['name1', 'filename1'],['name2','filename2']]
 
else:
    ex['precursor_ncdf'] = [[]]

# Option 3333333333333333333333333333333333333333333333333333333333333333333333
# Import precursor timeseries (daily) 
# 33333333333333333333333333333333333333333333333333333333333333333333333333333
if ex['import_prec_ts'] == True:
    # Requires filepath to a hdf5 pandas dataframe with a df called 'df_data'
    # should contain a boolean mask with the TrainIsTrue column and RV_mask
    ex['precursor_ts'] = [['name1', 'filepath1']]
                         
else:                            
    ex['precursor_ts'] = None
    
    
    
# Option 4444444444444444444444444444444444444444444444444444444444444444444444
# Import Response Variable 1-dimensional time serie.
# 44444444444444444444444444444444444444444444444444444444444444444444444444444
if import_RV_ncdf == True:
    ex['RVnc_name'] =  ['RV_name', 'filepath']   
else:
    ex['RVnc_name'] = []


# Option 5555555555555555555555555555555555555555555555555555555555555555555555
# Import Response Variable 1-dimensional time serie.
# 55555555555555555555555555555555555555555555555555555555555555555555555555555
ex['importRV_1dts'] = importRV_1dts
if importRV_1dts == True:
    # file should be in path_pp/RV_ts/{file}
    ex['RV_name'] = 't2mmax_E-US'
    ex['RV_detrend'] = False
    ex['RVts_filename'] = 'filename'






# =============================================================================
# Note, ex['vars'] is expanded if you have own ncdfs, the first element of array will
# always be the Response Variable, unless you set importRV_1dts = True
# =============================================================================
# =============================================================================
# Make a class for each variable, this class contains variable specific information,
# needed to download and post process the data. Along the way, information is added
# to class based on decisions that you make.
# =============================================================================
    
if ECMWFdownload == True:
    for idx in range(len(ex['vars'][0]))[:]:
        # class for ECMWF downloads
        var_class = ECMWF.Var_ECMWF_download(ex, idx)
        ECMWF.retrieve_field(var_class)
        ex[ex['vars'][0][idx]] = var_class

if import_RV_ncdf == True and importRV_1dts == False:
    ex['RV_name'] = ex['RVnc_name'][0]
    ex['vars'][0].insert(0, ex['RV_name'])
    var_class = functions_pp.Var_import_RV_netcdf(ex)
    ex[ex['RVnc_name'][0]] = var_class
    print(('inserted own netcdf as Response Variable {}\n'.format(ex['RV_name'])))

if import_precursor_ncdf == True:
    print(ex['precursor_ncdf'][0][0])
    for idx in range(len(ex['precursor_ncdf'])):
        var_class = functions_pp.Var_import_precursor_netcdf(ex, idx)
        ex[var_class.name] = var_class

# =============================================================================
# Combine precursor information
# =============================================================================
list_varclass = []
allvar = ex['vars'][0] # list of all variable names
for var in allvar[:]: # loop over all variables
    list_varclass.append(ex[var])

kwrgs_corr = {'list_varclass':list_varclass}
# =============================================================================
# Now we have collected all info on what variables will be analyzed, based on
# downloading, own netcdfs / importing RV time serie.
# =============================================================================
if importRV_1dts == True:
    RV_actor_names = ex['RV_name'] + '_' + "_".join(ex['vars'][0])
elif importRV_1dts == False:
    # if no time series is imported, it will take the first of ex['vars] as the
    # Response Variable
    ex['RV_name'] = ex['vars'][0][0]
    RV_actor_names = "_".join(ex['vars'][0])
    # if import RVts == False, then a spatial mask is used for the RV
    ex['spatial_mask_naming'] = '{name_to_refer_to_experiment}'
    ex['spatial_mask_file'] = 'filepath'
    # You can also include a latitude longitude box as a spatial mask by just 
    # giving a list [west_lon, east_lon, south_lat, north_lat] instead of a file
#    ex['spatial_mask_file'] = [18.25, 24.75, 75.25, 87.75]


# =============================================================================
# General Temporal Settings: frequency, lags, part of year investigated
# =============================================================================
# Information needed to pre-process,
for freq in ex['tfreqlist']:
    ex['tfreq'] = freq
    # choose lags to test, strongly recommended to choose only one lag, e.g. 0 or 1
    # Tigramite will take into account the lag, i.e. shift the timeseries up to
    # tigr_tau_max
    ex['lags_i'] = np.array([0], dtype=int)
    ex['lags'] = np.array([l*freq for l in ex['lags_i']], dtype=int)
    lags = ex['lags']
    
    ex['exp_pp'] = '{}_m{}-{}_dt{}'.format(RV_actor_names,
                        ex['sstartdate'].split('-')[0], 
                        ex['senddate'].split('-')[0], ex['tfreq'])

    ex['path_exp'] = os.path.join(base_path, exp_folder, ex['exp_pp'])
    if os.path.isdir(ex['path_exp']) == False : os.makedirs(ex['path_exp'])
    # =============================================================================
    # Preprocess data (this function uses cdo/nco and requires execution rights of
    # the created bash script)
    # =============================================================================
    # First time: Read Docstring by typing 'functions_pp.preprocessing_ncdf?' in console
    # Solve permission error by giving bash script execution right.

    functions_pp.perform_post_processing(ex)

    # *****************************************************************************
    # *****************************************************************************
    # Step 3 Settings for Response Variable (RV)
    # *****************************************************************************
    # *****************************************************************************
    class RV_seperateclass:
        def __init__(self):
            self.name = None
            self.RVfullts = None
            self.RVts = None

    RV = RV_seperateclass()
    # =============================================================================
    # 3.1 Selecting RV period (which period of the year you want to predict)
    # =============================================================================
    # If you don't have your own timeseries yet, then we assume you want to make
    # one using the first variable listed in ex['vars'].

    RV, ex = functions_pp.RV_spatial_temporal_mask(ex, RV, importRV_1dts)
    ex[ex['RV_name']] = RV



    print('\n\t**\n\tOkay, end of pre-processing climate data!\n\t**' )

    # *****************************************************************************
    # *****************************************************************************
    # Part 2 Configure RGCPD/Tigramite settings
    # *****************************************************************************
    # *****************************************************************************

    # =============================================================================
    # Corr maps settings
    # =============================================================================
    alpha = 0.01 # set significnace level for correlation maps
    FDR_control = True # Accounting for false discovery rate?
    kwrgs_corr = dict(alpha=alpha,
                      list_varclass=list_varclass,
                      lags=lags,
                      FDR_control=FDR_control)
    
    # =============================================================================
    # Tigramite settings
    # =============================================================================
    ex['tigr_tau_max'] = 5
    ex['max_comb_actors'] = 10
    ex['alpha_level_tig'] = 0.01 # Alpha level for final regression analysis by Tigrimate
    ex['pcA_sets'] = dict({   # dict of sets of pc_alpha values
          'pcA_set1a' : [ 0.05], # 0.05 0.01
          'pcA_set1b' : [ 0.01], # 0.05 0.01
          'pcA_set1c' : [ 0.1], # 0.05 0.01
          'pcA_set2'  : [ 0.2, 0.1, 0.05, 0.01, 0.001], # set2
          'pcA_set3'  : [ 0.1, 0.05, 0.01], # set3
          'pcA_set4'  : [ 0.5, 0.4, 0.3, 0.2, 0.1], # set4
          'pcA_none'  : None # default
          })
    ex['pcA_set'] = 'pcA_none' 
    # =============================================================================
    # settings precursor region selection
    # =============================================================================   
    distance_eps = 400 # proportional to km apart from a core sample, standard = 1000 km
    min_area_in_degrees2 = 3 # minimal size to become precursor region (core sample)
    group_split = 'together' # choose 'together' or 'seperate'
    kwrgs_cluster = dict(distance_eps=distance_eps,
                         min_area_in_degrees2=min_area_in_degrees2,
                         group_split='together')
    # =============================================================================
    # Train test split
    # =============================================================================
    ###options###
    # (1) random{int}   :   with the int(ex['method'][6:8]) determining the amount of folds
    # (2) ran_strat{int}:   random stratified folds, stratified based upon events, 
    #                       requires kwrgs_events.    
    # (3) leave{int}    :   chronologically split train and test years.
    # (4) split{int}    :   split dataset into single train and test set
    # (5) no_train_test_split
    
    # Extra: RV events settings are needed to make balanced traintest splits
    # =============================================================================
    method='ran_strat10'
    seed=30
    kwrgs_events={'event_percentile':'std', 
                  'min_dur': 1, 
                  'max_break': 0, 
                  'grouped': False}
    precursor_ts=ex['precursor_ts']
    
    
    
    kwrgs_RV = dict(method=method,
                    seed=seed,
                    kwrgs_events=kwrgs_events,
                    precursor_ts=precursor_ts)
    
    # =============================================================================
    # Load some standard settings
    # =============================================================================
    ex = wrapper_RGCPD_tig.standard_settings_and_tests(ex, kwrgs_RV, kwrgs_corr)
    central_lon_plots = 200
    map_proj = ccrs.LambertCylindrical(central_longitude=central_lon_plots)
    #%%
    # *****************************************************************************
    # *****************************************************************************
    # Part 3 Run RGCPD python script with settings
    # *****************************************************************************
    # *****************************************************************************
    
    RV, ex = functions_pp.RV_spatial_temporal_mask(ex, RV, importRV_1dts)
    # =============================================================================
    # Define RV and train-test split
    # =============================================================================
    RV, df_splits = wrapper_RGCPD_tig.RV_and_traintest(RV, ex, **kwrgs_RV)
    # =============================================================================
    # Find precursor fields (potential precursors)
    # =============================================================================
    
    outdic_actors = wrapper_RGCPD_tig.calculate_corr_maps(RV, df_splits, ex, **kwrgs_corr)
    #%% Change distance_eps if clustering is inappropriate (trial & error needed)
    outdic_actors = wrapper_RGCPD_tig.cluster_regions(outdic_actors, ex, plot=True, 
                                                      **kwrgs_cluster)
    
    #%%
    # calculate precursor timeseries
    outdic_actors = wrapper_RGCPD_tig.get_prec_ts(outdic_actors, ex)
    
    if ex['n_tot_regs'] != 0:
        
        # =============================================================================
        # Run tigramite to extract causal precursors
        # =============================================================================
        df_sum, df_data = wrapper_RGCPD_tig.run_PCMCI_CV(ex, outdic_actors, map_proj)
        
        # =============================================================================
        # Plot final results
        # =============================================================================
        #%%
        
        dict_ds = plot_maps.causal_reg_to_xarray(ex, df_sum, outdic_actors)
        
        wrapper_RGCPD_tig.store_ts(df_data, df_sum, dict_ds, outdic_actors, ex, add_spatcov=False)
        
        plot_maps.plot_labels_vars_splits(dict_ds, df_sum, map_proj, ex)
        plot_maps.plot_corr_vars_splits(dict_ds, df_sum, map_proj, ex)    

        print("--- {:.1f} hours ---".format((time.time() - start_time)/3600))
        #%%


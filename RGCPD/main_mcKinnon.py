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
if sys.version[:1] == '3':
    from importlib import reload as rel
import numpy as np
import pandas as pd
import functions_pp
import wrapper_RGCPD_tig
import plot_maps
import matplotlib.pyplot as plt
import xarray as xr
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
     'grid_res'     :       2.5,
     'startyear'    :       1979, # download startyear
     'endyear'      :       2018, # download endyear
     'input_freq'   :       'daily',
     'months'       :       list(range(1,12+1)), #downoad months
     # if dealing with daily data, give string as 'month-day', i.e. '07-01'
     # if dealing with monthly data, the day of month is neglected 
     'startperiod'  :       '06-22', # RV period
     'endperiod'    :       '08-24', # RV period
     'sstartdate'   :       '01-01', # precursor period
     'senddate'     :       '09-30', # precursor period
     'selbox'       :       {'la_min':20, # select domain in degrees east
                             'la_max':60,
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
ex['import_prec_ts'] = True


# Option 1111111111111111111111111111111111111111111111111111111111111111111111
# Download ncdf fields (in ex['vars']) through ECMWF MARS?
# 11111111111111111111111111111111111111111111111111111111111111111111111111111
# only analytical fields

# Info to download ncdf from ECMWF, atm only analytical fields (no forecasts)
# You need the ecmwf-api-client package for this option. See http://apps.ecmwf.int/datasets/.
if ECMWFdownload == True:
    if ex['input_freq'] == 'daily':
        # select hours you want to download from analysis
        ex['time']      =       pd.DatetimeIndex(start='00:00', end='23:00', 
                                freq=(pd.Timedelta(6, unit='h')))
        

#    ex['vars']      =       [['st1','st2'],['139.128', '170.128'],['sfc','sfc'],['0','0']]
#    ex['vars']      =       [ ['z_500hpa', 'sst', 't_850hpa'],['129.128', '34.128', '130.128'],
#                              ['pl', 'sfc', 'pl'],[['500'], '0', ['850']] ]
#    ex['vars']      =       [['t2mmax','sst'],['167.128','34.128'],['sfc','sfc'],['0','0']]
#    ex['vars']      =       [['sst'],
#                               ['sea_surface_temperature'],
#                               ['sfc'], [0]]
#    ex['vars']      =       [['sst', 'u500hpa'],
#                               ['sea_surface_temperature', 'u_component_of_wind'],
#                               ['sfc', 'pl'], [0,500]]
    ex['vars']      =       [['v200hpa'], ['v_component_of_wind'],['pl'], ['500']]
#    ex['vars']      =       [['t2mmax', 'sst', 'u', 't100'],
#                            ['167.128', '34.128', '131.128', '130.128'],
#                            ['sfc', 'sfc', 'pl', 'pl'],[0, 0, '500', '100']]
#    ex['vars']     =   [
#                        ['t2m', 'u'],              # ['name_RV','name_actor', ...]
#                        ['167.128', '131.128'],    # ECMWF param ids
#                        ['sfc', 'pl'],             # Levtypes
#                        [0, 200],                  # Vertical levels
#                        ]
else:
    ex['vars']      =       [[]]

# Option 2222222222222222222222222222222222222222222222222222222222222222222222
# Import ncdf lonlat fields to be precursors.
# 22222222222222222222222222222222222222222222222222222222222222222222222222222
# Must have same period, daily data and on same grid
if import_precursor_ncdf == True:
    # var names may not contain underscores
    ex['precursor_ncdf'] = [['name1', 'filename1'],['name2','filename2']]
    ex['precursor_ncdf'] = [['sm123', ('sm_123_{}-{}_1_12_daily_'
                              '0.25deg.nc'.format(ex['startyear'], ex['endyear'],
                               ex['grid_res']))]]
#    ex['precursor_ncdf'] = [['p_rm61', ('p_rm61_{}-{}_1_12_daily_'
#                              '2.5deg.nc'.format(ex['startyear'], ex['endyear'],
#                               ex['grid_res']))]]
#    ex['precursor_ncdf'] = [
#                            ['p_rm61', ('p_rm61_{}-{}_1_12_daily_'
#                              '2.5deg.nc'.format(ex['startyear'], ex['endyear'],
#                               ex['grid_res']))], 
#                            ['sm3', ('sm_3_{}-{}_1_12_daily_'
#                              '0.25deg.nc'.format(ex['startyear'], ex['endyear'],
#                               ex['grid_res']))]
#                            ]
#    ex['precursor_ncdf'] = [['sst', 'sst_NOAA_mcKbox_det_1982_2017_1_12_daily_0.25deg.nc']]
#    ex['precursor_ncdf'] = [['z_850hpa', 'z_850hpa_1979-2017_1_12_monthly_2.5deg.nc']]

else:
    ex['precursor_ncdf'] = [[]]

# Option 3333333333333333333333333333333333333333333333333333333333333333333333
# Import precursor timeseries (daily) 
# 33333333333333333333333333333333333333333333333333333333333333333333333333333
if ex['import_prec_ts'] == True:
    ex['precursor_ts'] = [['name1', 'filename1'],['name2','filename2']]
    ex['precursor_ts'] = [
                            ['sst_CPPA', ('/Users/semvijverberg/surfdrive/MckinRepl/',
                              'era5_T2mmax_sst_Northern/ran_strat10_s30/data/era5_19-09-19_12hr_lag_0.h5')]
                            ]

    
    
    
# Option 4444444444444444444444444444444444444444444444444444444444444444444444
# Import Response Variable 1-dimensional time serie.
# 44444444444444444444444444444444444444444444444444444444444444444444444444444
if import_RV_ncdf == True:
#    ex['RVnc_name'] =  ['t2mmax', ('t2mmax_{}-{}_1_12_{}_'
#                              '{}deg.nc'.format(ex['startyear'], ex['endyear'],
#                               ex['input_freq'], ex['grid_res']))]
    ex['RVnc_name'] =  ['t2mmax', ('t2mmax_{}-{}_1_12_daily_'
                              '0.75deg.nc'.format(ex['startyear'], ex['endyear']))]    
else:
    ex['RVnc_name'] = []


# Option 5555555555555555555555555555555555555555555555555555555555555555555555
# Import Response Variable 1-dimensional time serie.
# 55555555555555555555555555555555555555555555555555555555555555555555555555555
ex['excludeRV'] = 0 # if 0, then corr fields of RV_1dts calculated vs. RV netcdf
ex['importRV_1dts'] = importRV_1dts
if importRV_1dts == True:
    ex['RV_name'] = 't2mmax_E-US'
    ex['RV_detrend'] = False
#    ex['RVts_filename'] = 't2mmax_1979-2017_averAggljacc_tf14_n8__to_t2mmax_tf1.npy'
    ex['RVts_filename'] = 'era5_t2mmax_US_1979-2018_averAggljacc0.25d_tf1_n4__to_t2mmax_US_tf1_selclus4.npy'
#    ex['RVts_filename'] = 'comp_v_spclus2of4_tempclus2_AgglomerativeClustering_smooth15days_compmean_daily.npy'



    


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
    ex['spatial_mask_naming'] = 'averAggljacc_tf14_n8'
    ex['spatial_mask_file'] = os.path.join(ex['path_pp'], 'RVts2.5',
                          't2mmax_1979-2017_averAggljacc0.75d_tf1_n6__to_t2mmax_tf1.npy')
    # You can also include a latitude longitude box as a spatial mask by just 
    # giving a list [west_lon, east_lon, south_lat, north_lat] instead of a file
#    ex['spatial_mask_file'] = [18.25, 24.75, 75.25, 87.75]


# =============================================================================
# General Temporal Settings: frequency, lags, part of year investigated
# ===================================lag_steps==========================================
# Information needed to pre-process,
# Select temporal frequency:
ex['tfreqlist'] = [10] #[2,4,7,14,21,35] #[1,2,4,7,14,21,35]
for freq in ex['tfreqlist']:
    ex['tfreq'] = freq
    # choose lags to test
#    lag_min = int(np.timedelta64(5, 'D') / np.timedelta64(ex['tfreq'], 'D'))
    ex['lags_i'] = np.array([0], dtype=int)
    ex['lags'] = np.array([l*freq for l in ex['lags_i']], dtype=int)
    
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
    #%%
    # *****************************************************************************
    # *****************************************************************************
    # Part 2 Configure RGCPD/Tigramite settings
    # *****************************************************************************
    # *****************************************************************************
    ex['tigr_tau_max'] = 5
    ex['max_comb_actors'] = 10
    ex['alpha'] = 0.05# set significnace level for correlation maps
    ex['alpha_fdr'] = 2*ex['alpha'] # conservative significance level
    ex['FDR_control'] = True # Do you want to use the conservative alpha_fdr or normal alpha?
    ex['alpha_level_tig'] = 0.05 # Alpha level for final regression analysis by Tigrimate
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
    ex['distance_eps'] = 1000 # proportional to km apart from a core sample, standard = 1000 km
    ex['min_area_in_degrees2'] = 4 # minimal size to become precursor region (core sample)
    ex['group_split'] = 'together' # choose 'together' or 'seperate'
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
    
    ex['method'] = 'ran_strat10' ; ex['seed'] = 30 
#    ex['method'] = 'no_train_test_split'
    # =============================================================================
    # RV events settings (allows to make balanced traintest splits)
    # =============================================================================
    ex['kwrgs_events'] = {'event_percentile':'std', 
                          'min_dur': 1, 
                          'max_break': 0, 
                          'grouped': False}

    # =============================================================================
    # Load some standard settings
    # =============================================================================
    ex = wrapper_RGCPD_tig.standard_settings_and_tests(ex)
    central_lon_plots = 200
    map_proj = ccrs.LambertCylindrical(central_longitude=central_lon_plots)
    #%%
    # *****************************************************************************
    # *****************************************************************************
    # Part 3 Run RGCPD python script with settings
    # *****************************************************************************
    # *****************************************************************************
    # =============================================================================
    # Find precursor fields (potential precursors)
    # =============================================================================

    ex, outdic_actors = wrapper_RGCPD_tig.calculate_corr_maps(ex, map_proj)
    
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
        
        wrapper_RGCPD_tig.store_ts(df_data, df_sum, dict_ds, outdic_actors, ex, add_spatcov=True)
        
        plot_maps.plotting_per_variable(dict_ds, df_sum, map_proj, ex)
        

        print("--- {:.0} minutes ---".format((time.time() - start_time)/60))
        #%%


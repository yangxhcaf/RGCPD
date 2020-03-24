#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 16:20:31 2019

@author: semvijverberg
"""

import inspect, os, sys
if sys.platform == 'linux':
    import matplotlib as mpl
    mpl.use('Agg')
    n_cpu = 31
else:
    n_cpu = None
    

user_dir = os.path.expanduser('~')
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
RGCPD_dir = os.path.join(main_dir, 'RGCPD')
fc_dir = os.path.join(main_dir, 'forecasting')
df_ana_dir = os.path.join(main_dir, 'df_analysis/df_analysis/')
if main_dir not in sys.path or fc_dir not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(RGCPD_dir)
    sys.path.append(df_ana_dir)
    sys.path.append(fc_dir)

from itertools import product
import numpy as np
from class_fc import fcev
import valid_plots as dfplots


verbosity = 1

logit = ('logit', None)

logitCV = ('logitCV', 
          {'class_weight':{ 0:1, 1:1},
           'scoring':'brier_score_loss',
           'penalty':'l2',
           'solver':'lbfgs'})

#%%
## import original Response Variable timeseries:
#path_ts = '/Users/semvijverberg/surfdrive/MckinRepl/RVts'
#RVts_filename = 'era5_t2mmax_US_1979-2018_averAggljacc0.25d_tf1_n4__to_t2mmax_US_tf1_selclus4_okt19.npy'
#filename_ts = os.path.join(path_ts, RVts_filename)
#kwrgs_events_daily =    (filename_ts, 
#                         {  'event_percentile': 90,
#                        'min_dur' : 1,
#                        'max_break' : 0,
#                        'grouped' : False   }
#                         )
import time
start_time = time.time()
# ERA 5
path_data = user_dir + '/surfdrive/output_RGCPD/easternUS/ERA5_mx2t_sst_Northern/ff393_ran_strat10_s30/data/ERA5_21-03-20_12hr_lag_0_ff393.h5'
# EC-earth
# path_cluster = user_dir + '/surfdrive/output_RGCPD/easternUS_EC/958dd_ran_strat10_s30/tf1_n_clusters5_q95_dendo_958dd.nc'
# label = 1
# path_data = user_dir + '/surfdrive/output_RGCPD/easternUS_EC/958dd_ran_strat10_s30/data/EC_16-03-20_15hr_lag_0_958dd.h5'



start_end_TVdate = None
n_boot = 1
LAG_DAY = 21
add_autocorr = False

percentiles = [50, 66, 'std']
frequencies = np.arange(4, 32, 2)
frequencies = np.insert(frequencies, 0, 1)
# folds = np.arange(10)
folds = [[-6, -7, -8, -9]]
# percentiles = [66, 'std']
# frequencies = np.arange(10, 12, 2)
# folds = [[-8, -9]]


list_of_fc = [] ; times = []
dict_perc = {}; dict_folds = {}; dict_freqs = {}
f_prev, p_prev = folds[0], percentiles[0]
for perc, freq, fold in product(percentiles, frequencies, folds):        
    t0 = time.time()
    kwrgs_events = {'event_percentile': perc}
    fc = fcev(path_data=path_data, precur_aggr=freq, 
                        use_fold=fold, start_end_TVdate=None,
                        stat_model=logitCV, 
                        kwrgs_pp={'add_autocorr':False}, 
                        dataset=f'{freq}',
                        keys_d='CPPA',
                        n_cpu=n_cpu,
                        verbosity=verbosity)

    print(f'{fc.fold} {fc.test_years[0]} {perc}')
    # fc.load_TV_from_cluster(path_cluster=path_cluster, label=label, 
    #                         name_ds='q75tail')
    
    fc.get_TV(kwrgs_events=kwrgs_events)

    fc.fit_models(lead_max=np.array([LAG_DAY]))
 
    fc.perform_validation(n_boot=n_boot, blocksize='auto', 
                                  threshold_pred='upper_clim')
                                  
    list_of_fc.append(fc)
    
    dict_sum = fc.dict_sum
    
    # store data in 3 double dict
    dict_folds[str(fold)] = dict_sum
    if fold == folds[-1]:
        dict_freqs[str(freq)] = dict_folds
        # empty folds dict, those are now stored in dict_freq
        dict_folds = {} 
    if freq == frequencies[-1] and fold == folds[-1]:       
        dict_perc[str(perc)] = dict_freqs
        dict_freqs =  {}
    single_run_time = int(time.time()-t0)
    times.append(single_run_time)
    total_n_runs = len(percentiles) * len(frequencies) * len(folds)
    ETC = (int(np.mean(times) * total_n_runs))
    print(f'Time elapsed single run in {single_run_time} sec\t'
          f'ETC {int(ETC/60)} min \t Progress {int(100*(time.time()-t0)/ETC)}% ')
    

print('Total run time {:.1f} minutes'.format((time.time() - start_time)/60))


#%%

subfoldername='forecast_optimal_freq'
f_name = '{}_freqs{}-{}_perc{}-{}'.format(fc.hash, frequencies[0], frequencies[-1], 
                                          percentiles[0], percentiles[-1])
working_folder, filename = fc._print_sett(list_of_fc=list_of_fc, 
                                          subfoldername=subfoldername, f_name=f_name)





metric = 'BSS'
if type(kwrgs_events) is tuple:
    x_label = 'Temporal window [days]'
else:
    x_label = 'Temporal Aggregation [days]'

file_path = filename + '.h5'
path_data, dict_of_dfs = dfplots.get_score_matrix(d_expers=dict_perc, 
                                                  metric=metric, lags_t=LAG_DAY,
                                                  file_path=file_path)


fig = dfplots.plot_score_expers(path_data, 
                                x_label=x_label)
f_format = '.pdf'                      
fig.savefig(os.path.join(path_data.replace('.h5','') + f_format), 
            bbox_inches='tight') # dpi auto 600

fig = dfplots.plot_score_matrix(path_data, 
                                x_label=x_label, ax=None)
fig.savefig(os.path.join(path_data.replace('.h5','') +'_matrix' + f_format), 
            bbox_inches='tight') # dpi auto 600



    

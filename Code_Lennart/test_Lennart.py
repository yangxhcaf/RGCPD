#!/usr/bin/env python
# coding: utf-8

# get_ipython().run_line_magic('load_ext', 'autoreload')
# get_ipython().run_line_magic('autoreload', '2')

import os, inspect, sys

import matplotlib.pyplot as plt

if sys.platform == 'linux':
    import matplotlib as mpl
    mpl.use('Agg')
# user_dir = os.path.expanduser('~')
# user_dir = '/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD'

curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
RGCPD_func = os.path.join(main_dir, 'RGCPD')
cluster_func = os.path.join(main_dir, 'clustering/') 
if cluster_func not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(RGCPD_func)
    sys.path.append(cluster_func)
    
import numpy as np

import itertools
flatten = itertools.chain.from_iterable

# ## Initialize RGCPD class
# args:
# - list_of_name_path
# - start_end_TVdate
# 
#         list_of_name_path : list of name, path tuples. 
#         Convention: first entry should be (name, path) of target variable (TV).
#         list_of_name_path = [('TVname', 'TVpath'), ('prec_name1', 'prec_path1')]
#         
#         TV period : tuple of start- and enddate in format ('mm-dd', 'mm-dd')

import shutil

from RGCPD import RGCPD
from RGCPD import EOF
from class_BivariateMI_PCMCI import BivariateMI_PCMCI
from find_precursors import relabel

from class_BivariateMI_PCMCI import corr_map
from class_BivariateMI_PCMCI import entropy_map
from class_BivariateMI_PCMCI import entropy_map_pearson
# from class_BivariateMI_PCMCI import parcorr_map_spatial
from class_BivariateMI_PCMCI import parcorr_map_time
from class_BivariateMI_PCMCI import granger_map
from class_BivariateMI_PCMCI import gpdc_map
from class_BivariateMI_PCMCI import rcot_map
from class_BivariateMI_PCMCI import cmiknn_map
from df_ana import plot_ac, autocorr_sm

import creating_time_series as cts

if len(sys.argv) > 1:
    local_base_path = sys.argv[1]
else:
    print('Not cluster')
    local_base_path = "/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD" #/Code_Lennart/results
print(local_base_path)
local_script_dir = os.path.join(local_base_path, "ERA5" )
# sys.exit()

old_CPPA = [('sst_CPPA', local_script_dir + '/era5_24-09-19_07hr_lag_0.h5')]
CPPA_s30 = [('sst_CPPAs30', local_script_dir + '/era5_21-01-20_10hr_lag_10_Xzkup1.h5' )]
CPPA_s5  = [('sst_CPPAs5', local_script_dir + '/ERA5_15-02-20_15hr_lag_10_Xzkup1.h5')]


settings = {}
settings['N'] = 5
settings['nx'], settings['ny'], settings['T'] = 30, settings['N'] * 30, 5114
settings['spatial_covariance'] = 0.3
settings['random_modes'] = False
settings['noise_use_mean'] = True
settings['noise_level'] = 0
settings['transient'] = 200
settings['spatial_factor'] = 0.1

settings['user_dir'] = user_dir = '/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD'
settings['extra_dir'] = 'Code_Lennart'
settings['filename'] = 'multiple_test'

if len(sys.argv) > 1:
    settings['user_dir']  = sys.argv[1]
    user_dir = settings['user_dir']  + '/' + settings['extra_dir'] + '/results'
else:
    settings['user_dir'] = "/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD"
    user_dir = settings['user_dir']  + '/' + settings['extra_dir'] + '/results'
local_base_path = user_dir
print(f"DIR is: {user_dir}")



settings['random_causal_map'] = True
settings['area_size'] = None


## If any of the following settings is set to True, the results folder with {filename} will be removed!
## Also when 'plot_points' is not None
settings['netcdf4'] = True
settings['save_time_series'] = True
settings['do_pcmci'] = True
settings['save_matrices'] = True
settings['plot_points'] = 500
links_coeffs = 'model3'

settings['alpha'] = 0.01
settings['measure'] = 'average'
settings['val_measure'] = 'average'


test_splits = 5

# output = 'era5'
output =  'Xavier'
bivariate = corr_map
# bivariate = entropy_map
# bivariate = entropy_map_pearson
# bivariate = granger_map
# bivariate = parcorr_map_spatial
# bivariate = parcorr_map_time
# bivariate = gpdc_map
# bivariate = rcot_map
# bivariate = cmiknn_map


kwrgs_bivariate = {}
if bivariate == parcorr_map_time:
    lag = 5
    target = False
    precur = True
    kwrgs_bivariate = {'lag':lag, 'target':target, 'precur':precur}

if output == 'era5':
    list_of_name_path = [#('t2mmmax', local_script_dir + '/era5_t2mmax_US_1979-2018_averAggljacc0.25d_tf1_n4__to_t2mmax_US_tf1_selclus4_okt19_Xzkup1.npy'),
                            # ('sm1', local_script_dir + '/sm1_1979-2018_1_12_daily_1.0deg.nc'),
                            # ('sm2', local_script_dir + '/sm2_1979-2018_1_12_daily_1.0deg.nc')                     
                            # ('sm3', local_script_dir + '/sm3_1979-2018_1_12_daily_1.0deg.nc'),  
                            (1, '/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD/ERA5/clustered/output_RGCPD_dendo_20491.nc'),
                            ('st2', local_script_dir + '/st2_1979-2018_1_12_daily_1.0deg.nc')
                            # ('OLR', local_script_dir + '/OLRtrop_1979-2018_1_12_daily_2.5deg.nc')

    #                        ('u500', local_script_dir + '/u500hpa_1979-2018_1_12_daily_2.5deg.nc'),
    #                         ('v200', local_script_dir + '/input_raw/v200hpa_1979-2018_1_12_daily_2.5deg.nc'),
    #                         ('v500', local_script_dir + '/input_raw/v500hpa_1979-2018_1_12_daily_2.5deg.nc'),
    #                        ('sst', local_script_dir + '/sst_1979-2018_1_12_daily_1.0deg.nc'),
    #                        ('sm123', local_script_dir + '/sm_123_1979-2018_1_12_daily_1.0deg.nc')
    ]

    # list_for_EOFS = [EOF(name='st2', neofs=1, selbox=[-180, 360, -15, 30])]
    list_for_MI   = [BivariateMI_PCMCI(name='st2', func=bivariate, kwrgs_func={'alpha':.05, 'FDR_control':True}, distance_eps=100, min_area_in_degrees2=1, kwrgs_bivariate=kwrgs_bivariate)]

else:
    list_of_name_path = [#('test_target', local_base_path + '/Code_Lennart/NC/test.npy'),
                        (1, local_base_path + f'/{output}/NC/{output}_target.nc'),
                        ('test_precur', local_base_path + f'/{output}/NC/{output}.nc')
    ]

    # list_for_MI   = [BivariateMI_PCMCI(name='test_precur', func=bivariate, kwrgs_func={'alpha':.05, 'FDR_control':True})]
    list_for_MI   = [BivariateMI_PCMCI(name='test_precur', func=bivariate, kwrgs_func={'alpha':.05, 'FDR_control':False}, distance_eps=300, min_area_in_degrees2=3, kwrgs_bivariate=kwrgs_bivariate)]

# start_end_TVdate = ('06-24', '08-22')
# start_end_TVdate = None

# start_end_TVdate = ('3-13', '2-25')
start_end_TVdate = ('7-1', '12-31')
start_end_date = ('1-1', '12-31')
tfreq = 1
# start_end_date = None

RGCPD_path = local_base_path + f'/{output}/output_RGCPD/{bivariate.__name__}'
if bivariate.__name__ == 'parcorr_map_time':
    RGCPD_path = RGCPD_path + f'-{lag}-{target}-{precur}'
shutil.rmtree(RGCPD_path, ignore_errors=True)
os.makedirs(RGCPD_path)
rg = RGCPD(list_of_name_path=list_of_name_path, 
        #    list_for_EOFS=list_for_EOFS,
           list_for_MI=list_for_MI,
           start_end_TVdate=start_end_TVdate,
           start_end_date=start_end_date,
           tfreq=tfreq, lags_i=np.array([1]),
           path_outmain=RGCPD_path)

#selbox = [None, {'sst':[-180,360,-10,90]}]
selbox = None
#anomaly = [True, {'sm1':False, 'sm2':False, 'sm3':False}]
anomaly = [True, {'sm1':False, 'sm2':False, 'sm3':False, 'st2':False}]


rg.pp_precursors(selbox=selbox, anomaly=False, detrend=False)

rg.pp_TV()

#kwrgs_events={'event_percentile':66}
kwrgs_events=None
rg.traintest(method=f'random{test_splits}', kwrgs_events=kwrgs_events)

rg.calc_corr_maps()

rg.plot_maps_corr(save=True)

rg.cluster_list_MI()

# rg.df_data


def rename_labels(rg):
    all_locs = []
    for precur in rg.list_for_MI:
        prec_labels = precur.prec_labels.copy()
        # prec_labels = prec_labels.median(dim='split')
        if all(np.isnan(prec_labels.values.flatten()))==False:
            split_locs = []
            for split in range(len(prec_labels.values)): 
                labels = np.nan_to_num(prec_labels.values[split])[0]
                shape = labels.shape
                rows, columns = shape[0], shape[1]
                middle, offset = int(rows/2), int(rows/6)
                N_areas = int(columns / rows)
                locs = []
                reassign = {}
                for loc in range(N_areas):
                    area = labels[middle - offset: middle + offset, rows * loc + middle - offset: rows * loc + middle + offset]
                    area_nonzero = np.nonzero(area)
                    if len(area_nonzero[0]) > 0:
                        locs.append(loc+1)
                        value = area[area_nonzero[0][0]][area_nonzero[1][0]]
                        reassign[value] = loc+1
                locs = list(reassign.values())
                relabeld = relabel(precur.prec_labels.values[split], reassign).astype('float')
                relabeld[relabeld == 0] = np.nan
                precur.prec_labels.values[split] = relabeld
                split_locs.append(locs)
            all_locs.append(split_locs)
            # all_locs.append(list(set(flatten(split_locs))))
        else:
            pass
        
    return all_locs

def filter_matrices(matrices, locs, locs_intersect=None):
    if locs_intersect == None:
        locs_intersect = list(set.intersection(*map(set, locs)))
    else:
        locs_intersect = locs_intersect[1:]
    filtered_matrices = np.zeros((len(matrices), len(locs_intersect) + 1, len(locs_intersect) + 1, len(matrices[0][0][0])))
    for i, loc in enumerate(locs):
        indices = list(np.where(np.isin(loc, locs_intersect))[0])
        indices = [0] + [i+1 for i in indices]
        filtered_matrices[i] = matrices[i][indices][:, indices]
    return filtered_matrices, ([0] + locs_intersect)

locs = rename_labels(rg)

# rg.quick_view_labels()

rg.get_ts_prec(precur_aggr=None)

# keys = rg.df_data.columns[0]
rg.PCMCI_df_data(pc_alpha=None, 
                 tau_max=2,
                 max_combinations=2)

rg.PCMCI_get_links(alpha_level=0.1)

kwrgs = {'link_colorbar_label':'cross-MCI',
                     'node_colorbar_label':'auto-MCI',
                     'curved_radius':.4,
                     'arrowhead_size':4000,
                     'arrow_linewidth':50,
                     'label_fontsize':14,
                     'node_label_size':1}
# rg.PCMCI_plot_graph(s=1, variable='1ts', kwrgs=kwrgs)
# rg.PCMCI_plot_graph(s=2, kwrgs=kwrgs)



timeseries_RGCPD = rg.df_data.copy() 
timeseries_RGCPD = timeseries_RGCPD.loc[0]
timeseries_RGCPD = timeseries_RGCPD.values[:,:2]# time x number of timeseries

# fig, ax = plt.subplots(nrows=1, ncols=2, constrained_layout=True)
# ax[0] = plot_ac(y=rg.df_data['1ts'], ax=ax[0], title='Target')

# ax[1] = plot_ac(y=rg.df_data[f'{tfreq}..{locs[0][0][0]}..test_precur'], ax=ax[1], title='Precur')
# plt.show()



# rg.quick_view_labels()

rg.plot_maps_sum(cols=['corr'])

# parents = rg.parents_dict[0][0]
# parents = [i[0] for i in parents if i[1] == -1]



pcmci_matrix_path = local_base_path + f'/{output}' + f'/matrices/{bivariate.__name__}'
if bivariate.__name__ == 'parcorr_map_time':
    pcmci_matrix_path = pcmci_matrix_path + f'-{lag}-{target}-{precur}'
# settings = {'N': len(rg.pcmci_results_dict[0])}
if len(locs) == 0:
    locs = [[] for _ in range(test_splits)]
else:
    locs = list(np.array(locs)[0])#[most_common_p_matrix])  #[0]
p_matrices = np.array([rg.pcmci_results_dict[i]['p_matrix'] for i in rg.pcmci_results_dict])
area_lengths = [len(i) for i in p_matrices]
common_length = max(set(area_lengths), key = area_lengths.count)
p_matrices, locs_filtered = filter_matrices(p_matrices, locs)
val_matrices = np.array([rg.pcmci_results_dict[i]['val_matrix'] for i in rg.pcmci_results_dict])
val_matrices, locs = filter_matrices(val_matrices, locs, locs_intersect=locs_filtered)

p_matrix = np.mean(p_matrices, axis=0)
val_matrix = np.mean(val_matrices, axis=0)


# locs = list(set(flatten(locs)))
# locs = [0] + locs_filtered
print(f'\n\nFound regions {locs}')
# print(f'Found parents for split 0: {list(np.array(locs)[parents])}\n')
# print(common_length)
cts.save_matrices(settings, pcmci_matrix_path, p_matrix, val_matrix, iteratelist=locs)
np.save(pcmci_matrix_path + '/ZZZ_correlated', locs)

# pcmci_matrix_path = local_base_path + f'/{output}' + f'/matrices/AAA_real'
# np.save(pcmci_matrix_path + '/ZZZ_correlated', list(range(settings['N'] + 1)))

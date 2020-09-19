import os, inspect, sys, scipy

import argparse
parser = argparse.ArgumentParser()

if sys.platform == 'linux':
    import matplotlib as mpl
    mpl.use('Agg')

curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
RGCPD_func = os.path.join(main_dir, 'RGCPD')
cluster_func = os.path.join(main_dir, 'clustering/') 
# df_ana_func = os.path.join(main_dir, 'df_analysis/df_analysis') 
if cluster_func not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(RGCPD_func)
    sys.path.append(cluster_func)
    # sys.path.append(df_ana_func)

# df_ana_dir = os.path.join(curr_dir, '..', 'df_analysis/df_analysis/') # add df_ana path
# fc_dir       = os.path.join(curr_dir, '..', 'forecasting/') # add df_ana path
# sys.path.append(df_ana_dir) ; sys.path.append(fc_dir)
# df_ana_dir2 = os.path.join(curr_dir, '..', 'df_analysis/') # add df_ana path
# sys.path.append(df_ana_dir2)
df_ana_dir2 = os.path.join(curr_dir, 'df_analysis/') # add df_ana path
sys.path.append(df_ana_dir2)

import creating_time_series as cts
import causal_score

import shutil

# from RGCPD import RGCPD
from class_RGCPD import RGCPD
from find_precursors import relabel
from class_BivariateMI_PCMCI import BivariateMI_PCMCI

from class_BivariateMI_PCMCI import corr_map
from class_BivariateMI_PCMCI import entropy_map
# from class_BivariateMI_PCMCI import parcorr_map_spatial
from class_BivariateMI_PCMCI import parcorr_map_time
from class_BivariateMI_PCMCI import granger_map
from class_BivariateMI_PCMCI import gpdc_map
from class_BivariateMI_PCMCI import rcot_map
from class_BivariateMI_PCMCI import cmiknn_map
# from df_ana import plot_ac, autocorr_sm

import numpy as np
import pandas as pd
from datetime import date

import itertools
flatten = itertools.chain.from_iterable




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

     





def run_multiple(settings, years=None, modes=None, signals=None, noises=None, spatials=None, meandays=None, autocors=None, iterations=10, model='multiple', custom_noise=False, debug=False):
    # bivariate_list = [corr_map, entropy_map, granger_map, gpdc_map, cmiknn_map, granger_map]
    bivariate_list = [corr_map, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time] #, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time, parcorr_map_time
    bivariate_kwrgs_list = [(0,0,0), (5,False,True), (2,False,True), (1,False,True), (5,True,False), (2,True,False), (1,True,False)] #, (5,False,True), (2,False,True), (1,False,True), (5,True,False), (2,True,False), (1,True,False)
    bivariate_list = [corr_map, parcorr_map_time]
    bivariate_kwrgs_list = [(0,0,0), (5,False,True)]
    table_list = None
    test = None


    test_splits = 5

    signal_list = list(np.array(signals).flat)
    if signals == None:
        signal_list = np.arange(0,0.01, 0.01)#np.arange(0, 0.21, 0.01)
        if model == 'old':
            signal_list = np.arange(0,0.155,0.01)
        if model == 'some':
            signal_list = np.arange(0,0.01, 0.01)#np.arange(0, 0.155, 0.01)
        table_list = signal_list
        test = 'sign'
    print(f"\nTested signal strengths: {signal_list}")
    
    

    modes_list = list(np.array(modes).flat)
    if modes == None:
        modes_list = np.arange(4,13,1)
        table_list = modes_list
        test = 'mode'
    print(f"\nTested number of modes: {modes_list}")


    year_list = list(np.array(years).flat)
    if years == None:
        year_list = np.arange(5, 15, 1)
        table_list = year_list
        test = 'time'
    day1 = date(1979, 1, 1) #YYYY-MM-DD
    length_list = [(date(1979 + i, 1, 1) - day1).days for i in year_list]
    print(f"\nTested time series lengths: {length_list}, which is in years: {year_list}\n")

    noises_list = list(np.array(noises).flat)
    if noises == None:
        noises_list = np.arange(0,30.5,1)
        if debug:
            noises_list = np.arange(10,21,10)
        table_list = noises_list
        test = 'nois'
    if custom_noise:
        print('Testing with custom noise')
        test = 'cnoi' 
    print(f"\nTested number of noise levels: {noises_list}")

    spatial_list = list(np.array(spatials).flat)
    if spatials == None:
        spatial_list = list(np.arange(200,4100,100)) #152
        # spatial_list = np.array([1] + spatial_list)
        table_list = spatial_list
        test = 'spat'
    print(f"\nTested number of spatial covariance levels: {spatial_list}")

    meanday_list = list(np.array(meandays).flat)
    if meandays == None:
        meanday_list = list(np.arange(1,35.5,1)) #152
        # meanday_list = [1,10]
        # spatial_list = np.array([1] + spatial_list)
        table_list = meanday_list
        test = 'mday'
    print(f"\nTested days mean: {meanday_list}")

    autocor_list = list(np.array(autocors).flat)
    if autocors == None:
        autocor_list = list(np.arange(0.8,0.995,0.01)) #152
        # autocor_list = [0.8, 0.99]
        # spatial_list = np.array([1] + spatial_list)
        table_list = autocor_list
        test = 'acor'
    print(f"\nTested autocorrelation strengths: {autocor_list}")

    corr_ts_list = np.zeros((iterations, len(table_list)))
    corr_pc_list = np.zeros((iterations, len(table_list)))


    


    # pcmci_df = pd.DataFrame(columns=modes_list)
    # bivariate_df = pd.DataFrame(columns=modes_list)
    # pcmci_df = np.zeros((iterations, len(modes_list)))
    # bivariate_df = np.zeros((iterations, len(modes_list)))

    # for biv_i, bivariate in enumerate(bivariate_list):
    pcmci_df = np.zeros((iterations, len(table_list)))
    print(table_list)
    bivariate_df = np.zeros((len(bivariate_list), iterations, len(table_list)))
    # print(bivariate_df)
    for signal_i, signal in enumerate(signal_list):
        for year_i, time in enumerate(length_list):
            for mode_i, N in enumerate(modes_list):
                for spatial_i, spatial in enumerate(spatial_list):
                    for noise_i, noise in enumerate(noises_list):
                        for meanday_i, meanday in enumerate(meanday_list):
                            for autocor_i, autocor in enumerate(autocor_list):
                                if signals == None:
                                    table_i = signal_i
                                elif modes == None:
                                    table_i = mode_i
                                elif years == None:
                                    table_i = year_i
                                elif noises == None:
                                    table_i = noise_i
                                elif spatials == None:
                                    table_i = spatial_i
                                elif meandays == None:
                                    table_i = meanday_i
                                elif autocors == None:
                                    table_i = autocor_i
                                
                                for iteration in range(iterations):
                                    settings['N'] = N
                                    settings['ny'] = N * 30
                                    settings['autocor'] = autocor
                                    settings['autocor_target'] = 0.6
                                    settings['timefreq'] = int(meanday)
                                    print(f'Iteration {iteration + 1}/{iterations}')
                                    print('')
                                    print(f"Modes: {N}")
                                    print(f"Years = {year_list[year_i]}")
                                    print(f"Signal = {signal}")
                                    if custom_noise:
                                        print(f'Custom noise = {noise}')
                                        settings['noise_level'] = 0 #0.5
                                        settings['custom_noise_level'] = noise #0.5
                                    else:
                                        print(f"Noise = {noise}")
                                        settings['noise_level'] = noise #0.5
                                        settings['custom_noise_level'] = 0
                                    print(f"Spatial covariance = {spatial}")
                                    print(f"Model = {model}")
                                    print(f'Autocorrelatie = {autocor}')
                                    print(f'{meanday} day mean is used')
                                    settings['model'] = model
                                    
                                    settings['spatial_covariance'] = spatial
                                    settings['signal'] = signal
                                    settings['T'] = time
                                    real_data = cts.create_time_series(settings, links_coeffs, verbose=False,
                                                                            plot_modes=False,
                                                                            plot_timeseries=False,
                                                                            draw_network=False,
                                                                            custom_noise=custom_noise,
                                                                            cluster=True)
                                    real_data = real_data[:,:2]

                                    print("Finished generating!")
                                    local_base_path = user_dir
                                    local_script_dir = os.path.join(local_base_path, "ERA5" )
                                    
                                    output = settings['filename']

                                    # bivariate = corr_map
                                    for biv_i, bivariate in enumerate(bivariate_list):
                                        print(bivariate.__name__)
                                        list_of_name_path = [#('test_target', local_base_path + '/Code_Lennart/NC/test.npy'),
                                                            (1, local_base_path + f'/{output}/NC/{output}_target.nc'),
                                                            ('test_precur', local_base_path + f'/{output}/NC/{output}.nc')
                                        ]

                                        kwrgs_bivariate = {}
                                        if bivariate == parcorr_map_time:
                                            lag = bivariate_kwrgs_list[biv_i][0]
                                            target = bivariate_kwrgs_list[biv_i][1]
                                            precur = bivariate_kwrgs_list[biv_i][2]
                                            kwrgs_bivariate = {'lag':lag, 'target':target, 'precur':precur}

                                        print(kwrgs_bivariate)

                                        list_for_MI   = [BivariateMI_PCMCI(name='test_precur', func=bivariate, kwrgs_func={'alpha':.05, 'FDR_control':False}, distance_eps=200, min_area_in_degrees2=3, kwrgs_bivariate=kwrgs_bivariate)]

                                        start_end_TVdate = ('7-1', '12-31')
                                        start_end_date = ('1-1', '12-31')
                                        # start_end_TVdate = None
                                        # start_end_date = None

                                        RGCPD_path = local_base_path + f'/{output}/output_RGCPD/{bivariate.__name__}'
                                        shutil.rmtree(RGCPD_path, ignore_errors=True)
                                        os.makedirs(RGCPD_path)
                                        print(RGCPD_path)
                                        rg = RGCPD(list_of_name_path=list_of_name_path, 
                                                #    list_for_EOFS=list_for_EOFS,
                                                list_for_MI=list_for_MI,
                                                start_end_TVdate=start_end_TVdate,
                                                start_end_date=start_end_date,
                                                tfreq=settings['timefreq'], lags_i=np.array([1]),
                                                verbosity=0,
                                                path_outmain=RGCPD_path)

                                        selbox = None

                                        anomaly = [True, {'sm1':False, 'sm2':False, 'sm3':False, 'st2':False}]

                                        rg.pp_precursors(selbox=selbox, anomaly=False, detrend=False)

                                        rg.pp_TV()

                                        #kwrgs_events={'event_percentile':66}
                                        kwrgs_events=None
                                        rg.traintest(method=f'random{test_splits}', kwrgs_events=kwrgs_events)

                                        rg.calc_corr_maps()

                                        # rg.plot_maps_corr(save=True)

                                        rg.cluster_list_MI()

                                        # rg.quick_view_labels()

                                        try:
                                            locs = rename_labels(rg)

                                            rg.get_ts_prec(precur_aggr=None)
                                        except:
                                            # iteration -= 1
                                            print("PASSED BECAUSE NO AREAS FOUND")
                                            continue


                                        rg.PCMCI_df_data(pc_alpha=0.01, 
                                                        tau_max=2,
                                                        max_combinations=2)

                                        rg.PCMCI_get_links(alpha_level=0.01)

                                        # rg.PCMCI_plot_graph(s=1)

                                        # rg.quick_view_labels()

                                        # rg.plot_maps_sum()

                                        # p_matrices = np.array([rg.pcmci_results_dict[i]['p_matrix'] for i in rg.pcmci_results_dict])
                                        # area_lengths = [len(i) for i in p_matrices]
                                        # common_length = max(set(area_lengths), key = area_lengths.count)
                                        # most_common_p_matrix = np.where(np.array(area_lengths) == common_length)
                                        # p_matrices = p_matrices[most_common_p_matrix]
                                        # p_matrix = np.mean(p_matrices, axis=0)
                                        # # p_matrix = p_matrix.mean(0)
                                        # val_matrix = np.array([rg.pcmci_results_dict[i]['val_matrix'] for i in rg.pcmci_results_dict])[most_common_p_matrix]
                                        # val_matrix = np.mean(val_matrix, axis=0)

                                        # parents = rg.parents_dict[0][0]
                                        # parents = [i[0] for i in parents if i[1] == -1]

                                        if bivariate == corr_map:
                                            timeseries_RGCPD = rg.df_data.copy() 
                                            timeseries_RGCPD = timeseries_RGCPD.loc[0]
                                            timeseries_RGCPD = timeseries_RGCPD.values[:,:2]# time x number of timeseries
                                            corr_ts, _ = scipy.stats.pearsonr(real_data[:,0],timeseries_RGCPD[:,0])
                                            corr_pc, _ = scipy.stats.pearsonr(real_data[:,1],timeseries_RGCPD[:,1])
                                            print(f'\n\nCorr ts: {corr_ts},   corr precur: {corr_pc}')
                                            corr_ts_list[iteration][table_i] = corr_ts
                                            corr_pc_list[iteration][table_i] = corr_pc




                                        pcmci_matrix_path = local_base_path + f'/{output}' + f'/matrices/{bivariate.__name__}'
                                        # print(f"Matrix {bivariate.__name__} path: {pcmci_matrix_path}")
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
                                        print(f'\n\nFound regions {locs}\n')
                                        # print(f'Found parents for split 0: {list(np.array(locs)[parents])}\n')
                                        # print(common_length)
                                        if len(locs) > common_length:
                                            # iteration -= 1
                                            print("PASSED BECAUSE OF UNEQUAL FOUND AREAS")
                                            continue
                                        cts.save_matrices(settings, pcmci_matrix_path, p_matrix, val_matrix, iteratelist=locs)
                                        np.save(pcmci_matrix_path + '/ZZZ_correlated', locs)

                                    score = causal_score.calculate_causal_score(settings, val=False, verbose=False, locs=locs, target_only=True, no_ac=False)
                                    # print(score)

                                    
                                    print(f'Table_i: {table_i}')
                                    # path = local_base_path + f'/{output}/scores'
                                    # if os.path.isdir(path) != True : os.makedirs(path)
                                    test_list = [bivariate.__name__ for bivariate in bivariate_list]
                                    for i, key in enumerate(score.columns):
                                        key = key.split(' ', 1)[0]
                                        if key[:7] == 'parcorr':
                                            key2, lag, target, precur = key.split('-')
                                            target = (target == 'True')
                                            precur = (precur == 'True')
                                            key = key2
                                        if key == 'pcmci_test':
                                            # pcmci_df = pcmci_df.append({N: score.values[0][i]}, ignore_index=True)
                                            pcmci_df[iteration][table_i] = score.values[0][i]
                                            print("PCMCI score:")
                                            print(score.values[0][i])
                                        elif key in test_list:
                                            test_list_index = test_list.index(key)
                                            if key[:7] == 'parcorr':
                                                test_list_index = bivariate_kwrgs_list.index((int(lag),target,precur))
                                            # bivariate_df = bivariate_df.append({N: score.values[0][i]}, ignore_index=True)
                                            bivariate_df[test_list_index][iteration][table_i] = score.values[0][i]
                                            if key[:7] == 'parcorr':
                                                print(f'Score {key}, lag {lag}, target {target}, precur {precur}:')
                                            else:
                                                print(f'Score {key}:')
                                            print(score.values[0][i])
    path = local_base_path + f'/scores/{output}'
    if os.path.isdir(path) != True : os.makedirs(path)
    for biv_i, df in enumerate(bivariate_df):
        print(df)
        bivariate_df = pd.DataFrame(df, columns=table_list)
        path2 = path + f'/{test}_{bivariate_list[biv_i].__name__}'
        if bivariate_list[biv_i].__name__ == 'parcorr_map_time':
            kwrgs = bivariate_kwrgs_list[biv_i]
            path2 = path2 + f'-{kwrgs[0]}-{kwrgs[1]}-{kwrgs[2]}'
        bivariate_df.to_csv(path2 + '.csv', index=False)
    print("------------------------------------")
    print(pcmci_df)
    pcmci_df = pd.DataFrame(pcmci_df, columns=table_list)
    pcmci_df.to_csv(path + f'/{test}_pcmci.csv', index=False)
    corr_ts_df = pd.DataFrame(corr_ts_list, columns=table_list)
    corr_ts_df.to_csv(path + f'/{test}_pcaaa_corr_ts.csv', index=False)
    corr_pc_df = pd.DataFrame(corr_pc_list, columns=table_list)
    corr_pc_df.to_csv(path + f'/{test}_pcaaa_corr_pc.csv', index=False)
    

    return





settings = {}
settings['N'] = 5
settings['nx'], settings['ny'], settings['T'] = 30, settings['N'] * 30, 5114
settings['spatial_covariance'] = 0.3
settings['random_modes'] = False
settings['noise_use_mean'] = False
settings['noise_level'] = 0
settings['transient'] = 200
settings['spatial_factor'] = 0.1

settings['user_dir'] = user_dir = '/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD'
settings['extra_dir'] = 'Code_Lennart'
settings['filename'] = 'multiple_test'

parser.add_argument("-dir", "--user_dir", help="User dir")
parser.add_argument("-test", "--testtt", help="Test to perform, can be ['signals', 'modes', 'years', 'spatial_one', 'spatial_mult','noise_one', 'noise_mult', 'meanday', 'autocor']")

args = parser.parse_args()

if len(sys.argv) > 1:
    settings['user_dir']  = args.user_dir
    user_dir = settings['user_dir']  + '/' + settings['extra_dir'] + '/results'
    testtt = args.testtt
    print(testtt)
else:
    print('No args parsed')
    settings['user_dir'] = "/mnt/c/Users/lenna/Documents/Studie/2019-2020/Scriptie/RGCPD"
    user_dir = settings['user_dir']  + '/' + settings['extra_dir'] + '/results'
    testtt = 'debug' 
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

if testtt == 'signals':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=None, noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=100, model='one')
elif testtt == 'signals_old':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=None, noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=30, model='old')
elif testtt == 'signals_some':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[8], signals=None, noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=30, model='some')
elif testtt == 'modes':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=None, signals=[0.12], noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=30, model='multiple')
elif testtt == 'years':
    print(f'Testing {testtt}')
    run_multiple(settings, years=None, modes=[7], signals=[0.12], noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=30, model='multiple')
elif testtt == 'spatial_one':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.09], noises=[10], spatials=None, meandays=[1], autocors=[0.96], iterations=100, model='one')
elif testtt == 'noise_one':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.09], noises=None, spatials=[1000], meandays=[1], autocors=[0.96], iterations=100, model='one')
elif testtt == 'noise_custom':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.09], noises=None, spatials=[1000], meandays=[1], autocors=[0.96], iterations=100, model='one', custom_noise=True)
elif testtt == 'spatial_mult':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.12], noises=[10], spatials=None, meandays=[1], autocors=[0.96], iterations=30, model='multiple')
elif testtt == 'noise_mult':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.12], noises=None, spatials=[1000], meandays=[1], autocors=[0.96], iterations=30, model='multiple')
elif testtt == 'meanday':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.18], noises=[10], spatials=[1000], meandays=None, autocors=[0.96], iterations=100, model='one')
elif testtt == 'autocor':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=[0.12], noises=[10], spatials=[1000], meandays=[1], autocors=None, iterations=30, model='multiple')
elif testtt == 'debug':
    print(f'Testing {testtt}')
    run_multiple(settings, years=[8], modes=[7], signals=None, noises=[10], spatials=[1000], meandays=[1], autocors=[0.96], iterations=1, model='one', debug=True)



# plt.imshow(xrvals.values[i][0])
#                 plt.show()
#                 f_name = 'corr_map_{}_test_{}'.format(precur_name, i)

#                 fig_path = os.path.join(self.path_outsub1, f_name)+self.figext
#                 plt.savefig(fig_path, bbox_inches='tight')
import os, sys, inspect, warnings
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
sub_dir = os.path.join(main_dir, 'RGCPD/')
if main_dir not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(sub_dir)
import numpy as np 
import statsmodels.api as sm 
from statsmodels.tsa.api import VAR
import matplotlib.pyplot as plt 
plt.style.use('seaborn')
import pandas as pd 
import pywt as wv
from pprint import pprint as pp 
import synthetic_data as sd 
import wave_ana as wa 
from RGCPD import RGCPD
from RGCPD import BivariateMI
import wave_ana as wa 
import multiprocessing as mp
import investigate_ts as inv
# TODO INVESTIGATE MORE ON WAVELET VARIANCE
prec_paths= [' ', 'z500hpa_1979-2018_1_12_daily_2.5deg.nc','sm2_1979-2018_1_12_daily_1.0deg.nc' ]

rg = inv.generate_rgcpd_default(doc=prec_paths[0])
rg_obj_aggr =  inv.generate_rgcpd_object_prec_aggr(rg=rg, precur_aggr=1)
rg_data, rg_index , wave, mode = inv.generate_rgcpd_data(rg_obj_aggr=rg_obj_aggr)

#    target = 
# p = mp.Pool(mp.cpu_count()-1)
# answer  = p.starmap_async(extract_ar_data,zip([rg_data_, rg_data_],[target_, precursor]))
# result_3ts, result_prec1 =  answer.get()
# p.close()
# p.join()
# const_ts, ar_ts = result_3ts
# const_p1, ar_p1 = result_prec1

cols =  rg_data.columns.tolist()

gammas = np.arange(0, 1, 0.1)
nus = np.arange(0, 1, 0.1)
thetas = np.arange(0, 1 , 0.1)
# for gamma in gammas:
for col in cols[1:]:
    for nu in nus:
        ar_ts, const_ts = inv.extract_ar_data(rg_data, cols[0])
        ar, const = inv.extract_ar_data(rg_data, col) 


        # poly_prec = inv.polynomial_fit(ar=ar, rg_data=rg_data, col=cols[i], sigma=np.std(rg_data[cols[i]].values), const=const, dependance=False)
        poly_prec = inv.polynomial_fit_turbulance(ar=ar, col=col,  sigma=np.std(rg_data[col].values), rg_data=rg_data, const=const, theta=1, nu=nu)
        poly_ts = inv.polynomial_fit(ar=ar_ts, rg_data=rg_data, col=cols[0], sigma=np.std(rg_data[cols[0]].values), const=const_ts, dependance=False)

        poly_dep = inv.polynomial_fit(ar=ar_ts, rg_data=rg_data, col=cols[0], sigma=np.std(rg_data[cols[0]].values), const=const_ts, gamma=0.1, dependance=True, x1=poly_prec)

        result_var_target = inv.wavelet_variance_levels(data=rg_data, col=cols[0], wavelet=wave, mode=mode, levels=6)
        result_var_prec = inv.wavelet_variance_levels(data=rg_data, col=col, wavelet=wave, mode=mode,  levels=6)

        prec_cA = inv.create_wavelet_details(poly_prec, index_poly=rg_index, level=6, wave=wave, mode=mode , debug=True)
        target_cA = inv.create_wavelet_details(poly_dep, index_poly=rg_index, level=6, wave=wave, mode=mode , debug=True)
        target_prec_lag  = inv.get_mci_coeffs_lag(details_prec=prec_cA, details_target=target_cA, index=rg_index, rg_obj=rg_obj_aggr, debug=False)

        inv.plot_mci_prediction(detail_prec=prec_cA, prec_lag=target_prec_lag, title=f'Dependance with {str(np.round(nu, 2))} variation on prec', savefig=True)
        inv.plot_wavelet_variance(var_result=result_var_target, title=cols[0], savefig=True)
        inv.plot_wavelet_variance(var_result=result_var_prec, title=col, savefig=True)
        inv.display_polynome(poly=poly_dep, ar_list=[ar_ts[0], ar_ts[1], 0.1], rg_data=rg_data, col=cols[0], title=f'AR fit dependance {0.1} gamma', save_fig=True, dependance=True)
        inv.display_polynome(poly=poly_ts, ar_list=ar_ts, rg_data=rg_data, col=cols[0], title=f'AR fit on {cols[0]} target', save_fig=True, dependance=False)
        inv.display_polynome(poly=poly_prec, ar_list=ar, rg_data=rg_data, col=col, title=f'AR fit on {col} precursor with {str(nu)} variation', save_fig=True, dependance=False)
        plt.show()
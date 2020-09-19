#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec  5 12:17:25 2019

@author: semvijverberg
"""

import itertools
import numpy as np
import xarray as xr
#import datetime
import scipy
import pandas as pd
from statsmodels.sandbox.stats import multicomp
import functions_pp
import find_precursors
from typing import Union
flatten = lambda l: list(itertools.chain.from_iterable(l))

# from pyinform import transfer_entropy
from math import log, e
from scipy import stats
import sys
import matplotlib.pyplot as plt

import csv
import os

from tigramite.independence_tests import ParCorr
from tigramite.independence_tests import GPDC
from tigramite.independence_tests import RCOT
from tigramite.independence_tests import CMIknn
from statsmodels.tsa.stattools import grangercausalitytests

class BivariateMI_PCMCI:

    def __init__(self, name, func=None, kwrgs_func={}, kwrgs_bivariate={}, lags=np.array([1]), 
                 distance_eps=400, min_area_in_degrees2=3, group_split='together', 
                 calc_ts='region mean', selbox: tuple=None,
                 use_sign_pattern: bool=False, use_coef_wghts: bool=False, verbosity=1):
        '''

        Parameters
        ----------
        name : str
            Name that links to a filepath pointing to a Netcdf4 file.
        func : function to apply to calculate the bivariate 
            Mutual Informaiton (MI), optional
            The default is applying a correlation map.
        kwrgs_func : TYPE, optional
            DESCRIPTION. The default is {}.
        lags : int, optional
            lag w.r.t. the the target variable at which to calculate the MI. 
            The default is np.array([1]).
        distance_eps : int, optional
            The maximum distance between two gridcells for one to be considered 
            as in the neighborhood of the other, only gridcells with the same 
            sign are grouped together.
            The default is 400.
        min_area_in_degrees2 : TYPE, optional
            The number of samples gridcells in a neighborhood for a 
            region to be considered as a core point. The parameter is 
            propotional to the average size of 1 by 1 degree gridcell.
            The default is 3.
        group_split : str, optional
            Choose 'together' or 'seperate'. If 'together', then region labels
            will be equal between different train test splits.
            The default is 'together'.
        calc_ts : str, optional
            Choose 'region mean' or 'pattern cov'. If 'region mean', a 
            timeseries is calculated for each label. If 'pattern cov', the 
            spatial covariance of the whole pattern is calculated. 
            The default is 'region_mean'.
        selbox : tuple, optional
            has format of (lon_min, lon_max, lat_min, lat_max)
        use_sign_pattern : bool, optional
            When calculating spatial covariance, do not use original pattern
            but focus on the sign of each region. Used for quantifying Rossby
            waves.
        use_coef_wghts : bool, optional
            When True, using (corr) coefficient values as weights when calculating
            spatial mean. (will always be area weighted).
        verbosity : int, optional
            Not used atm. The default is 1.

        Returns
        -------
        Initialization of the BivariateMI class

        '''
        self.name = name
        if func is None:
            self.bivariate_func = corr_new
            
        else:
            self.bivariate_func = func
        if kwrgs_func is None:
            self.kwrgs_func = {'alpha':.05, 'FDR_control':True}
        else:
            self.kwrgs_func = kwrgs_func
        
        if (kwrgs_bivariate == {}) and (self.bivariate_func.__name__ == 'parcorr_map_time'):
            self.kwrgs_bivariate = {'lag':1, 'target':False, 'precur':True}
        else:
            self.kwrgs_bivariate = kwrgs_bivariate

        #get_prec_ts & spatial_mean_regions
        self.calc_ts = calc_ts
        self.selbox = selbox
        self.use_sign_pattern = use_sign_pattern
        self.use_coef_wghts = use_coef_wghts
        # cluster_DBSCAN_regions
        self.distance_eps = distance_eps
        self.min_area_in_degrees2 = min_area_in_degrees2
        self.group_split = group_split
        
        self.verbosity = verbosity

        return
    

    def bivariateMI_map(self, precur_arr, df_splits, RV): #, lags=np.array([0]), alpha=0.05, FDR_control=True #TODO
        #%%
        #    v = ncdf ; V = array ; RV.RV_ts = ts of RV, time_range_all = index range of whole ts
        """
        This function calculates the correlation maps for precur_arr for different lags.
        Field significance is applied to test for correltion.
        This function uses the following variables (in the ex dictionary)
        prec_arr: array
        time_range_all: a list containing the start and the end index, e.g. [0, time_cycle*n_years]
        lag_steps: number of lags
        time_cycle: time cycyle of dataset, =12 for monthly data...
        RV_period: indices that matches the response variable time series
        alpha: significance level
        
        A land sea mask is assumed from settin all the nan value to True (masked).
        For xrcorr['mask'], all gridcell which are significant are not masked,
        i.e. bool == False
        """

        n_lags = len(self.lags)
        lags = self.lags
        assert n_lags >= 0, ('Maximum lag is larger then minimum lag, not allowed')

        self.df_splits = df_splits # add df_splits to self
        n_spl = df_splits.index.levels[0].size
        # make new xarray to store results
        xrcorr = precur_arr.isel(time=0).drop('time').copy()
        orig_mask = np.isnan(precur_arr[0])
        # add lags
        list_xr = [xrcorr.expand_dims('lag', axis=0) for i in range(n_lags)]
        xrcorr = xr.concat(list_xr, dim = 'lag')
        xrcorr['lag'] = ('lag', lags)
        # add train test split
        list_xr = [xrcorr.expand_dims('split', axis=0) for i in range(n_spl)]
        xrcorr = xr.concat(list_xr, dim = 'split')
        xrcorr['split'] = ('split', range(n_spl))

        print('\n{} - calculating correlation maps'.format(precur_arr.name))
        np_data = np.zeros_like(xrcorr.values)
        np_mask = np.zeros_like(xrcorr.values)
        def corr_single_split(RV_ts, precur_train, alpha, FDR_control): #, lags, alpha, FDR_control

            lat = precur_train.latitude.values
            lon = precur_train.longitude.values

            z = np.zeros((lat.size*lon.size,len(lags) ) )
            Corr_Coeff = np.ma.array(z, mask=z)


            dates_RV = RV_ts.index
            for i, lag in enumerate(lags):

                dates_lag = functions_pp.func_dates_min_lag(dates_RV, lag)[1]
                prec_lag = precur_train.sel(time=dates_lag)
                prec_lag = np.reshape(prec_lag.values, (prec_lag.shape[0],-1))


                # correlation map and pvalue at each grid-point:
                corr_val, pval = self.bivariate_func(prec_lag, RV_ts.values.squeeze(), **self.kwrgs_bivariate)
                mask = np.ones(corr_val.size, dtype=bool)
                if FDR_control == True:
                    # test for Field significance and mask unsignificant values
                    # FDR control:
                    adjusted_pvalues = multicomp.multipletests(pval, method='fdr_bh')
                    ad_p = adjusted_pvalues[1]

                    mask[ad_p <= alpha] = False

                else:
                    mask[pval <= alpha] = False


                Corr_Coeff[:,i] = corr_val[:]
                Corr_Coeff[:,i].mask = mask
                
            Corr_Coeff = np.ma.array(data = Corr_Coeff[:,:], mask = Corr_Coeff.mask[:,:])
            Corr_Coeff = Corr_Coeff.reshape(lat.size,lon.size,len(lags)).swapaxes(2,1).swapaxes(1,0)
            return Corr_Coeff

        RV_mask = df_splits.loc[0]['RV_mask']
        for s in xrcorr.split.values:
            progress = int(100 * (s+1) / n_spl)
            # =============================================================================
            # Split train test methods ['random'k'fold', 'leave_'k'_out', ', 'no_train_test_split']
            # =============================================================================
            RV_train_mask = np.logical_and(RV_mask, df_splits.loc[s]['TrainIsTrue'])
            RV_ts = RV.fullts[RV_train_mask.values]
            precur_train = precur_arr[df_splits.loc[s]['TrainIsTrue'].values]

        #        dates_RV  = pd.to_datetime(RV_ts.time.values)
            dates_RV = RV_ts.index
            n = dates_RV.size ; r = int(100*n/RV.dates_RV.size )
            print(f"\rProgress traintest set {progress}%, trainsize=({n}dp, {r}%)", end="")
            # if s == 6:
                # break
            ma_data = corr_single_split(RV_ts, precur_train, **self.kwrgs_func)
            np_data[s] = ma_data.data
            np_mask[s] = ma_data.mask
        print("\n")
        xrcorr.values = np_data
        mask = (('split', 'lag', 'latitude', 'longitude'), np_mask )
        xrcorr.coords['mask'] = mask
        # fill nans with mask = True
        xrcorr['mask'] = xrcorr['mask'].where(orig_mask==False, other=orig_mask) 
        #%%
        return xrcorr
  
    
    def get_prec_ts(self, precur_aggr=None, kwrgs_load=None): #, outdic_precur #TODO
        # tsCorr is total time series (.shape[0]) and .shape[1] are the correlated regions
        # stacked on top of each other (from lag_min to lag_max)
        
        n_tot_regs = 0
        splits = self.corr_xr.split
        if hasattr(self, 'prec_labels') == False:
            print(f'{self.name} is not clustered yet')
        else:
            if np.isnan(self.prec_labels.values).all():
                self.ts_corr = np.array(splits.size*[[]])
            else:
                if self.calc_ts == 'region mean':
                    self.ts_corr = find_precursors.spatial_mean_regions(self, 
                                                precur_aggr=precur_aggr, 
                                                kwrgs_load=kwrgs_load)
                elif self.calc_ts == 'pattern cov':
                    self.ts_corr = loop_get_spatcov(self, 
                                                    precur_aggr=precur_aggr, 
                                                    kwrgs_load=kwrgs_load)
                # self.outdic_precur[var] = precur
                n_tot_regs += max([self.ts_corr[s].shape[1] for s in range(splits.size)])
        return

def corr_map(field, ts):
    """
    This function calculates the correlation coefficent r and 
    the pvalue p for each grid-point of field vs response-variable ts

    """
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)   
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])

    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    
    for i in nonans_gc:
        corr_vals[i], pvals[i] = scipy.stats.pearsonr(ts,field[:,i])
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def granger_map(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    ts = np.expand_dims(ts, axis=1)
    for i in nonans_gc:
        data = np.concatenate((ts, np.expand_dims(field[:,i], axis=1)), axis=1)
        granger = grangercausalitytests(data, [1, 10], verbose=False)
        corr_vals[i], pvals[i], _, _ = granger[10][0]['ssr_ftest']
        # corr_vals[i], pvals[i], _ = granger[1][0]['ssr_chi2test']
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals


# def parcorr_map_spatial(field, ts):
#     x = np.ma.zeros(field.shape[1])
#     corr_vals = np.array(x)
#     pvals = np.array(x)
#     fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
#     nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
#     ts = np.expand_dims(ts, axis=1)
#     for i in nonans_gc:

#         cond_ind_test = ParCorr()
#         if i < 199:
#             east = np.expand_dims(field[:,i+1], axis=1)
#         else:
#             east = np.expand_dims(field[:,0], axis=1)
#         if i > 0:
#             west = np.expand_dims(field[:,i-1], axis=1)
#         else:
#             west = np.expand_dims(field[:,-1], axis=1)
#         data = np.concatenate((west, east), axis=1)
#         # a = cond_ind_test.get_dependence_measure(data,[0,1])
#         # b = cond_ind_test.get_analytic_significance(a, len(ts[0]), 2)
#         a, b = cond_ind_test.run_test_raw(ts, np.expand_dims(field[:,i], axis=1), data)
#         corr_vals[i] = a
#         pvals[i] = b
#     # restore original nans
#     corr_vals[fieldnans] = np.nan
#     return corr_vals, pvals

def parcorr_map_time(field, ts, lag=1, target=False, precur=True):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    if target:
        z = np.expand_dims(ts[:-lag], axis=1)
    ts = np.expand_dims(ts[lag:], axis=1)
    for i in nonans_gc:

        cond_ind_test = ParCorr()
        if precur:
            if target:
                z2 = np.expand_dims(field[:-lag, i], axis=1)
                z = np.concatenate((z,z2), axis=1)
            else:
                z = np.expand_dims(field[:-lag, i], axis=1)
        field_i = np.expand_dims(field[lag:,i], axis=1)
        a, b = cond_ind_test.run_test_raw(ts, field_i, z)
        corr_vals[i] = a
        pvals[i] = b
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def gpdc_map(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    ts = np.expand_dims(ts, axis=1)
    for i in nonans_gc:
        cond_ind_test = GPDC()
        a, b = cond_ind_test.run_test_raw(ts, np.expand_dims(field[:,i], axis=1))
        corr_vals[i] = a
        pvals[i] = b
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def cmiknn_map(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    ts = np.expand_dims(ts, axis=1)
    for i in nonans_gc:
        cond_ind_test = CMIknn()
        a, b = cond_ind_test.run_test_raw(ts, np.expand_dims(field[:,i], axis=1))
        corr_vals[i] = a
        pvals[i] = b
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def rcot_map(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)
    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]
    ts = np.expand_dims(ts, axis=1)
    for i in nonans_gc:
        cond_ind_test = RCOT()
        a, b = cond_ind_test.run_test_raw(ts, np.expand_dims(field[:,i], axis=1))
        corr_vals[i] = a
        pvals[i] = b
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def entropy_map(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)

    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]

    kde_ts = stats.gaussian_kde(ts)([np.arange(-30,30,1)])
    for i in nonans_gc:
        corr_vals[i] = transfer_entropy(field[:,i], ts)
        kde_precur = stats.gaussian_kde(field[:,i])
        kde_precur = kde_precur([np.arange(-30,30,1)])
        chi2, pvals[i], _, _ = stats.chi2_contingency([kde_precur, kde_ts])
    
    mean = corr_vals.mean()
    corr_vals -= mean
    pvals = 1 - pvals
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def entropy_map_pearson(field, ts):
    x = np.ma.zeros(field.shape[1])
    corr_vals = np.array(x)
    pvals = np.array(x)

    fieldnans = np.array([np.isnan(field[:,i]).any() for i in range(x.size)])
    
    nonans_gc = np.arange(0, fieldnans.size)[fieldnans==False]

    # ts_contingency = np.histogram(ts, bins=60, density=False)[0]
    kde_ts = stats.gaussian_kde(ts)([np.arange(-30,30,1)])
    for i in nonans_gc:
        corr_vals[i] = transfer_entropy(field[:,i], ts)
        _, pvals[i] = scipy.stats.pearsonr(ts,field[:,i])
    
    mean = corr_vals.mean()
    corr_vals -= mean
    pvals = 1 - pvals
    # restore original nans
    corr_vals[fieldnans] = np.nan
    return corr_vals, pvals

def transfer_entropy(J, I):
    I1 = I[1:]
    I = I[:-1]
    J = J[:-1] 

    IJ = np.c_[I,J]
    a = conditional_entropy(I1,I)
    b = conditional_entropy(I1, IJ)

    return (a - b)


def conditional_entropy(J, I):
    return (joint_entropy(J, I) - entropy(I))

def joint_entropy(J, I):
    IJ = np.c_[I, J]
    return entropy(IJ)

def entropy(I, base=None):
    n_labels = len(I)
    
    if n_labels <= 1:
        return 0
    
    n_bins = 70
    jointHist, edges = np.histogramdd(I, bins=n_bins, density=False)
    jointHist /= jointHist.sum()

    n_classes = np.count_nonzero(jointHist)
    if n_classes <= 1:
        return 0

    ent = stats.entropy(jointHist.ravel())

    return ent

def loop_get_spatcov(precur, precur_aggr, kwrgs_load):
    
    name            = precur.name
    corr_xr         = precur.corr_xr
    prec_labels     = precur.prec_labels
    df_splits = precur.df_splits
    splits = df_splits.index.levels[0]
    lags            = precur.corr_xr.lag.values
    use_sign_pattern = precur.use_sign_pattern
    
    
    if precur_aggr is None:
        # use precursor array with temporal aggregation that was used to create 
        # correlation map
        precur_arr = precur.precur_arr
    else:
        # =============================================================================
        # Unpack kwrgs for loading 
        # =============================================================================
        filepath = precur.filepath
        kwrgs = {}
        for key, value in kwrgs_load.items():
            if type(value) is list and name in value[1].keys():
                kwrgs[key] = value[1][name]
            elif type(value) is list and name not in value[1].keys():
                kwrgs[key] = value[0] # plugging in default value
            else:
                kwrgs[key] = value
        kwrgs['tfreq'] = precur_aggr ; kwrgs['selbox'] = precur.selbox
        precur_arr = functions_pp.import_ds_timemeanbins(filepath, **kwrgs)

    full_timeserie = precur_arr        
    dates = pd.to_datetime(precur_arr.time.values)
    

    ts_sp = np.zeros( (splits.size), dtype=object)
    for s in splits:
        ts_list = np.zeros( (lags.size), dtype=list )
        track_names = []
        for il,lag in enumerate(lags):
        
            corr_vals = corr_xr.sel(split=s).isel(lag=il)
            mask = prec_labels.sel(split=s).isel(lag=il)
            pattern = corr_vals.where(~np.isnan(mask))
            if use_sign_pattern == True:
                pattern = np.sign(pattern)
            if np.isnan(pattern.values).all():
                # no regions of this variable and split
                nants = np.zeros( (dates.size, 1) )
                nants[:] = np.nan
                ts_list[il] = nants
                pass
            else:
                # if normalize == True:
                #     spatcov_full = calc_spatcov(full_timeserie, pattern)
                #     mean = spatcov_full.sel(time=dates_train).mean(dim='time')
                #     std = spatcov_full.sel(time=dates_train).std(dim='time')
                #     spatcov_test = ((spatcov_full - mean) / std)
                # elif normalize == False:
                xrts = find_precursors.calc_spatcov(full_timeserie, pattern)
                ts_list[il] = xrts.values[:,None]
            track_names.append(f'{lag}..0..{precur.name}' + '_sp')
        
        # concatenate timeseries all of lags
        tsCorr = np.concatenate(tuple(ts_list), axis = 1)

            
        ts_sp[s] = pd.DataFrame(tsCorr, 
                                index=dates,
                                columns=track_names)
    # df_sp = pd.concat(list(ts_sp), keys=range(splits.size))
    return ts_sp
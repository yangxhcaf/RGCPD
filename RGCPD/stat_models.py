#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 24 20:01:23 2019

@author: semvijverberg
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.api import add_constant
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.model_selection import GridSearchCV, StratifiedKFold
import itertools
flatten = lambda l: list(itertools.chain.from_iterable(l))
#from sklearn import metrics
#from sklearn.metrics import make_scorer


def logit(y_ts, df_norm, keys):
    #%%
    '''
    X contains all precursor data, incl train and test
    X_train, y_train are split up by TrainIsTrue
    Preciction is made for whole timeseries    
    '''
    import warnings
    warnings.simplefilter(action='ignore', category=FutureWarning)
    
    if keys is None:
        no_data_col = ['TrainIsTrue', 'RV_mask', 'fit_model_mask']
        keys = df_norm.columns
        keys = [k for k in keys if k not in no_data_col]
        
    # Get training years
    x_fit_mask, y_fit_mask, x_pred_mask, y_pred_mask = get_masks(df_norm)
    
    X = df_norm[keys]
    X = add_constant(X)
    X_train = X[x_fit_mask.values]
    X_pred  = X[x_pred_mask.values]
    
    RV_bin_fit = y_ts['bin']
    RV_bin_fit = RV_bin_fit.loc[y_fit_mask.index].copy()
    y_train = RV_bin_fit[y_fit_mask.values].squeeze()     

    if y_pred_mask is not None:
        y_dates = RV_bin_fit[y_pred_mask.values].index
    else:
        y_dates = X.index

    # Statsmodel wants the dataframes and that the indices are aligned. 
    # Therefore making new dataframe for X_train
    try:
        model_set = sm.Logit(y_train, 
                         pd.DataFrame(X_train.values, index=y_train.index), disp=0)
    except:
        print(x_fit_mask)
        print(X_train)
        print(y_train)
        
    try:
        model = model_set.fit( disp=0, maxfun=60 )
        prediction = model.predict(X_pred)
    except np.linalg.LinAlgError as err:
        if 'Singular matrix' in str(err):
            model = model_set.fit(method='bfgs', disp=0 )
            prediction = model.predict(X_pred)
        else:
            raise
    except Exception as e:
        print(e)
        model = model_set.fit(method='bfgs', disp=0 )
        prediction = model.predict(X_pred)
    
    prediction = pd.DataFrame(prediction.values, index=y_dates, columns=[0])                          
    #%%
    return prediction, model

def GBR_logitCV(y_ts, df_norm, keys, kwrgs_GBR=None, verbosity=0):
    #%%
    '''
    X contains all precursor data, incl train and test
    X_train, y_train are split up by TrainIsTrue
    Preciction is made for whole timeseries    
    '''
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning) 
        
    if kwrgs_GBR == None:
        # use Bram settings
        kwrgs_GBR = {'max_depth':3,
                 'learning_rate':0.001,
                 'n_estimators' : 1250,
                 'max_features':'sqrt',
                 'subsample' : 0.5}
    
    # find parameters for gridsearch optimization
    kwrgs_gridsearch = {k:i for k, i in kwrgs_GBR.items() if type(i) == list}
    # only the constant parameters are kept
    kwrgs = kwrgs_GBR.copy()
    [kwrgs.pop(k) for k in kwrgs_gridsearch.keys()]

    # Get training years
    x_fit_mask, y_fit_mask, x_pred_mask, y_pred_mask = get_masks(df_norm)
    
    X = df_norm[keys]
    X_train = X[x_fit_mask.values]
    X_pred  = X[x_pred_mask.values]

    RV_ts_fit = y_ts['cont']
    RV_ts_fit = RV_ts_fit.loc[y_fit_mask.index]
    y_train = RV_ts_fit[y_fit_mask.values].squeeze() 

    if y_pred_mask is not None:
        y_dates = RV_ts_fit[y_pred_mask.values].index
    else:
        y_dates = X.index

    y_train = RV_ts_fit[y_fit_mask.values] 
    
    if y_pred_mask is not None:
        y_dates = RV_ts_fit[y_pred_mask.values].index
    # add sample weight mannually
#    y_train[y_train > y_train.mean()] = 10 * y_train[y_train > y_train.mean()]
    
    # sample weight not yet supported by GridSearchCV (august, 2019)
#    y_wghts = (RV.RV_bin[TrainIsTrue.values] + 1).squeeze().values
    regressor = GradientBoostingRegressor(**kwrgs)

    if len(kwrgs_gridsearch) != 0:
#        scoring   = 'r2'
        scoring   = 'neg_mean_squared_error'
        regressor = GridSearchCV(regressor,
                  param_grid=kwrgs_gridsearch,
                  scoring=scoring, cv=5, refit=scoring, 
                  return_train_score=False)
        regressor.fit(X_train, y_train.values.ravel())
        if verbosity == 1:
            results = regressor.cv_results_
            scores = results['mean_test_score'] 
            improv = int(100* (min(scores)-max(scores)) / max(scores))
            print("Hyperparam tuning led to {:}% improvement, best {:.2f}, "
                  "best params {}".format(
                    improv, regressor.best_score_, regressor.best_params_))
    else:
        regressor.fit(X_train, y_train.values.ravel())
    
        
    prediction = pd.DataFrame(regressor.predict(X_pred), 
                              index=y_dates, columns=[0])
    # add masks for second fit with logitCV
    TrainIsTrue_ = df_norm['TrainIsTrue'].loc[y_pred_mask[y_pred_mask.values].index]
    prediction['TrainIsTrue'] = pd.Series(TrainIsTrue_.values, 
                                  index=TrainIsTrue_.index)

    logit_pred, model_logit = logit_skl(y_ts, prediction, keys=None)
    
    
    
#    logit_pred.plot() ; plt.plot(RV.RV_bin)
#    plt.figure()
#    prediction.plot() ; plt.plot(RV.RV_ts)
#    metrics_sklearn(RV.RV_bin, logit_pred.values, y_pred_c)
    #%%
    return logit_pred, regressor


def logit_skl(y_ts, df_norm, keys=None, kwrgs_logit=None):
    #%%
    '''
    X contains all precursor data, incl train and test
    X_train, y_train are split up by TrainIsTrue
    Preciction is made for whole timeseries    
    '''

    if keys is None:
            no_data_col = ['TrainIsTrue', 'RV_mask', 'fit_model_mask']
            keys = df_norm.columns
            keys = [k for k in keys if k not in no_data_col]
    import warnings 
    warnings.filterwarnings("ignore", category=DeprecationWarning) 
#    warnings.filterwarnings("ignore", category=FutureWarning) 
        
    if kwrgs_logit == None:
        # use Bram settings
        kwrgs_logit = { 'class_weight':{ 0:1, 1:1},
                'scoring':'brier_score_loss',
                'penalty':'l2',
                'solver':'lbfgs'}
                             
    
    # find parameters for gridsearch optimization
    kwrgs_gridsearch = {k:i for k, i in kwrgs_logit.items() if type(i) == list}
    # only the constant parameters are kept
    kwrgs = kwrgs_logit.copy()
    [kwrgs.pop(k) for k in kwrgs_gridsearch.keys()]
    
    # Get training years
    x_fit_mask, y_fit_mask, x_pred_mask, y_pred_mask = get_masks(df_norm)
    
    X = df_norm[keys]
#    X = add_constant(X)
    X_train = X[x_fit_mask.values]
    X_pred  = X[x_pred_mask.values]
    
    RV_bin_fit = y_ts['bin']
    RV_bin_fit = RV_bin_fit.loc[y_fit_mask.index]
    RV_bin_fit = RV_bin_fit.loc[y_fit_mask.index]
    y_train = RV_bin_fit[y_fit_mask.values].squeeze()   

    if y_pred_mask is not None:
        y_dates = RV_bin_fit[y_pred_mask.values].index
    else:
        y_dates = X.index
    
    # sample weight not yet supported by GridSearchCV (august, 2019)
    strat_cv = StratifiedKFold(5, shuffle=False)
    model = LogisticRegressionCV(Cs=10, fit_intercept=True, 
                                 cv=strat_cv,
                                 n_jobs=1, 
                                 **kwrgs_logit)
                                 
    model.fit(X_train, y_train)
    y_pred = model.predict_proba(X_pred)[:,1]

    prediction = pd.DataFrame(y_pred, index=y_dates, columns=[0])

    #%%
    return prediction, model

def get_masks(df_norm):
    '''
    x_fit and y_fit can be encompass more data then x_pred, therefore they
    are split from x_pred and y_pred.
    y_pred is needed in the special occasion no past (lagged) data for X avaible
    if these are not given, then model x_fit, y_fit, x_pred & y_pred are 
    fitted according to TrainIsTrue at lag=0. 
    '''
    TrainIsTrue = df_norm['TrainIsTrue']
    if 'x_fit' in df_norm.columns:
        x_fit_mask = np.logical_and(TrainIsTrue, df_norm['x_fit'])
    else:
        x_fit_mask = TrainIsTrue
    if 'y_fit' in df_norm.columns:
        y_dates = df_norm['y_fit'][df_norm['y_fit']].index
        TrainIsTrue_yfit = TrainIsTrue.loc[y_dates]
        y_fit_mask = np.logical_and(TrainIsTrue_yfit, df_norm['y_fit'].loc[y_dates])
        y_fit_mask = y_fit_mask
    else:
        y_fit_mask = TrainIsTrue
    if 'x_pred' in df_norm.columns:
        x_pred_mask = df_norm['x_pred']
    else:
        x_pred_mask = pd.Series(np.repeat(True, x_fit_mask.size),
                                index=x_fit_mask.index)
    if 'y_pred' in df_norm.columns:
        y_pred_dates = df_norm['y_pred'][df_norm['y_pred']].index
        y_pred_mask = df_norm['y_pred'].loc[y_pred_dates]
    else:
        y_pred_mask = None
    return x_fit_mask, y_fit_mask, x_pred_mask, y_pred_mask

def plot_importances(GBR_models_split_lags, lag=1, plot=True, cutoff=6):
    #%%

    if type(lag) is int:
        df_all = _get_importances(GBR_models_split_lags, lag=lag)
        
        if plot:
            fig, ax = plt.subplots(constrained_layout=True)
            lag_d = df_all.index[0]
            df_r = df_all.loc[lag_d].sort_values()
            ax.set_title(f"Relative Feature Importances")
            ax.barh(np.arange(df_all.columns.size), df_r.squeeze().values, tick_label=df_r.index)
            ax.text(0.97, 0.07, f'lead time: {lag_d} days',
                    fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='wheat', 
                              edgecolor='black', alpha=0.5),
                horizontalalignment='right',
                verticalalignment='top',
                transform=ax.transAxes)
    elif type(lag) is list or type(lag) is np.ndarray:
        
        dfs = []
        for i, l in enumerate(lag):
            dfs.append(_get_importances(GBR_models_split_lags, lag=l))
        all_vars = []
        all_vars.append([list(df.columns.values) for df in dfs])
        all_vars = np.unique(flatten(flatten(all_vars)))
        df_all = pd.DataFrame(columns=all_vars)
        for i, l in enumerate(lag):
            df_n = dfs[i] 
            df_all = df_all.append(df_n, sort=False)
        sort_index = df_all.mean(0).sort_values(ascending=False).index
        df_all = df_all.reindex(sort_index, axis='columns')
        
        if plot:

            # plot vs lags
            fig, ax = plt.subplots(constrained_layout=True)
            styles_ = [['solid'], ['dashed']]
            styles = flatten([6*s for i, s in enumerate(styles_)])[:cutoff]
            linewidths = np.linspace(cutoff/3, 1, cutoff)
            for col, style, lw in zip(df_all.columns, styles, linewidths):
                df_all.loc[:,col].plot(figsize=(8,5), 
                                      linestyle=style,
                                      linewidth=lw,
                                      ax=ax)
            ax.legend()
            ax.set_title('relative feature importance vs. lead time')
            ax.set_xlabel('lead time [days]')
    #%%
    return df_all


def _get_importances(GBR_models_split_lags, lag=1, plot=True, _ax=None):
    #%%
    '''
    get feature importance for single lag
    '''

    GBR_models_split = GBR_models_split_lags[f'lag_{lag}']
    feature_importances = {}
    
    for years, regressor in GBR_models_split.items():
        for name, importance in zip(regressor.X.columns, regressor.feature_importances_):
            if name not in feature_importances:
                feature_importances[name] = [0, 0]
            feature_importances[name][0] += importance
            feature_importances[name][1] += 1

    names, importances = [], []

    for name, (importance, count) in feature_importances.items():
        names.append(name)
        importances.append(float(importance) / float(count))

    importances = np.array(importances) / np.sum(importances)
    order = np.argsort(importances)
    names_order = [names[index] for index in order] ; names_order.reverse()
    freq = (regressor.X.index[1] - regressor.X.index[0]).days
    lags_tf = [l*freq for l in [lag]]
    if freq != 1:
        # the last day of the time mean bin is tfreq/2 later then the centerered day
        lags_tf = [l_tf- int(freq/2) if l_tf!=0 else 0 for l_tf in lags_tf]
    df = pd.DataFrame([sorted(importances, reverse=True)], columns=names_order, index=lags_tf)      

    #%%
    return df
    


#def GBR(y_ts, df_norm, keys=None, kwrgs_GBR=None, verbosity=0):
#    #%%
#    '''
#    X contains all precursor data, incl train and test
#    X_train, y_train are split up by TrainIsTrue
#    Preciction is made for whole timeseries    
#    '''
#    import warnings
#    warnings.filterwarnings("ignore", category=DeprecationWarning) 
#    warnings.simplefilter(action='ignore', category=FutureWarning)
#    
#    
#    if keys is None:
#        no_data_col = ['TrainIsTrue', 'RV_mask', 'fit_model_mask']
#        keys = df_norm.columns
#        keys = [k for k in keys if k not in no_data_col]
#        
#    if kwrgs_GBR == None:
#        # use Bram settings
#        kwrgs_GBR = {'max_depth':3,
#                 'learning_rate':0.001,
#                 'n_estimators' : 1250,
#                 'max_features':'sqrt',
#                 'subsample' : 0.5}
#    
#    # find parameters for gridsearch optimization
#    kwrgs_gridsearch = {k:i for k, i in kwrgs_GBR.items() if type(i) == list}
#    # only the constant parameters are kept
#    kwrgs = kwrgs_GBR.copy()
#    [kwrgs.pop(k) for k in kwrgs_gridsearch.keys()]
#    
#    X = df_norm[keys]
#    X = add_constant(X)
#    RV_ts = RV.RV_ts_fit
#    # Get training years
#    TrainIsTrue = df_norm['TrainIsTrue'] 
#    # Get mask to make only prediction for RV_mask dates
#    pred_mask   = df_norm['RV_mask']
#  
#    X_train = X[TrainIsTrue]
#    y_train = RV_ts[TrainIsTrue.values] 
#    
#    # add sample weight mannually
##    y_train[y_train > y_train.mean()] = 10 * y_train[y_train > y_train.mean()]
#    
#    # sample weight not yet supported by GridSearchCV (august, 2019)
##    y_wghts = (RV.RV_bin[TrainIsTrue.values] + 1).squeeze().values
#    regressor = GradientBoostingRegressor(**kwrgs)
#
#    if len(kwrgs_gridsearch) != 0:
##        scoring   = 'r2'
#        scoring   = 'neg_mean_squared_error'
#        regressor = GridSearchCV(regressor,
#                  param_grid=kwrgs_gridsearch,
#                  scoring=scoring, cv=5, refit=scoring, 
#                  return_train_score=False)
#        regressor.fit(X_train, y_train.values.ravel())
#        results = regressor.cv_results_
#        scores = results['mean_test_score'] 
#        improv = int(100* (min(scores)-max(scores)) / max(scores))
#        print("Hyperparam tuning led to {:}% improvement, best {:.2f}, "
#              "best params {}".format(
#                improv, regressor.best_score_, regressor.best_params_))
#    else:
#        regressor.fit(X_train, y_train.values.ravel())
#    
#
#    prediction = pd.DataFrame(regressor.predict(X[pred_mask]),
#                              index=X[pred_mask].index, columns=[0])
#    prediction['TrainIsTrue'] = pd.Series(TrainIsTrue.values, index=X.index)
#    prediction['RV_mask'] = pd.Series(pred_mask.values, index=pred_mask.index)
#    
#    logit_pred, model_logit = logit(RV, prediction, keys=None)
#    #%%
#    return logit_pred, (model_logit, regressor)
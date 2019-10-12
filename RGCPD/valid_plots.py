#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 29 20:15:50 2019

@author: semvijverberg
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
#from sklearn import metrics
import functions_pp
from sklearn.calibration import calibration_curve
import seaborn as sns
from itertools import chain
flatten = lambda l: list(chain.from_iterable(l))


from matplotlib import cycler
nice_colors = ['#EE6666', '#3388BB', '#9988DD',
                 '#EECC55', '#88BB44', '#FFBBBB']
colors_nice = cycler('color',
                nice_colors)
colors_datasets = sns.color_palette('deep')

plt.rc('axes', facecolor='#E6E6E6', edgecolor='none',
       axisbelow=True, grid=True, prop_cycle=colors_nice)
plt.rc('grid', color='w', linestyle='solid')
plt.rc('xtick', direction='out', color='black')
plt.rc('ytick', direction='out', color='black')
plt.rc('patch', edgecolor='#E6E6E6')
plt.rc('lines', linewidth=2)

mpl.rcParams['figure.figsize'] = [7.0, 5.0]
mpl.rcParams['figure.dpi'] = 100
mpl.rcParams['savefig.dpi'] = 600

mpl.rcParams['font.size'] = 13
mpl.rcParams['legend.fontsize'] = 'medium'
mpl.rcParams['figure.titlesize'] = 'medium'



def corr_matrix_pval(df, alpha=0.05):
    from scipy import stats
    if type(df) == type(pd.DataFrame()):
        cross_corr = np.zeros( (df.columns.size, df.columns.size) )
        pval_matrix = np.zeros_like(cross_corr)
        for i1, col1 in enumerate(df.columns):
            for i2, col2 in enumerate(df.columns):
                pval = stats.pearsonr(df[col1].values, df[col2].values)
                pval_matrix[i1, i2] = pval[-1]
                cross_corr[i1, i2]  = pval[0]
        # recreate pandas cross corr
        cross_corr = pd.DataFrame(data=cross_corr, columns=df.columns, 
                                  index=df.columns)
    sig_mask = pval_matrix < alpha
    return cross_corr, sig_mask, pval_matrix

def build_ts_matric(df_init, win=20, lag=0, columns=list, rename=dict, period='fullyear'):
    #%%
    '''
    period = ['fullyear', 'summer60days', 'pre60days']
    '''
    splits = df_init.index.levels[0]
    dates_full_orig = df_init.loc[0].index
    dates_RV_orig   = df_init.loc[0].index[df_init.loc[0]['RV_mask']==True]
    
    
    if columns is None:
        columns = df_init.columns
        
    df_cols = df_init[columns]
    
    TrainIsTrue = df_init['TrainIsTrue']

    list_test = []
    for s in range(splits.size):
        TestIsTrue = TrainIsTrue[s]==False
        list_test.append(df_cols.loc[s][TestIsTrue])
    
    df_test = pd.concat(list_test).sort_index()


    # shift precursor vs. tmax 
    for c in df_test.columns[1:]:
        df_test[c] = df_test[c].shift(periods=-lag)
         
    # bin means
    df_test = df_test.resample(f'{win}D').mean()
    
    if period=='fullyear':
        dates_sel = dates_full_orig.strftime('%Y-%m-%d')
    elif period == 'summer60days':
        dates_sel = dates_RV_orig.strftime('%Y-%m-%d')
    elif period == 'pre60days':
        dates_sel = (dates_RV_orig - pd.Timedelta(60, unit='d')).strftime('%Y-%m-%d')
    
    # after resampling, not all dates are in their:
    dates_sel =  pd.to_datetime([d for d in dates_sel if d in df_test.index] )
    df_period = df_test.loc[dates_sel, :].dropna()

    if rename is not None:
        df_period = df_period.rename(rename, axis=1)
        
    corr, sig_mask, pvals = corr_matrix_pval(df_period, alpha=0.01)

    # Generate a mask for the upper triangle
    mask_tri = np.zeros_like(corr, dtype=np.bool)
    
    mask_tri[np.triu_indices_from(mask_tri)] = True
    mask_sig = mask_tri.copy()
    mask_sig[sig_mask==False] = True
  
    # removing meaningless row and column
    cols = corr.columns
    corr = corr.drop(cols[0], axis=0).drop(cols[-1], axis=1)
    mask_sig = mask_sig[1:, :-1]
    mask_tri = mask_tri[1:, :-1]
    # Set up the matplotlib figure
    f, ax = plt.subplots(figsize=(10, 10))

    # Generate a custom diverging colormap
    cmap = sns.diverging_palette(220, 10, n=9, l=30, as_cmap=True)
    
    
    ax = sns.heatmap(corr, ax=ax, mask=mask_tri, cmap=cmap, vmax=1E99, center=0,
                square=True, linewidths=.5, 
                 annot=False, annot_kws={'size':30}, cbar=False)
    
    
    sig_bold_labels = sig_bold_annot(corr, mask_sig)
    # Draw the heatmap with the mask and correct aspect ratio
    ax = sns.heatmap(corr, ax=ax, mask=mask_tri, cmap=cmap, vmax=1, center=0,
                square=True, linewidths=.5, cbar_kws={"shrink": .8},
                 annot=sig_bold_labels, annot_kws={'size':30}, cbar=False, fmt='s')
    
    ax.tick_params(axis='both', labelsize=15, 
                   bottom=True, top=False, left=True, right=False,
                   labelbottom=True, labeltop=False, labelleft=True, labelright=False)
    
    ax.set_xticklabels(corr.columns, fontdict={'fontweight':'bold', 
                                               'fontsize':25})
    ax.set_yticklabels(corr.index, fontdict={'fontweight':'bold',
                                               'fontsize':25}, rotation=0) 
    #%%
    return

def sig_bold_annot(corr, pvals):
    corr_str = np.zeros_like( corr, dtype=str ).tolist()
    for i1, r in enumerate(corr.values):
        for i2, c in enumerate(r):
            if pvals[i1, i2] <= 0.05 and pvals[i1, i2] > 0.01:
                corr_str[i1][i2] = '{:.2f}*'.format(c)
            if pvals[i1, i2] <= 0.01:
                corr_str[i1][i2]= '{:.2f}**'.format(c)        
            elif pvals[i1, i2] > 0.05: 
                corr_str[i1][i2]= '{:.2f}'.format(c)
    return np.array(corr_str) 

def plot_score_lags(df_metric, metric, color, lags_tf, clim=None,
                    cv_lines=False, col=0, ax=None):
    #%%

    if ax==None:
        print('ax == None')
        ax = plt.subplot(111)

    if metric == 'BSS':
        y_lim = (-0.4, 0.6)
    elif metric[:3] == 'AUC':
        y_lim = (0,1.0)
    elif metric in ['Precision', 'Accuracy']:
        y_lim = (0,1)
        y_b = clim
    y = np.array(df_metric.loc[metric])
    y_min = np.array(df_metric.loc['con_low'])
    y_max = np.array(df_metric.loc['con_high'])
    if cv_lines == True:
        y_cv  = [0]


    x = lags_tf
    if 0 in lags_tf:
        tfreq = 2 * (lags_tf[1] - lags_tf[0])
    else:
        tfreq = (lags_tf[1] - lags_tf[0])
#    tfreq = max([lags_tf[i+1] - lags_tf[i] for i in range(len(lags_tf)-1)])
    
    style = 'solid'
    ax.fill_between(x, y_min, y_max, linestyle='solid', 
                            edgecolor='black', facecolor=color, alpha=0.3)
    ax.plot(x, y, color=color, linestyle=style, 
                    linewidth=2, alpha=1 ) 
    ax.scatter(x, y, color=color, linestyle=style, 
                    linewidth=2, alpha=1 ) 
    if cv_lines == True:
        for f in range(y_cv.shape[1]):
            style = 'dashed'
            ax.plot(x, y_cv[f,:], color=color, linestyle=style, 
                         alpha=0.35 ) 
    ax.set_xlabel('Lead time [days]', fontsize=13, labelpad=0.1)
    ax.grid(b=True, which='major')
#    ax.set_title('{}-day mean'.format(col))
    if min(x) == 1:
        xmin = 0
        xticks = np.arange(min(x), max(x)+1E-9, 10) ; 
        xticks[0] = 1
    elif min(x) == 0:
        xmin = int(tfreq/2)
        xticks = np.arange(xmin, max(x)+1E-9, 10) ; 
        xticks = np.insert(xticks, 0, 0)
    else:
        xticks = np.arange(min(x), max(x)+1E-9, 10) ; 

        
    ax.set_xticks(xticks)
    ax.set_ylim(y_lim)
    ax.set_ylabel(metric)
    if metric == 'BSS':
        y_major = [-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6]
        ax.set_yticks(y_major, minor=False)
        ax.set_yticklabels(y_major)
        ax.set_yticks(np.arange(-0.6,0.6+1E-9, 0.1), minor=True)
        ax.hlines(y=0, xmin=min(x), xmax=max(x), linewidth=1)
        ax.text(max(x), 0 - 0.05, 'Benchmark clim. pred.', 
                horizontalalignment='right', fontsize=12,
                verticalalignment='center', 
                rotation=0, rotation_mode='anchor', alpha=0.5)
    elif metric == 'AUC-ROC':
        y_b = 0.5
        ax.set_yticks(np.arange(0.5,1+1E-9, 0.1), minor=True)
        ax.hlines(y=y_b, xmin=min(x), xmax=max(x), linewidth=1) 
    elif metric in ['AUC-PR', 'Precision', 'Accuracy']:
        ax.set_yticks(np.arange(0.5,1+1E-9, 0.1), minor=True)
        y_b = clim
        ax.hlines(y=y_b, xmin=min(x), xmax=max(x), linewidth=1) 
        
    if metric in ['Precision', 'Accuracy']:
#        threshold = int(100 * clim/2)
        ax.text(0.00, 0.05, 'Pos. pred. for top 75% of above clim. prob.', 
                horizontalalignment='left', fontsize=10,
                verticalalignment='center', transform=ax.transAxes,
                rotation=0, rotation_mode='anchor', alpha=0.5)
    if metric in ['AUC-ROC', 'AUC-PR', 'Precision']:
        ax.text(max(x), y_b-0.05, 'Benchmark rand. pred.', 
                horizontalalignment='right', fontsize=12,
                verticalalignment='center', 
                rotation=0, rotation_mode='anchor', alpha=0.5)
    if col != 0 :
        ax.set_ylabel('')
        ax.tick_params(labelleft=False)
    
    
        
#    str_freq = str(x).replace(' ' ,'')  
    #%%
    return ax


def rel_curve_base(RV, lags_tf, n_bins=5, col=0, ax=None):
    #%%



    if ax==None:    
        print('ax == None')
        fig, ax = plt.subplots(1, facecolor='white')
        
    ax.set_fc('white')

    ax.patch.set_edgecolor('black')  
    ax.patch.set_linewidth('0.5')  
    ax.grid(b=True, which = 'major', axis='both', color='black',
            linestyle='--', alpha=0.2)
    
    n_bins = 5

    # perfect forecast
    perfect = np.arange(0,1+1E-9,(1/n_bins))
    pos_text = np.array((0.5, 0.52))
    ax.plot(perfect,perfect, color='black', alpha=0.5)
    trans_angle = plt.gca().transData.transform_angles(np.array((45,)),
                                                       pos_text.reshape((1, 2)))[0]
    ax.text(pos_text[0], pos_text[1], 'perfect forecast', fontsize=14,
                   rotation=trans_angle, rotation_mode='anchor')
    obs_clim = RV.prob_clim.mean()[0]
    ax.text(obs_clim+0.2, obs_clim-0.05, 'Obs. clim', 
                horizontalalignment='center', fontsize=14,
         verticalalignment='center', rotation=0, rotation_mode='anchor')
    ax.hlines(y=obs_clim, xmin=0, xmax=1, label=None, color='grey',
              linestyle='dashed')
    ax.vlines(x=obs_clim, ymin=0, ymax=1, label=None, color='grey', 
              linestyle='dashed')
    
    # forecast clim
#    pred_clim = y_pred_all.mean().values
#    ax.vlines(x=np.mean(pred_clim), ymin=0, ymax=1, label=None)
#    ax.vlines(x=np.min(pred_clim), ymin=0, ymax=1, label=None, alpha=0.2)
#    ax.vlines(x=np.max(pred_clim), ymin=0, ymax=1, label=None, alpha=0.2)
    ax.text(np.min(obs_clim)-0.025, obs_clim.mean()+0.3, 'Obs. clim', 
            horizontalalignment='center', fontsize=14,
     verticalalignment='center', rotation=90, rotation_mode='anchor')
    # resolution = reliability line
    BSS_clim_ref = perfect - obs_clim
    dist_perf = (BSS_clim_ref / 2.) + obs_clim
    x = np.arange(0,1+1E-9,1/n_bins)
    ax.plot(x, dist_perf, c='grey')
    def get_angle_xy(x, y):
        import math
        dy = np.mean(dist_perf[1:] - dist_perf[:-1])
        dx = np.mean(x[1:] - x[:-1])
        angle = np.rad2deg(math.atan(dy/dx))
        return angle
    angle = get_angle_xy(x, dist_perf)
    pos_text = (x[int(4/n_bins)], dist_perf[int(2/n_bins)]+0.04)
    trans_angle = plt.gca().transData.transform_angles(np.array((angle,)),
                                      np.array(pos_text).reshape((1, 2)))[0]
#    ax.text(pos_text[0], pos_text[1], 'resolution=reliability', 
#            horizontalalignment='center', fontsize=14,
#     verticalalignment='center', rotation=trans_angle, rotation_mode='anchor')
    # BSS > 0 ares
    ax.fill_between(x, dist_perf, perfect, color='grey', alpha=0.5) 
    ax.fill_betweenx(perfect, x, np.repeat(obs_clim, x.size), 
                    color='grey', alpha=0.5) 
    # Better than random
    ax.fill_between(x, dist_perf, np.repeat(obs_clim, x.size), color='grey', alpha=0.2) 
    if col == 0:
        ax.set_ylabel('Fraction of Positives')
    else:
        ax.tick_params(labelleft=False)
    ax.set_xlabel('Mean Predicted Value')
    #%%
    return ax, n_bins
    #%%
def rel_curve(RV, y_pred_all, color, lags_tf, n_bins, mean_lags=True, ax=None):
    #%%
    
    if ax==None:    
        print('ax == None')
        ax, n_bins = rel_curve_base(RV, lags_tf)
    
    strategy = 'uniform' # 'quantile' or 'uniform'
    fop = [] ; mpv = []
    for l, lag in enumerate(lags_tf):
        
        fraction_of_positives, mean_predicted_value = calibration_curve(RV.RV_bin, y_pred_all[lag], 
                                                                       n_bins=n_bins, strategy=strategy)
        fop.append(fraction_of_positives)
        mpv.append(mean_predicted_value)
    fop = np.array(fop)
    mpv = np.array(mpv)
    if len(fop.shape) == 2:
        # al bins are present, we can take a mean over lags
        # plot forecast
        mean_mpv = np.mean(mpv, 0) ; mean_fop = np.mean(fop, 0)
        fop_std = np.std(fop, 0)
    else:
        bins = np.arange(0,1+1E-9,1/n_bins)
        b_prev = 0
        dic_mpv = {}
        dic_fop = {}
        for i, b in enumerate(bins[1:]):
            
            list_mpv = []
            list_fop = []
            for i_lags, m_ in enumerate(mpv):
                m_ = list(m_)
                # if mpv falls in bin, it is added to the list, which will added to 
                # the dict_mpv
                
                list_mpv.append([val for val in m_ if (val < b and val > b_prev)])
                list_fop.append([fop[i_lags][m_.index(val)] for idx,val in enumerate(m_) if (val < b and val > b_prev)])
            dic_mpv[i] = flatten(list_mpv)
            dic_fop[i] = flatten(list_fop)
            b_prev = b
        mean_mpv = np.zeros( (n_bins) )
        mean_fop = np.zeros( (n_bins) )
        fop_std  = np.zeros( (n_bins) )
        for k, item in dic_mpv.items():
            mean_mpv[k] = np.mean(item)
            mean_fop[k] = np.mean(dic_fop[k])
            fop_std[k]  = np.std(dic_fop[k])
    
    ax.plot(mean_mpv, mean_fop, color=color, label=f'fc lag {lag}') ; 
        
    ax.fill_between(mean_mpv, mean_fop+fop_std, 
                    mean_fop-fop_std, label=None,
                    alpha=0.2, color=color) ; 
    color_line = ax.lines[-1].get_c() # get color
    # determine size freq
    freq = np.histogram(y_pred_all[lag], bins=n_bins)[0]
    n_freq = freq / RV.RV_ts.size
    ax.scatter(mean_mpv, mean_fop, s=n_freq*2000, 
               c=color_line, alpha=0.5)
        

    #%%        
    return ax

def plot_oneyr_events(df, event_percentile, test_year):
    #%%
    fig = plt.figure(figsize=(15, 5))
    ax = fig.add_subplot(111)
    
    linestyles = ['solid', 'dashed', 'stippled']
    
    for i, col in enumerate(df.columns):
        if event_percentile == 'std':
            # binary time serie when T95 exceeds 1 std
            threshold = df[col].mean() + df[col].std()
        else:
            percentile = event_percentile
            threshold = np.percentile(df[col], percentile)
    
        testyear = df[df.index.year == test_year]
        freq = pd.Timedelta(testyear.index.values[1] - testyear.index.values[0])
        plotpaper = df.loc[pd.date_range(start=testyear.index.values[0],
                                                    end=testyear.index.values[-1],
                                                    freq=freq )]

    
        color = nice_colors[i]
        ax.plot_date(plotpaper.index, plotpaper[col].values, color=color, 
                     linewidth=3, linestyle=linestyles[i], label=col, alpha=0.8)
        ax.axhline(y=threshold, color=color, linewidth=2 )
        if i == 0:
            label = 'Events'
        else:
            label = None
        ax.fill_between(plotpaper.index, threshold, plotpaper[col].values.squeeze(), 
                         where=(plotpaper[col].values.squeeze() > threshold),
                     interpolate=True, color="crimson", label=label)
        ax.legend(fontsize='x-large', fancybox=True, facecolor='grey',
                  frameon=True, framealpha=0.3)
        ax.set_title('Timeseries and Events', fontsize=18)
        ax.set_ylabel('Temperature anomalies [K]', fontsize=15)
        ax.set_xlabel('')
    #%%
    return

def plot_events(RV, color, n_yrs = 10, col=0, ax=None):
    #%%
#    ax=None

    if type(n_yrs) == int:
        years = []
        sorted_ = RV.freq.sort_values().index
        years.append(sorted_[:int(n_yrs/2)])
        years.append(sorted_[-int(n_yrs/2):])
        years = flatten(years)
        dates_ts = []
        for y in years:
            d = RV.dates_RV[RV.dates_RV.year == y]
            dates_ts.append(d)
        
        dates_ts = pd.to_datetime(flatten(dates_ts))
    else:
        dates_ts = RV.RV_bin.index
        
    if ax==None:    
        print('ax == None')
        fig, ax = plt.subplots(1, subplot_kw={'facecolor':'white'})
        
    else:
        ax.axes.set_facecolor('white')
        ax.patch.set_edgecolor('black')  
        ax.patch.set_linewidth('0.5')  
    
    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]
    y = RV.RV_bin.loc[dates_ts]

    years = np.array(years)
    x = np.linspace(0, years.size, dates_ts.size)
    ax.bar(x, y.values.ravel(), alpha=0.75, color='silver', width=0.1, label='events')
    clim_prob = RV.RV_bin.sum() / RV.RV_bin.size
    ax.hlines(clim_prob, x[0], x[-1], label='Clim prob.')
    
    
    means = []
    for chnk in list(chunks(x, int(dates_ts.size/2.))):
        means.append( chnk.mean() )
    ax.margins(0.)
    cold_hot = means
    labels =['Lowest \nn-event years', 'Highest \nn-event years']
    ax.set_xticks(cold_hot)    
    ax.set_xticklabels(labels)
    minor_ticks = np.linspace(0, x.max(), dates_ts.size)
    ax.set_xticks(minor_ticks, minor=True);   
    ax.grid(b=True,which='major', axis='y', color='grey', linestyle='dotted', 
            linewidth=1)
    if col == 0:
        ax.legend(facecolor='white', markerscale=2, handlelength=0.75)
        ax.set_ylabel('Probability', labelpad=-3)
        probs = [f"{int(i*100)}%" for i in np.arange(0,1+1E-9,0.2)]
        ax.set_yticklabels(probs)
    else:
        ax.tick_params(labelleft=False)
        
        
    #%%
    return ax, dates_ts 

def plot_ts(RV, y_pred_all, dates_ts, color, lag_i=1, ax=None):
    #%%

    if ax == None:
        ax, dates_ts = plot_events(RV, color, ax=None)
        
#    dates = y_pred_all.index
    n_yrs = np.unique(dates_ts.year).size
    x = np.linspace(0, n_yrs, dates_ts.size)
    y = y_pred_all.iloc[:,lag_i].loc[dates_ts]
    ax.plot(x, y.values.ravel() , linestyle='solid', marker=None,
            linewidth=1)
    #%%
    return ax

def plot_freq_per_yr(RV):
    #%%
    dates_RV = RV.RV_bin.index
    all_yrs = np.unique(dates_RV.year)
    freq = pd.DataFrame(data= np.zeros(all_yrs.size), 
                        index = all_yrs, columns=['freq'])
    for i, yr in enumerate(all_yrs):
        oneyr = RV.RV_bin.loc[functions_pp.get_oneyr(dates_RV, yr)]
        freq.loc[yr] = oneyr.sum().values
    plt.figure( figsize=(8,6) )
    plt.bar(freq.index, freq['freq'])
    plt.ylabel('Events p/y', fontdict={'fontsize':14})
    #%%

    
def valid_figures(dict_experiments, expers, models, line_dim='model', group_line_by=None, 
                  met='default', wspace=0.08, col_wrap=None):
    #%%
    '''
    3 dims to plot: [metrics, experiments, stat_models]
    2 can be assigned to row or col, the third will be lines in the same axes.
    '''
    
    dims = ['exper', 'models', 'met']
    col_dim = [s for s in dims if s not in [line_dim, 'met']][0]
    if met == 'default':
        met = ['AUC-ROC', 'AUC-PR', 'BSS', 'Precision', 'Rel. Curve', 'ts']
    
    
    
    if line_dim == 'model':
        lines = models
        cols  = expers
    elif line_dim == 'exper':
        lines = expers
        cols  = models
    assert line_dim in ['model', 'exper'], ('illegal key for line_dim, '
                           'choose \'exper\' or \'model\'')
        
    if len(cols) == 1 and group_line_by is not None:
        group_s = len(group_line_by)
        cols = group_line_by
        lines_grouped = []
        for i in range(0,len(lines),group_s):
            lines_grouped.append(lines[i:i+group_s])
            
        

    grid_data = np.zeros( (2, len(met)), dtype=str)
    grid_data = np.stack( [np.repeat(met, len(cols)), 
                           np.repeat(cols, len(met))])

    
    df = pd.DataFrame(grid_data.T, columns=['met', col_dim])
    if len(cols) != 1 or col_wrap is None:
        g = sns.FacetGrid(df, row='met', col=col_dim, height=3, aspect=1.4,
                      sharex=False,  sharey=False)
        # Only if 1 column is requisted, col_wrap is allowed
    if len(cols) == 1 and col_wrap is not None:
#        cols = met
        g = sns.FacetGrid(df, col='met', height=3, aspect=1.4,
                      sharex=False,  sharey=False, col_wrap=col_wrap)


    
    
    for col, c_label in enumerate(cols):
        
        if col_wrap is None:
            g.axes[0,col].set_title(c_label)
        if len(models) == 1 and group_line_by is not None:
            lines = lines_grouped[col]
        
        
        for row, metric in enumerate(met):
            
            if col_wrap is None:
                ax = g.axes[row,col]    
            else: 
                ax = g.axes[row]    
                
            
            legend = []
            for l, line in enumerate(lines):
                
                if line_dim == 'model':
                    model = line
                    exper = c_label
                    color = nice_colors[l]
                    
                elif line_dim == 'exper':
                    model = c_label
                    exper = line
                    if len(models) == 1 and group_line_by is not None:
                        exper = line
                        model = models[0]
                    color = colors_datasets[l]
                
#                if col_wrap is not None:
#                    metric = c_label # metrics on rows
                    # exper is normally column, now we only have 1 expers
#                    exper = expers[0] 
                
                    
                
                df_valid, RV, y_pred_all = dict_experiments[exper][model]
                tfreq = (y_pred_all.iloc[1].name - y_pred_all.iloc[0].name).days
                lags_i     = list(dict_experiments[exper][model][2].columns.astype(int))
                lags_tf = [l*tfreq for l in lags_i]
                if tfreq != 1:
                    # the last day of the time mean bin is tfreq/2 later then the centerered day
                    lags_tf = [l_tf- int(tfreq/2) if l_tf!=0 else 0 for l_tf in lags_tf]
                
                
                
                if metric in ['AUC-ROC', 'AUC-PR', 'BSS', 'Precision', 'Accuracy']: 
                    df_metric = df_valid.loc[metric]
                    if metric in ['AUC-PR', 'Precision', 'Accuracy']:
                        clim = RV.RV_bin.values[RV.RV_bin==1].size / RV.RV_bin.size
                        if metric == 'Accuracy':
                            import validation as valid
                            # threshold upper 3/4 of above clim
                            threshold = int(100 * (1 - 0.75*clim))
                            df_ran = valid.get_metrics_confusion_matrix(RV, y_pred_all.loc[:,:0], 
                                                    thr=[threshold], n_shuffle=400)
                            clim = df_ran[threshold/100]['fc shuf'].loc[:,'Accuracy'].mean()
                            
                    else:
                        clim = None
                    plot_score_lags(df_metric, metric, color, lags_tf,
                                    clim, cv_lines=False, col=col,
                                    ax=ax)
                if metric == 'Rel. Curve':
                    if l == 0:
                        ax, n_bins = rel_curve_base(RV, lags_tf, col=col, ax=ax)
                    print(l,line)
                    
                    rel_curve(RV, y_pred_all, color, lags_i, n_bins, 
                              mean_lags=True, 
                              ax=ax)
                    
                if metric == 'ts':
                    if l == 0:
                        ax, dates_ts = plot_events(RV, color=nice_colors[-1], n_yrs=6, 
                                         col=col, ax=ax)
                    plot_ts(RV, y_pred_all, dates_ts, color, lag_i=1, ax=ax)
                
                # legend conditions
                same_models = np.logical_and(row==0, col==0)
                grouped_lines = np.logical_and(row==0, group_line_by is not None)
                if same_models or grouped_lines:
                    legend.append(patches.Rectangle((0,0),0.5,0.5,facecolor=color))

                    ax.legend(tuple(legend), lines, 
                          loc = 'lower left', fancybox=True,
                          handletextpad = 0.2, markerscale=0.1,
                          borderaxespad = 0.1,
                          handlelength=1, handleheight=1, prop={'size': 12})
    
    #%%
    g.fig.subplots_adjust(wspace=wspace)
                    
    return g.fig
                
                
                
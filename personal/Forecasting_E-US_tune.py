#!/usr/bin/env python
# coding: utf-8



# In[1]:


#get_ipython().run_line_magic('load_ext', 'autoreload')
#get_ipython().run_line_magic('autoreload', '2')
import os, inspect, sys
import numpy as np
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
RGCPD_dir = os.path.join(main_dir, 'RGCPD')
fc_dir = os.path.join(main_dir, 'forecasting')
df_ana_dir = os.path.join(main_dir, 'df_analysis/df_analysis/')
if fc_dir not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(RGCPD_dir)
    sys.path.append(df_ana_dir)
    sys.path.append(fc_dir)

user_dir = os.path.expanduser('~')
if sys.platform == 'linux':
    import matplotlib as mpl
    mpl.use('Agg')



from class_fc import fcev


# Define statmodel:
logit = ('logit', None)

logitCV = ('logitCV',
          {'Cs':np.logspace(-4,1,10),
          'class_weight':{ 0:1, 1:1},
           'scoring':'brier_score_loss',
           'penalty':'l2',
           'solver':'lbfgs',
           'max_iter':150})


logitCVfs = ('logitCV',
          {'class_weight':{ 0:1, 1:1},
           'scoring':'brier_score_loss',
           'penalty':'l2',
           'solver':'lbfgs',
           'feat_sel':{'model':None}})

GBC_tfs = ('GBC',
          {'max_depth':[1, 2, 3, 4],
           'learning_rate':[1E-2, 5E-3, 1E-3, 5E-4],
           'n_estimators' : [200, 300, 400, 500, 600, 700, 800, 1000],
           'min_samples_split':[.15, .25],
           'max_features':[.2,'sqrt', .5],
           'subsample' : [.3, .4, .5, 0.6],
           'random_state':60,
           'scoringCV':'brier_score_loss',
           'feat_sel':{'model':None} } )

GBC_t = ('GBC', 
         {'max_depth':[1, 2, 3, 4, 5, 6],
           'learning_rate':5E-4,
           'n_estimators' : [500, 750, 1000, 1250, 1500],
           'min_samples_split':.2,
           'max_features':[.15, .2, 'sqrt'],
           'subsample' : [.3, .45],
           'random_state':60,
           # 'n_iter_no_change':20,
           # 'tol':1E-4,
           # 'validation_fraction':.3,
           'scoringCV':'brier_score_loss' } )


GBC = ('GBC',
      {'max_depth':1,
       'learning_rate':.05,
       'n_estimators' : 500,
       'min_samples_split':.25,
       'max_features':.4,
       'subsample' : .45,
       'random_state':60,
       'n_iter_no_change':20,
       'tol':1E-4,
       'validation_fraction':.3,
       'scoringCV':'brier_score_loss'
       } )

# In[6]:
path_data = user_dir + '/surfdrive/McKinRepl/EC_tas_tos_Northern/958dd_ran_strat10_s30/data/EC_16-03-20_15hr_lag_0_958dd.h5'


kwrgs_events = {'event_percentile': 66}

kwrgs_events = kwrgs_events
precur_aggr = 30
use_fold = None
lags_i = np.array([0])
start_end_TVdate = None # ('7-04', '8-22')



# list_of_fc = [fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                     use_fold=use_fold, start_end_TVdate=None,
#                     stat_model=logitCV, 
#                     kwrgs_pp={}, 
#                     dataset=f'{precur_aggr} day means',
#                     keys_d='persistence'),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                     use_fold=use_fold, start_end_TVdate=None,
#                     stat_model=logitCV, 
#                     kwrgs_pp={}, 
#                     dataset=f'{precur_aggr} day means',
#                     keys_d='all'),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=logitCV, 
#                       kwrgs_pp={}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='all',
#                       causal=True),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=logitCV, 
#                       kwrgs_pp={}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='sst+sm+z500'),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=GBC_t, 
#                       kwrgs_pp={'normalize':False}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='persistence'),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=GBC_t, 
#                       kwrgs_pp={'normalize':False}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='all'),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=GBC_t, 
#                       kwrgs_pp={'normalize':False}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='all',
#                       causal=True),
#                 fcev(path_data=path_data, precur_aggr=precur_aggr, 
#                       use_fold=use_fold, start_end_TVdate=None,
#                       stat_model=GBC_t, 
#                       kwrgs_pp={'normalize':False}, 
#                       dataset=f'{precur_aggr} day means',
#                       keys_d='sst+sm+z500')]
                   

list_of_fc = [fcev(path_data=path_data, precur_aggr=precur_aggr, 
                    use_fold=use_fold, start_end_TVdate=None,
                    stat_model=logit, 
                    kwrgs_pp={'normalize':False}, 
                    dataset=f'{precur_aggr} day means',
                    keys_d='all',
                    causal=False)]
              
fc = list_of_fc[0]
#%%
for i, fc in enumerate(list_of_fc):

    fc.get_TV(kwrgs_events=kwrgs_events)
    
    fc.fit_models(lead_max=lags_i, verbosity=1)

    fc.perform_validation(n_boot=500, blocksize='auto', alpha=0.05,
                          threshold_pred=(1.5, 'times_clim'))
    

# In[8]:
store = False
if __name__ == "__main__":
    store = True

import valid_plots as dfplots
import functions_pp
kwrgs = {'wspace':0.25, 'col_wrap':None}
#kwrgs = {'wspace':0.25, 'col_wrap':3, 'threshold_bin':fc.threshold_pred}
met = ['AUC-ROC', 'AUC-PR', 'BSS', 'Rel. Curve', 'Precision']
#met = ['AUC-ROC', 'AUC-PR', 'BSS', 'Rel. Curve']


line_dim = 'exper'


dict_all = dfplots.merge_valid_info(list_of_fc, store=store)
if store:
    dict_all = functions_pp.load_hdf5(fc.filename +'.h5')

fig = dfplots.valid_figures(dict_all, 
                          line_dim=line_dim,
                          group_line_by=None,
                          met=met, **kwrgs)




working_folder, filename = fc._print_sett(list_of_fc=list_of_fc)

f_format = '.pdf'
pathfig_valid = os.path.join(filename + f_format)
fig.savefig(pathfig_valid,
            bbox_inches='tight') # dpi auto 600



#%%

im = 0
il = 1
ifc = 0
f_format = '.pdf'
if os.path.isdir(fc.filename) == False : os.makedirs(fc.filename)
import valid_plots as dfplots
if __name__ == "__main__":
    for ifc, fc in enumerate(list_of_fc):
        for im, m in enumerate([n[0] for n in fc.stat_model_l]):
            for il, l in enumerate(fc.lags_i):
                fc = list_of_fc[ifc]
                m = [n[0] for n in fc.stat_model_l][im]
                l = fc.lags_i[il]
                # visual analysis
                f_name = os.path.join(filename, f'ifc{ifc}_va_l{l}_{m}')
                fig = dfplots.visual_analysis(fc, lag=l, model=m)
                fig.savefig(os.path.join(working_folder, f_name) + f_format, 
                            bbox_inches='tight') # dpi auto 600
                # plot deviance
                if m[:3] == 'GBC':
                    fig = dfplots.plot_deviance(fc, lag=l, model=m)
                    f_name = os.path.join(filename, f'ifc{ifc}_deviance_l{l}')
                    

                    fig.savefig(os.path.join(working_folder, f_name) + f_format,
                                bbox_inches='tight') # dpi auto 600
                    
                    fig = fc.plot_oneway_partial_dependence()
                    f_name = os.path.join(filename, f'ifc{ifc}_partial_depen_l{l}')
                    fig.savefig(os.path.join(working_folder, f_name) + f_format,
                                bbox_inches='tight') # dpi auto 600
                    
                if m[:7] == 'logitCV':
                    fig = fc.plot_logit_regularization(lag_i=l)
                    f_name = os.path.join(filename, f'ifc{ifc}_logitregul_l{l}')
                    fig.savefig(os.path.join(working_folder, f_name) + f_format,
                            bbox_inches='tight') # dpi auto 600
                
            df_importance, fig = fc.plot_feature_importances()
            f_name = os.path.join(filename, f'ifc{ifc}_feat_l{l}_{m}')
            fig.savefig(os.path.join(working_folder, f_name) + f_format, 
                        bbox_inches='tight') # dpi auto 600

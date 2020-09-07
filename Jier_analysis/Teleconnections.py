#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, inspect, sys
import pandas as pd
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
subdates_dir = os.path.join(main_dir, 'RGCPD/')
df_ana_dir = os.path.join(main_dir, 'df_analysis/df_analysis/')

if main_dir not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(subdates_dir)
    sys.path.append(df_ana_dir)
# print(main_dir)
# get_ipython().run_line_magic('load_ext', 'autoreload')
# get_ipython().run_line_magic('autoreload', '2')

from RGCPD import RGCPD
from RGCPD import BivariateMI
import df_ana as sa 
import matplotlib.pyplot as plt


# In[2]:


# define input: list_of_name_path = [('TVname', 'TVpath'), ('prec_name', 'prec_path')]
path_test = os.path.join(main_dir, 'data')
list_of_name_path = [(3, os.path.join(path_test, 'tf5_nc5_dendo_80d77.nc')),
                    ('sst', os.path.join(path_test,'sst_1979-2018_2.5deg_Pacific.nc'))]

# define analysis:
list_for_MI = [BivariateMI(name='sst', func=BivariateMI.corr_map, 
                          kwrgs_func={'alpha':.0001, 'FDR_control':True}, 
                          distance_eps=700, min_area_in_degrees2=5)]

rg = RGCPD(list_of_name_path=list_of_name_path,
           list_for_MI=list_for_MI,
           path_outmain=os.path.join(main_dir,'data'))


# In[3]:


# if TVpath contains the xr.DataArray xrclustered, we can have a look at the spatial regions.
rg.plot_df_clust()


# In[4]:


rg.pp_precursors(detrend=True, anomaly=True, selbox=None)


# ### Post-processing Target Variable

# In[5]:


rg.pp_TV()


# In[7]:


rg.traintest(method='random5')


# In[8]:


rg.calc_corr_maps() 


# In[9]:


rg.plot_maps_corr()


# In[10]:


rg.cluster_list_MI()


# In[11]:


rg.quick_view_labels(median=True) 


# In[12]:


rg.get_ts_prec()

# sys.exit()
# In[13]:


# rg.df_data

from df_ana_class import DFA
df = pd.DataFrame(rg.df_data)
dd = DFA(df)

# df.apply(lambda c :   sa.plot_timeseries(c), axis=0)
# plt.show()
# serie = DF.subset_series(df)

# VS.vis_timeseries(serie, df[df.columns[df.dtypes != bool]])
# VS.vis_dataframe(df)
# print(df.index)
# series = DF.spectrum(df)
# VS.vis_spectrum(title="Test", subtitle=list(df.columns), results=series[0], freqdf=series[1], freq=series[2], idx_=series[3])
# df = DFA(df=rg.df_data)
# df.dataframe(df.df)






# # In[14]:


# rg.PCMCI_df_data()


# # In[15]:


# rg.PCMCI_get_links(alpha_level=.05)


# # In[16]:


# rg.plot_maps_sum()


# # In[17]:


# rg.df_data


# # In[18]:


# rg.df_links


# # In[19]:


# rg.store_df_PCMCI()


# # In[20]:


# rg.PCMCI_get_ParCorr_from_txt()


# # In[21]:


# rg.df_ParCorr_sum


# # In[ ]:





# # In[ ]:




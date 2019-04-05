# -*- coding: utf-8 -*-
import numpy as np
import matplotlib
matplotlib.rcParams['backend'] = "Qt4Agg"
from pylab import *
import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap, shiftgrid, cm
import scipy
import pandas as pd
from statsmodels.sandbox.stats import multicomp
import xarray as xr
import cartopy.crs as ccrs
import itertools
flatten = lambda l: list(itertools.chain.from_iterable(l))
def get_oneyr(datetime):
        return datetime.where(datetime.year==datetime.year[0]).dropna()
from dateutil.relativedelta import relativedelta as date_dt

def extract_data(d, D, ex):	
	"""
	Extracts the array of variable d for indices index_range over the domain box
	d: netcdf elements
	D: the data array
	index_range: a list containing the start and the end index, e.g. [0, time_cycle*n_years]
	"""
	
	
	index_0 = ex['time_range_all'][0]
	index_n = ex['time_range_all'][1]

	if 'latitude' in list(d.variables.keys()):
	  lat = d.variables['latitude'][:]
	else:
	  lat = d.variables['lat'][:]
	if 'longitude' in list(d.variables.keys()):
	  lon = d.variables['longitude'][:]
	else:
	  lon = d.variables['lon'][:]

	if lon.min() < 0: 
	  lon[ lon < 0] = 360 + lon[ lon < 0]


#	time = d.variables['time'][:]
#	unit = d.variables['time'].units
#	u = utime(unit)
#	date = u.num2date(time[:])
	D = D[index_0: index_n, :, :]
	D = D[:,(lat>=ex['la_min']) & (lat<=ex['la_max']),:]
	D = D[:,:,(lon>=ex['lo_min']) & (lon<=ex['lo_max'])]
	
	return D

	
	
def plot_basemap_options(m):

	''' specifies basemap options for basemap m'''
	
	# Basemap options:
	m.drawcoastlines(color='gray', linewidth=0.35)
	#m.drawcountries(color='gray', linewidth=0.2)
	m.drawmapboundary(fill_color='white', color='gray')
	#m.drawmapboundary(color='gray')
	#m.fillcontinents(color='white',lake_color='white')
	m.drawmeridians(np.arange(0, 360, 30), color='lightgray')
	m.drawparallels(np.arange(-90, 90, 30), color='lightgray')


	
	

# This functions merges sets which contain at least on common element. It was taken from:
# http://stackoverflow.com/questions/9110837/python-simple-list-merging-based-on-intersections

def merge_neighbors(lsts):
  sets = [set(lst) for lst in lsts if lst]
  merged = 1
  while merged:
    merged = 0
    results = []
    while sets:
      common, rest = sets[0], sets[1:]
      sets = []
      for x in rest:
        if x.isdisjoint(common):
          sets.append(x)
        else:
          merged = 1
          common |= x
      results.append(common)
    sets = results
  return sets
	
def corr_new(D, di):
	"""
	This function calculates the correlation coefficent r  and the the pvalue p for each grid-point of field D with the response-variable di
	"""
	x = np.ma.zeros(D.shape[1])
	corr_di_D = np.ma.array(data = x, mask =False)	
	sig_di_D = np.array(x)
	
	for i in range(D.shape[1]):
		r, p = scipy.stats.pearsonr(di,D[:,i])
		corr_di_D[i]= r 
		sig_di_D[i]= p
									
	return corr_di_D, sig_di_D

	
def calc_corr_coeffs_new(ncdf, precur_arr, RV, ex):
    #%%
#    v = ncdf ; V = array ; RV.RV_ts = ts of RV, time_range_all = index range of whole ts
    """
    This function calculates the correlation maps for fied V for different lags. Field significance is applied to test for correltion.
    This function uses the following variables (in the ex dictionary)
    ncdf: netcdf element
    prec_arr: array
    box: list of form [la_min, la_max, lo_min, lo_max]
    time_range_all: a list containing the start and the end index, e.g. [0, time_cycle*n_years]
    lag_steps: number of lags
    time_cycle: time cycyle of dataset, =12 for monthly data...
    RV_period: indices that matches the response variable time series
    alpha: significance level

    """
    lag_steps = ex['lag_max'] - ex['lag_min'] +1
    
    assert lag_steps >= 0, ('Maximum lag is larger then minimum lag, not allowed')
		
    d = ncdf
	
    if 'latitude' in list(d.variables.keys()):
        lat = d.variables['latitude'][:]
    else:
        lat = d.variables['lat'][:]
    if 'longitude' in list(d.variables.keys()):
        lon = d.variables['longitude'][:]
    else:
        lon = d.variables['lon'][:]

    if lon.min() < 0: 
        lon[lon < 0] = 360 + lon[lon < 0]
	
    lat_grid = lat[(lat>=ex['la_min']) & (lat<=ex['la_max'])]
    lon_grid = lon[(lon>=ex['lo_min']) & (lon<=ex['lo_max'])]
	
    la = lat_grid.shape[0]
    lo = lon_grid.shape[0]
	
    lons, lats = np.meshgrid(lon_grid,lat_grid)

#    A1 = np.zeros((la,lo))
    z = np.zeros((la*lo,lag_steps))
    Corr_Coeff = np.ma.array(z, mask=z)
	
	


    # reshape
    sat = np.reshape(precur_arr.values, (precur_arr.shape[0],-1))
    
    allkeysncdf = list(d.variables.keys())
    dimensionkeys = ['time', 'lat', 'lon', 'latitude', 'longitude', 'mask', 'levels']
    var = [keync for keync in allkeysncdf if keync not in dimensionkeys][0]  
    print('\ncalculating correlation maps for {}'.format(var))
	
	
    for i in range(lag_steps):

        lag = ex['lag_min'] + i
        
        if ex['time_match_RV'] == True:
            months_indices_lagged = [r - lag for r in ex['RV_period']]
        else:
            # recreate RV_period of precursor to match the correct indices           
            start_prec = pd.Timestamp(RV.RVfullts[ex['RV_period'][0]].time.values) - date_dt(months=lag * ex['tfreq'])
            start_ind = int(np.where(pd.to_datetime(precur_arr.time.values) == start_prec)[0])
            new_n_oneyr  = get_oneyr(pd.to_datetime(precur_arr.time.values)).size
            RV_period = [ (yr*new_n_oneyr)-start_ind for yr in range(1,int(ex['n_yrs'])+1)]
            months_indices_lagged = [r - (lag) for r in RV_period]

            
#            precur_arr.time.values[months_indices_lagged]
            # only winter months 		
        sat_winter = sat[months_indices_lagged]
		
		# correlation map and pvalue at each grid-point:
        corr_di_sat, sig_di_sat = corr_new(sat_winter, RV.RV_ts)
		
        if ex['FDR_control'] == True:
				
			# test for Field significance and mask unsignificant values			
			# FDR control:
            adjusted_pvalues = multicomp.multipletests(sig_di_sat, method='fdr_bh')			
            ad_p = adjusted_pvalues[1]
			
            corr_di_sat.mask[ad_p> ex['alpha']] = True

        else:
            corr_di_sat.mask[sig_di_sat> ex['alpha']] = True
			
			
        Corr_Coeff[:,i] = corr_di_sat[:]
            
    Corr_Coeff = np.ma.array(data = Corr_Coeff[:,:], mask = Corr_Coeff.mask[:,:])
	#%%
    return Corr_Coeff, lat_grid, lon_grid
	

def plot_corr_coeffs(Corr_Coeff, m, lag_min, lat_grid, lon_grid, title='Corr Maps for different time lags', Corr_mask=False):	
	'''
	This function plots the differnt corr coeffs on map m. the variable title must be a string. If mask==True, only significant values are shown.
	'''
	
	print('plotting correlation maps...')
	n_rows = Corr_Coeff.shape[1]
	fig = plt.figure(figsize=(4, 2*n_rows))
	#fig.subplots_adjust(left=None, bottom = None, right=None, top=0.3, wspace=0.1, hspace= 0.1)

	plt.suptitle(title, fontsize = 14)

	if Corr_Coeff.count()==0:
		vmin = -0.99 
		vmax = 0.99
	
	else:
		vmin = Corr_Coeff.min()
		vmax = Corr_Coeff.max()
		
	maxabs = max([np.abs(vmin), vmax]) + 0.01
	levels = np.linspace(- maxabs, maxabs , 13) 
	levels = [round(elem,2) for elem in levels]
	
	#gs1 = gridspec.GridSpec(2, Corr_Coeff.shape[1]/2) 
	for i in range(Corr_Coeff.shape[1]):
		plt.subplot(Corr_Coeff.shape[1], 1, i+1)
		lag = lag_min +i
		plt.title('lag = -' + str(lag), fontsize =12)
		
		
		corr_di_sat = np.ma.array(data = Corr_Coeff[:,i], mask = Corr_Coeff.mask[:,i])
		
		la = lat_grid.shape[0]
		lo = lon_grid.shape[0]
		
		# lons_ext = np.zeros((lon_grid.shape[0]+1))
		# lons_ext[:-1] = lon_grid
		# lons_ext[-1] = 360

		# lons, lats = np.meshgrid(lons_ext,lat_grid)
		lons, lats = np.meshgrid(lon_grid,lat_grid)
		
		
		# reshape for plotting
		corr_di_sat = np.reshape(corr_di_sat, (la, lo))
		corr_di_sat_significance = np.zeros(corr_di_sat.shape)
		corr_di_sat_significance[corr_di_sat.mask==False]=1				
		
		# # make new dimension for plotting
		# B = np.zeros((corr_di_sat.shape[0], corr_di_sat.shape[1]+1))
		# B[:, :-1] = corr_di_sat
		# B[:, -1] = corr_di_sat[:, 0]
	
		# D = np.zeros((corr_di_sat_significance.shape[0], corr_di_sat_significance.shape[1]+1))
		# D[:, :-1] = corr_di_sat_significance
		# D[:, -1] = corr_di_sat_significance[:, 0]	
		

		# if (Corr_mask==True) | (np.sum(corr_di_sat_significance)==0):
		if (Corr_mask==True):
			# plotting otions:
			im = m.contourf(lons,lats, corr_di_sat, vmin = vmin, vmax = vmax, latlon=True, levels = levels, cmap="RdBu_r")
			# m.colorbar(location="bottom")
			plot_basemap_options(m)


		elif (np.sum(corr_di_sat_significance)==0):
			im = m.contourf(lons,lats, corr_di_sat.data, vmin = vmin, vmax = vmax, latlon=True, levels = levels, cmap="RdBu_r")
			# m.colorbar(location="bottom")
			plot_basemap_options(m)
		
		else:				
			
			plot_basemap_options(m)		
			im = m.contourf(lons,lats, corr_di_sat.data, vmin = vmin, vmax = vmax, latlon=True, levels = levels, cmap="RdBu_r")				
			m.contour(lons,lats, corr_di_sat_significance, latlon = True, linewidths=0.2,colors='k')

			#m.colorbar(location="bottom")
			#m.scatter(lons,lats,corr_di_sat_significance,alpha=0.7,latlon=True, color="k")
	
	
	# vertical colorbar
	# cax2 = fig.add_axes([0.92, 0.3, 0.013, 0.4])
	# cb = fig.colorbar(im, cax=cax2, orientation='vertical')
	# cb.outline.set_linewidth(.1)
	# cb.ax.tick_params(labelsize = 7)
	
	
	cax2 = fig.add_axes([0.25, 0.07, 0.5, 0.014])
	cb = fig.colorbar(im, cax=cax2, orientation='horizontal')
	cb.outline.set_linewidth(.1)
	cb.ax.tick_params(labelsize = 7)
	
	#fig.tight_layout(rect=[0, 0.03, 1, 0.93])
	return fig


def define_regions_and_rank_new(Corr_Coeff, lat_grid, lon_grid, ex):
    #%%
    '''
	takes Corr Coeffs and defines regions by strength

	return A: the matrix whichs entries correspond to region. 1 = strongest, 2 = second strongest...
    '''
#    print('extracting features ...\n')

	
	# initialize arrays:
	# A final return array 
    A = np.ma.copy(Corr_Coeff)
#    A = np.ma.zeros(Corr_Coeff.shape)
	#========================================
	# STEP 1: mask nodes which were never significantly correlatated to index (= count=0)
	#========================================
	
	#========================================
	# STEP 2: define neighbors for everey node which passed Step 1
	#========================================

    indices_not_masked = np.where(A.mask==False)[0].tolist()

    lo = lon_grid.shape[0]
    la = lat_grid.shape[0]
	
	# create list of potential neighbors:
    N_pot=[[] for i in range(A.shape[0])]

	#=====================
	# Criteria 1: must bei geographical neighbors:
    n_between = ex['prec_reg_max_d']
	#=====================
    for i in indices_not_masked:
        neighb = []
        def find_neighboors(i, lo):
            n = []	
    
            col_i= i%lo
            row_i = i//lo
    
    		# knoten links oben
            if i==0:	
                n= n+[lo-1, i+1, lo ]
    
    		# knoten rechts oben	
            elif i== lo-1:
                n= n+[i-1, 0, i+lo]
    
    		# knoten links unten
            elif i==(la-1)*lo:
                n= n+ [i+lo-1, i+1, i-lo]
    
    		# knoten rechts unten
            elif i == la*lo-1:
                n= n+ [i-1, i-lo+1, i-lo]
    
    		# erste zeile
            elif i<lo:
                n= n+[i-1, i+1, i+lo]
    	
    		# letzte zeile:
            elif i>la*lo-1:
                n= n+[i-1, i+1, i-lo]
    	
    		# erste spalte
            elif col_i==0:
                n= n+[i+lo-1, i+1, i-lo, i+lo]
    	
    		# letzt spalte
            elif col_i ==lo-1:
                n= n+[i-1, i-lo+1, i-lo, i+lo]
    	
    		# nichts davon
            else:
                n = n+[i-1, i+1, i-lo, i+lo]
            return n
        
        for t in range(n_between+1):
            direct_n = find_neighboors(i, lo)
            if t == 0:
                neighb.append(direct_n)
            if t == 1:
                for n in direct_n:
                    ind_n = find_neighboors(n, lo)
                    neighb.append(ind_n)
        n = list(set(flatten(neighb)))
        if i in n:
            n.remove(i)
        
	
	#=====================
	# Criteria 2: must be all at least once be significanlty correlated 
	#=====================	
        m =[]
        for j in n:
            if j in indices_not_masked:
                m = m+[j]
		
		# now m contains the potential neighbors of gridpoint i

	
	#=====================	
	# Criteria 3: sign must be the same for each step 
	#=====================				
        l=[]
	
        cc_i = A.data[i]
        cc_i_sign = np.sign(cc_i)
		
	
        for k in m:
            cc_k = A.data[k]
            cc_k_sign = np.sign(cc_k)
		

            if cc_i_sign *cc_k_sign == 1:
                l = l +[k]

            else:
                l = l
			
            if len(l)==0:
                l =[]
                A.mask[i]=True	
    			
            elif i not in l: 
                l = l + [i]	
		
		
            N_pot[i]=N_pot[i] + l	



	#========================================	
	# STEP 3: merge overlapping set of neighbors
	#========================================
    Regions = merge_neighbors(N_pot)
	
	#========================================
	# STEP 4: assign a value to each region
	#========================================
	

	# 2) combine 1A+1B 
    B = np.abs(A)
	
	# 3) calculate the area size of each region	
	
    Area =  [[] for i in range(len(Regions))]
	
    for i in range(len(Regions)):
        indices = np.array(list(Regions[i]))
        indices_lat_position = indices//lo
        lat_nodes = lat_grid[indices_lat_position[:]]
        cos_nodes = np.cos(np.deg2rad(lat_nodes))		
		
        area_i = [np.sum(cos_nodes)]
        Area[i]= Area[i]+area_i
	
	#---------------------------------------
	# OPTIONAL: Exclude regions which only consist of less than n nodes
	# 3a)
	#---------------------------------------	
	
    # keep only regions which are larger then the mean size of the regions
    if ex['min_n_gc'] == 'mean':
        n_nodes = int(np.mean([len(r) for r in Regions]))
    else:
        n_nodes = ex['min_n_gc']
    
    R=[]
    Ar=[]
    for i in range(len(Regions)):
        if len(Regions[i])>=n_nodes:
            R.append(Regions[i])
            Ar.append(Area[i])
	
    Regions = R
    Area = Ar	
	
	
	
	# 4) calcualte region value:
	
    C = np.zeros(len(Regions))
	
    Area = np.array(Area)
    for i in range(len(Regions)):
        C[i]=Area[i]*np.mean(B[list(Regions[i])])


	
	
#	 mask out those nodes which didnot fullfill the neighborhood criterias
#    A.mask[A==0] = True	
		
		
	#========================================
	# STEP 5: rank regions by region value
	#========================================
	
	# rank indices of Regions starting with strongest:
    sorted_region_strength = np.argsort(C)[::-1]
	
	# give ranking number
	# 1 = strongest..
	# 2 = second strongest
    
    # create clean array
    Regions_lag_i = np.zeros(A.data.shape)
    for i in range(len(Regions)):
        j = list(sorted_region_strength)[i]
        Regions_lag_i[list(Regions[j])]=i+1
    
    Regions_lag_i = np.array(Regions_lag_i, dtype=int)
    Regions_lag_i = np.ma.masked_where(Regions_lag_i==0, Regions_lag_i)
    #%%
    return Regions_lag_i
	

def calc_actor_ts_and_plot(Corr_Coeff, actbox, ex, lat_grid, lon_grid, var):
    #%%
    """
	Calculates the time-series of the actors based on the correlation coefficients and plots the according regions. 
	Only caluclates regions with significant correlation coefficients
	"""
    if Corr_Coeff.ndim == 1:
        lag_steps = 1
        n_rows = 1
    else:
        lag_steps = Corr_Coeff.shape[1]
        n_rows = Corr_Coeff.shape[1]

	
    la_gph = lat_grid.shape[0]
    lo_gph = lon_grid.shape[0]
    lons_gph, lats_gph = np.meshgrid(lon_grid, lat_grid)

    cos_box_gph = np.cos(np.deg2rad(lats_gph))
    cos_box_gph_array = np.repeat(cos_box_gph[None,:], actbox.shape[0], 0)
    cos_box_gph_array = np.reshape(cos_box_gph_array, (cos_box_gph_array.shape[0], -1))


    Actors_ts_GPH = [[] for i in range(lag_steps)]
	
	#test = [len(a) for a in Actors_ts_GPH]
	#print test


    Number_regions_per_lag = np.zeros(lag_steps)
    x = 0
	# vmax = 50
    for i in range(lag_steps):
		
        if Corr_Coeff.ndim ==1:
            Regions_lag_i = define_regions_and_rank_new(Corr_Coeff, lat_grid, lon_grid, ex)
		
        else:
            Regions_lag_i = define_regions_and_rank_new(Corr_Coeff[:,i], lat_grid, lon_grid, ex)
		
        
        
        if Regions_lag_i.max()> 0:
            n_regions_lag_i = int(Regions_lag_i.max())
            print(('{} regions detected for lag {}, variable {}'.format(n_regions_lag_i, ex['lag_min']+i,var)))
            x_reg = np.max(Regions_lag_i)
			
#            levels = np.arange(x, x + x_reg +1)+.5
            A_r = np.reshape(Regions_lag_i, (la_gph, lo_gph))
            A_r + x
            
            x = A_r.max() 

			# this array will be the time series for each region
            ts_regions_lag_i = np.zeros((actbox.shape[0], n_regions_lag_i))
				
            for j in range(n_regions_lag_i):
                B = np.zeros(Regions_lag_i.shape)
                B[Regions_lag_i == j+1] = 1	
                ts_regions_lag_i[:,j] = np.mean(actbox[:, B == 1] * cos_box_gph_array[:, B == 1], axis =1)

            Actors_ts_GPH[i] = ts_regions_lag_i
		
        else:
            print(('no regions detected for lag ', ex['lag_min'] + i))	
            Actors_ts_GPH[i] = np.array([])
            n_regions_lag_i = 0
		
        Number_regions_per_lag[i] = n_regions_lag_i
		

    if np.sum(Number_regions_per_lag) ==0:
        print('no regions detected at all')
        tsCorr = np.array([])
	
    else:
        print('{} regions detected in total\n'.format(
                        np.sum(Number_regions_per_lag)))
		
		# check for whcih lag the first regions are detected
        d = 0
		
        while (Actors_ts_GPH[d].shape[0]==0) & (d < lag_steps):
            d = d+1
            print(d)
		
		# make one array out of it:
        tsCorr = Actors_ts_GPH[d]
		
        for i in range(d+1, len(Actors_ts_GPH)):
            if Actors_ts_GPH[i].shape[0]>0:		
				
                tsCorr = np.concatenate((tsCorr, Actors_ts_GPH[i]), axis = 1)		
		
			# if Actors_ts_GPH[i].shape[0]==0:
				# print i+1
				
			# else:
				# tsCorr = np.concatenate((tsCorr, Actors_ts_GPH[i]), axis = 1)
    if np.sum(Number_regions_per_lag) != 0:
        assert np.where(np.isnan(tsCorr))[1].size < 0.5*tsCorr[:,0].size, ('more '
                       'then 10% nans found, i.e. {} out of {} datapoints'.format(
                               np.where(np.isnan(tsCorr))[1].size), tsCorr.size)
        while np.where(np.isnan(tsCorr))[1].size != 0:
            nans = np.where(np.isnan(tsCorr))
            print('{} nans were found in timeseries of regions out of {} datapoints'.format(
                    nans[1].size, tsCorr.size))
            tsCorr[nans[0],nans[1]] = tsCorr[nans[0]-1,nans[1]]
            print('taking value of previous timestep')
    #%%
    return tsCorr, Number_regions_per_lag#, fig_GPH
	

	
def print_particular_region(ex, number_region, Corr_Coeff_lag_i, actor, map_proj, title):
#    (number_region, Corr_Coeff_lag_i, latitudes, longitudes, map_proj, title)=(according_number, Corr_precursor[:, :], actor.lat_grid, actor.lon_grid, map_proj, according_fullname) 
    #%%
    # check if only one lag is tested:
    if Corr_Coeff_lag_i.ndim == 1:
        lag_steps = 1

    else:
        lag_steps = Corr_Coeff_lag_i.shape[1]

    latitudes = actor.lat_grid
    longitudes = actor.lon_grid
    
    x = 0
    for i in range(lag_steps):
	
        if Corr_Coeff_lag_i.ndim == 1:
            Regions_lag_i = define_regions_and_rank_new(Corr_Coeff_lag_i, 
                                                        latitudes, longitudes, ex)
		
        else:	
            Regions_lag_i = define_regions_and_rank_new(Corr_Coeff_lag_i[:,i], 
                                                        latitudes, longitudes, ex)
		
        if np.max(Regions_lag_i.data)==0:
            n_regions_lag_i = 0
		
        else:	
            n_regions_lag_i = int(np.max(Regions_lag_i.data))
#            x_reg = np.max(Regions_lag_i)	
#            levels = np.arange(x, x + x_reg +1)+.5

		
            A_r = np.reshape(Regions_lag_i, (latitudes.size, longitudes.size))
            A_r = A_r + x			
            x = A_r.max() 
            print(x)
		
		
        if (x >= number_region) & (x>0):
					
            A_number_region = np.zeros(A_r.shape)
            A_number_region[A_r == number_region]=1
            xr_A_num_reg = xr.DataArray(data=A_number_region, coords=[latitudes, longitudes], 
                                        dims=('latitude','longitude'))
            map_proj = map_proj
            plt.figure(figsize=(6, 4))
            ax = plt.axes(projection=map_proj)
            im = xr_A_num_reg.plot.pcolormesh(ax=ax, cmap=plt.cm.BuPu,
                             transform=ccrs.PlateCarree(), add_colorbar=False)
            plt.colorbar(im, ax=ax , orientation='horizontal')
            ax.coastlines(color='grey', alpha=0.3)
            ax.set_title(title)
            
            break
#%%
    return

	
		
	




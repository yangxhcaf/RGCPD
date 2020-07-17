import os, sys, inspect, warnings
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
main_dir = '/'.join(curr_dir.split('/')[:-1])
sub_dir = os.path.join(main_dir, 'RGCPD/')
if main_dir not in sys.path:
    sys.path.append(main_dir)
    sys.path.append(sub_dir)
import numpy as np 
import statsmodels as st 
import statsmodels.api as sm 
import pandas as pd 
import matplotlib.pyplot as plt 
import itertools as it
from statsmodels.tsa.stattools import adfuller, kpss 
from statsmodels.tsa.arima_process import  arma_generate_sample, ArmaProcess
from pprint import pprint as pp 
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
np.random.seed(12345)
plt.style.use('seaborn')

from statsmodels.tools.sm_exceptions import ConvergenceWarning
warnings.simplefilter('ignore', ConvergenceWarning)

# TODO Look if simulation of more than one realization is needed and if so why, comment it. 
# Above is only needed when we want to test ground truth data scenarios against our target data. 



synthetic = dict()
synthetic['ARrange'] = np.array([.75, -.25])
synthetic['MArange'] = np.array([.65, .35])
synthetic['arparams'] = np.r_[1, -synthetic['ARrange']]
synthetic['maparams'] = np.r_[1, -synthetic['MArange']]
synthetic['nobs'] = 1000
synthetic['startyear'] = '1980m1'

def generate_synthetic_data():
    return arma_generate_sample(synthetic['arparams'],synthetic['maparams'], synthetic['nobs'])

def generate_date_range():
    return sm.tsa.datetools.dates_from_range(synthetic['startyear'], length=synthetic['nobs'])

def generate_combination_lags(end_range=4):
        return list(it.product(range(1,end_range), repeat=2))

def extract_lags_aic_bic_info_synth(y:pd.Series, combos:list):
    # TODO INCLUDE CONSTANT IN  EQUATION IF NEEDED
    print('Starting manually..')
    summaries = []
    aic, bic = 10000000000, 10000000000
    ar_ma_params, aci_info, arma_res, arma_mod = [] , [], None, None

    for i, j in combos:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            try:
                arma_mod = sm.tsa.ARMA(y, order=(i, j))
                arma_res = arma_mod.fit(trend='c', disp=-1)
            except:
                continue
        if arma_res.aic < aic and arma_res.bic < bic: 
            aic = arma_res.aic
            bic = arma_res.bic
            ar_ma_params.append((arma_res.arparams, arma_res.maparams,arma_res.sigma2,(i,j)))
            aci_info.append((aic, bic, (i, j),(arma_res.arroots, arma_res.maroots)))
            summaries.append(arma_res.summary())
    print('Done manually')
    return ar_ma_params, aci_info, summaries


def retrieve_aci_info(aci_info:list):
    print("AIC, BIC, (i, j), ARroots, MAroots", sep='\t')
    pp(aci_info)

def retrieve_ar_ma_info(ar_ma_params:list):
    print("ARparams, MAparams, Sigmas")
    pp(ar_ma_params)

def retrieve_summaries(summaries:list):
    pp(summaries)

def fit_manually_data(y, arparams:np.array, maparams:np.array, nobs:int, startyear:'', end_range:int, synthetics:bool=True):
    combos = generate_combination_lags(end_range=end_range)
    ar_ma_params, aci_info, summaries = None, None, None
    if synthetics:
        synthetic['ARrange'] = arparams
        synthetic['MArange'] = maparams
        synthetic['nobs'] = nobs
        synthetic['startyear'] = startyear
        y_ = generate_synthetic_data() 
        dates  = generate_date_range()
        y_ = pd.Series(y_, index=dates)
        ar_ma_params, aci_info, summaries = extract_lags_aic_bic_info_synth(y=y_, combos=combos)
    else:
        assert isinstance(y, pd.Series), f"Expected pandas Series, {type(y)} given"
        serie = y
        ar_ma_params, aci_info, summaries = extract_lags_aic_bic_info_synth(y=serie, combos=combos)

    return ar_ma_params, aci_info, summaries
    
def fit_automatically_data(y:pd.Series, pmax:int, qmax:int, ic:list=['aic','bic']):
    try:
        print('Starting automatic...')
        aut_model, aut_order = None, []
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            order_model =  sm.tsa.stattools.arma_order_select_ic(y, ic=ic, trend='c', max_ar=pmax, max_ma=qmax)
            if 'aic' in ic:
                aut_model = sm.tsa.ARMA(y, order=order_model.aic_min_order).fit(trend='c', disp=-1)
                aut_order.append((aut_model.aic, aut_model.bic, order_model.aic_min_order))
            if 'bic' in ic:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    aut_model = sm.tsa.ARMA(y, order=order_model.bic_min_order).fit(trend='c', disp=-1)
                aut_order.append((aut_model.aic, aut_model.bic, order_model.bic_min_order))

    except ValueError as err:
        print("Occured errors: ", err)
    print("Done Automatic")
    return aut_order

def determine_order(man_model:list, aut_model_order:list, check_info_score:list=['aic']):

    temp = [man_model[i][:3] for i in range(len(man_model))]
    man_aic = [temp[i][0] for i in range(len(temp))] 
    man_bic = [temp[i][1] for i in range(len(temp))]
    aut_aic, aut_bic, aut_order = aut_model_order[0]

    idx_aic, idx_bic = None, None
    aut_aic_check, aut_bic_check = False, False
    aic_check, bic_check = False, False

    if len(check_info_score) > 0:
        if 'aic' in check_info_score:
            if min(man_aic) <= aut_aic:
                idx_aic = next( (i for i , v in enumerate(temp) if v[0] == min(man_aic)),-1 )
                print("Small AIC mannually ", temp[idx_aic])
                aic_check = True
            elif aut_aic < min(man_aic):
                print("Small AIC automatically ", aut_aic, aut_order)
                aut_aic_check = True
        if 'bic' in check_info_score:
            if min(man_bic) <= aut_bic:
                idx_bic = next( (i for i , v in enumerate(temp) if v[0] == min(man_bic)),-1 )
                print("Small BIC mannually ", temp[idx_bic])
                bic_check = True
            elif aut_bic < min(man_bic):
                print("Small BIC automatically ", aut_bic, aut_order)
                aut_bic_check = True

    if aut_bic_check == True or aut_aic_check == True:
        return aut_order
    if aic_check == True: 
        return temp[idx_aic]
    elif bic_check == True:
        return temp[idx_bic]

def check_stationarity_invertibility(aci_info:list, ar_ma_params:list, check_info_score:list=[],nobs:int=synthetic['nobs'], get_params:bool=False, aic_check:bool=False):
    arma_process = []
    for i in range(len(aci_info)):
        arma_process.append((ar_ma_params[i], ArmaProcess(ar=ar_ma_params[i][:2][0], ma=ar_ma_params[i][:2][1], nobs=nobs)))
        print("Statioarity ", arma_process[i][-1].isstationary, "Invertibility ", arma_process[i][-1].isinvertible, ar_ma_params[i][-1])
        print('AR: ', ar_ma_params[i][0], 'MA: ', ar_ma_params[i][1], 'sigma2: ', ar_ma_params[i][2])

    if len(check_info_score) > 0:
        aic_check, bic_check = aic_check, not aic_check 
        idx_pr = None
        temp = [aci_info[i][:3] for i in range(len(aci_info))] # construct temp list of aic, bic info
        if 'aic' in check_info_score:
            man_aic  =[temp[i][0] for i in range(len(temp))]
            idx_aic = next( (i for i , v in enumerate(temp) if v[0] == min(man_aic)),-1 )
            idx_pr = next((i for i , v in enumerate(arma_process) if v[0][-1] == temp[idx_aic][-1]), -1)
            print('AIC stationarity and Invertibility ', arma_process[idx_pr][:-1][0])
            if get_params == True and aic_check == True:
                return arma_process[idx_pr][:-1][0]

        if 'bic' in check_info_score:
            man_bic = [temp[i][1] for i in range(len(temp))]
            idx_bic = next( (i for i , v in enumerate(temp) if v[0] == min(man_bic)),-1 )
            idx_pr = next((i for i , v in enumerate(arma_process) if v[0][-1] == temp[idx_bic][-1]), -1)
            print('BIC stationarity and Invertibility ', arma_process[idx_pr][:-1][0])

            if get_params == True and bic_check == True:
                return arma_process[idx_pr][:-1][0]   

def display_info_ts(y:pd.Series, figsize=(14, 8), title="", lags=20, save_fig:bool=False):
    assert isinstance(y, pd.Series), f"Expect pandas Series, {type(y)} given"
    serie = y 
    fig = plt.figure(figsize=figsize)
    serie.plot(ax = fig.add_subplot(3, 1, 1), title="$Time \ Series \ "+ title + "$", legend=False)
    sm.graphics.tsa.plot_acf(serie, lags=lags, zero=False, ax = fig.add_subplot(3, 2, 3))
    plt.xticks(np.arange(1, lags + 1, 1.0))

    sm.graphics.tsa.plot_pacf(serie, lags=lags, zero=False, ax = fig.add_subplot(3, 2, 4))
    plt.xticks(np.arange(1, lags + 1, 1.0))

    sm.qqplot(serie, line='s', ax = fig.add_subplot(3, 2, 5))
    fig.add_subplot(326).hist(serie, bins= 40, density=True)
    plt.tight_layout()
    if save_fig == True:
        pass
    plt.show()

def display_pierce_LJbox(y:pd.Series, dates:pd.DatetimeIndex, figsize=(14, 8), title="", lags=20, save_fig:bool=False):
    assert isinstance(y, pd.Series), f"Expect pandas Series, {type(y)} given"

    y.index = dates + pd.Timedelta(1, unit=dates.freqstr)
    acor_ljungbox = list(sm.stats.diagnostic.acorr_ljungbox(y, lags=lags, boxpierce=True))

    plt.plot(range(1, len(acor_ljungbox[0]) + 1), acor_ljungbox[1], 'bo', label= 'Ljung-Box values')
    plt.plot(range(1, len(acor_ljungbox[0]) + 1), acor_ljungbox[3], 'go', label= 'Box-Pierce values')
    plt.xticks(np.arange(1, len(acor_ljungbox[0]) + 1, 1.0))
    plt.axhline(y = 0.05, color = 'red', label= "$5 \%  critical value$")
    plt.title("$Time\ Serie\ " + title + " $")
    plt.legend()
    if save_fig == True:
        pass
    plt.show()
    column_ind = ["Ljung-Box: X-squared", 'Ljung-Box: p-value', 'Box-Pierce: X-squared', 'Box-Pierce: p-value']
    return pd.DataFrame(acor_ljungbox, index=column_ind, columns= range(1, len(acor_ljungbox[0]) + 1))

def display_poly_data_arma(simul_data:np.array, ar:list, ma:list, order:tuple, save_fig:bool=False):
    l = ''
    if order[0] >= order[1]:
        for i in range(order[0]):
            try:
                l +=str(round(ar[i], 2))+'Y_{t-'+f'{i}'+'}' + str(round(ma[i], 2)) +'\\epsilon_{t-' +f'{i}'+'}'
            except:
                l +=str(round(ar[i], 2))+'Y_{t-'+f'{i}'+'}' + str(round(ma[i-1], 2)) +'\\epsilon_{t-'+f'{i}'+'}'
    else:
        for i in range(order[1]):
            try:
                l +=str(round(ar[i-1], 2))+'Y_{t-' +f'{i}'+'}' + str(round(ma[i], 2)) +'\\epsilon_{t-' +f'{i}'+'}'
            except:
                pass 
    l +='+\\epsilon_{t}'
    plt.figure(figsize=(14, 8))
    plt.plot(simul_data, label='ARMA='+'$'+l+'$')
    # plt.plot(data['values'].values, label='Precursor data')
    plt.xlim(0.01, len(simul_data))
    plt.ylim(-0.5, 0.5)
    plt.title('Chosen fitted model params with original data')
    plt.legend()
    if save_fig == True:
        pass
    plt.show()

def display_poly_data_ar(simul_data:np.array, ar:list, signal, save_fig:bool=False):
    _dates = pd.DatetimeIndex(signal.index.levels[1], freq='infer')
    l = ''
    for i in range(len(ar[:2])):
        l +=str(round(ar[i], 2))+'Y_{t-'+f'{i}'+'}' 

    l +='+\\epsilon_{t}'
    plt.figure(figsize=(14, 8), dpi=120)
    plt.plot(_dates, simul_data, label='AR(2)= '+'$'+l+'$')
    plt.plot(_dates, signal['values'].values, '-k', label='Precursor data')
    plt.title('Chosen fitted model params with original data')
    plt.xlabel('Dates')
    plt.ylabel('Variance ins temperature')
    plt.legend()
    if save_fig == True:
        plt.savefig('Fitted/AR/AR2Fit on prec.pdf', dpi=120)
        plt.savefig('Fitted/AR/AR2Fit on prec.png', dpi=120)
    plt.show()

def evaluate_synthetic_data(display:bool=False):
    # Synthetic data
    dates = generate_date_range()
    dates = pd.DatetimeIndex(dates, freq='infer')
    y = generate_synthetic_data()
    y = pd.Series(y, index=dates)

    ar_ma_params, aci_info, summaries = fit_manually_data(y=None, arparams=np.array([.75, -.25]), maparams=np.array([.65, .35]), nobs=synthetic['nobs'], startyear=synthetic['startyear'], end_range=4)
    aut_model, aut_order = fit_automatically_data(y=y, pmax=4, qmax=4, ic=['bic'])

    order = determine_order(aci_info, aut_order)
    check_stationarity_invertibility(aci_info, ar_ma_params)
    model = sm.tsa.ARMA(y, order=order[-1]).fit(trend='c', disp=-1)

    if display == True:
        display_info_ts(pd.Series(y), title='Synthetic generated')
        display_pierce_LJbox(model.resid, dates=dates, title='Synthetic generated')

def evaluate_data(signal, display:bool=False, aic_check:bool=False, debug:bool=False):
    
    ar_ma_params, aci_info, summaries = fit_manually_data(signal['values'], arparams=np.array([.75, -.25]), maparams=np.array([.65, .35]), nobs=synthetic['nobs'], startyear=signal.index[0][1], end_range=4,synthetics=False)
    ar, ma, sigma, order = check_stationarity_invertibility(aci_info, ar_ma_params,check_info_score=['aic'] ,nobs=len(signal), get_params=True,aic_check=aic_check)

    if debug == True:
        pp(summaries)
      
        # print(aci_info[0], len(aci_info), len(aci_info[0]))
        # aut_order = fit_automatically_data(y=signal['values'], pmax=4, qmax=4, ic=['aic'])
        # pp(aut_order)
        # determine_order(aci_info, aut_model_order=aut_order,check_info_score=['aic'])

    if display == True:
        # TODO FIND WAY TO CHECK FOR MULTIPLE FOLDS OF MULTIINDEX AND CREATE MUTLIPLE ARIMA MODELS
        temp_dates = pd.DatetimeIndex(signal.index.levels[1], freq='infer')
        temp_m = pd.DataFrame(data=signal['values'].values, index=temp_dates)
        model = sm.tsa.ARMA(temp_m, order=order[-1]).fit(trend='c', disp=-1)
        display_info_ts(model.resid, title='Fitted  RGCPD precursor')
        display_pierce_LJbox(model.resid, dates=temp_dates, title='Fitted RGCPD precursor')
        display_info_ts(signal['values'], title='OriginalPrecursor')
        display_pierce_LJbox(signal['values'], dates=temp_dates, title='OriginalPrecursor')

    return ar, ma, sigma, order

def create_polynomial_fit_arma(ar:list, ma:list, sigma:float, data:pd.Series):
    # BETTER FIT ADD CONSTANT TO HAVE BETTER REPRESENTATION OF THE SIGNAL
    N =  len(data)
    epsilon = np.random.normal(loc=0, scale=sigma, size=N)
    simul_data = np.zeros(N)
    simul_data[0] = epsilon[0]
    simul_data[1] =  ar[0] * simul_data[0] + epsilon[1] + ma[0] * epsilon[0]
    for i in range(2, N):
        simul_data[i] = ar[0] * simul_data[ i - 1] + ar[1] * simul_data[i  - 2] + epsilon[i] + ma[0] * epsilon[i - 1] + ma[1] * epsilon[i - 2]
    
    return simul_data

def create_polynomial_fit_ar(ar:list, sigma:float, data:pd.Series, const:int):

    N =  len(data)
    epsilon = np.random.normal(loc=0, scale=sigma, size=N)
    simul_data = np.zeros(N)
    simul_data[0] = const + epsilon[0]
    simul_data[1] =  const + ar[0] * simul_data[0] + epsilon[1]
    simul_data[2] = const + ar[1] * simul_data[1] + epsilon[2] 
    for i in range(2, N):
        simul_data[i] = const + ar[0] * simul_data[i -1] + ar[1]*simul_data[i - 2]+  epsilon[i]

    return simul_data

def stationarity_test(serie, regression='c', debug=False):
    # ADF Test
    results = adfuller(serie, autolag='AIC')
    if debug == True:
        print(f'ADF Statistic: {results[0]}')
        print(f'p-value: {results[1]}')
        print('Critial Values:')
        for key, value in results[4].items():
            print(f'   {key}, {value}')
    print(f'Result: The series is {"NOT " if results[1] > 0.05 else ""}stationary')
    adf = False if results[1] > 0.05 else True

    # KPSS Test
    result = kpss(serie, regression=regression, lags='auto')
    if debug == True:
        print('\nKPSS Statistic: %f' % result[0])
        print('p-value: %f' % result[1])
        print('Critial Values:')
        for key, value in result[3].items():
            print(f'   {key}, {value}')
    print(f'Result: The series is {"NOT " if result[1] < 0.05 else ""}stationary')
    kps = False if result[1] < 0.05 else True
    return adf and kps

if __name__ == "__main__":
    current_analysis_path = os.path.join(main_dir, 'Jier_analysis')
    # Synthetic data is to play and understand sampling process
    # evaluate_synthetic_data()
    target = pd.read_csv(os.path.join(current_analysis_path, 'target.csv'), engine='python', index_col=[0,1])
    first_sst = pd.read_csv(os.path.join(current_analysis_path, 'first_sst_prec.csv'), engine='python', index_col=[0, 1])
    second_sst = pd.read_csv(os.path.join(current_analysis_path, 'second_sst_prec.csv'), engine='python', index_col=[0, 1])
    var = np.var(first_sst['values'].values)
    stat_test = stationarity_test(second_sst['values'].values, regression='ct')
    # fig, ax = plt.subplots(3, 1, figsize=(16, 8), dpi=90)
    # with pd.plotting.plot_params.use('x_compat', True):
    #     target.plot(title='target',  ax=ax[0])
    #     first_sst.plot(title='prec1',  ax=ax[1])
    #     second_sst.plot(title='prec2', ax=ax[2])
    #     plt.tight_layout(h_pad=1.5)
    #     plt.show()

 
    if stat_test == True:
        # CHANGING FROM ARMA TO AR IS CREATE DISSAPEARING AR PROCESS THE SAME AS WHITENOISE, ONLY USE ARMA TO CHECK VARIABILITY OF PROCESS
        evaluate_data(signal=first_sst, display=False, aic_check=True)
        
        # UNNECESSARY
        # arr = st.tsa.arima_process.arma2ar(ar, ma, lags=len(first_sst))
        # const = (1 + arr.sum())/len(arr)
        
        marr = st.tsa.ar_model.AR(first_sst['values']).fit(ic='aic' ,method='mle', maxiter=len(first_sst), disp=0)
        const = marr.params[0]
        arr = marr.params[1:]

        # polyARMA = create_polynomial_fit_arma(ar=ar, ma=ma,sigma=sigma, data=first_sst)
        polyAR = create_polynomial_fit_ar(ar=arr, sigma=var, data=first_sst, const=const)
        
        # first_sst.plot(label='original')
        # # marr.fittedvalues.plot(label='Fitted')
        # plt.legend(loc=0)
        # plt.show()
        # display_poly_data_arma(simul_data=polyARMA, ar=ar, ma=ma, order=order)
        display_poly_data_ar(simul_data=polyAR,signal=first_sst, ar=arr)


    
    




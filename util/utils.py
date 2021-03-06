"""
General python utility functions
"""
import pandas as pd
import pytz as tz
import matplotlib.pyplot as plt

# used by convert_tz func.
TZ_Dict =      {'SG':      tz.timezone('Singapore'),
                'CN':      tz.timezone('Singapore'),
                'US':      tz.timezone('US/Eastern'),
                'UK':      tz.timezone('Europe/London'),
                'Europe':  tz.timezone('Europe/Berlin'),
                'JP':      tz.timezone('Asia/Tokyo')
                }


def get_daily_vol(inputdf, lookback=100, numday=1):
    """
    From AFML books, for each time step, firstly compute the return based on the given numday. Then, apply a span of lookback days to an expoentially weighted moving
    average. It can be used to compute therholds for profit taking and stop loss limites
    :args
    inputdf: it is the input dataframe with the columns:
                1. index:   datetime in pd.datetime format
                2. columns: at least close
    lookback: the time interval to compute the ewm volaitilty
    numday:   1

    :return:
    seris of daily volatility value
    """
    closeser = inputdf.close
    df0 = closeser.index.searchsorted(closeser.index - pd.Timedelta(days=numday))
    df0 = df0[df0 > 0]
    df0 = (pd.Series(closeser.index[df0 - 1], index=closeser.index[closeser.shape[0] - df0.shape[0]:]))
    df0 = closeser.loc[df0.index] / closeser.loc[df0.values].values - 1  # daily returns
    df0 = df0.ewm(span=lookback).std()
    outputdf  = df0.to_frame(name='vol')
    outputdf.dropna(inplace=True)
    return outputdf

def sample_df(inputdf, freq='1D'):
    """
    the function that sample the dataframe based on the input sampling
    frequency. S, T, H, D, M denotes second, minute, hour, day and month

    :args
    inputdf: it is the input dataframe with the columns:
                1. index:   datetime in pd.datetime format
                2. columns: high, open, low, close, volume(potential)
    freq: the sampling frequency, which can be '1D', '5m' and so on

    :return
    the dataframe that is resampled based on freq
    """
    dfoutput           = pd.DataFrame()
    dfoutput['open']   = inputdf.open.resample(freq).first()
    dfoutput['close']  = inputdf.close.resample(freq).last()
    dfoutput['low']    = inputdf.low.resample(freq).min()
    dfoutput['high']   = inputdf.high.resample(freq).max()
    if 'volume' in inputdf.columns:
        dfoutput['volume'] = inputdf.volume.resample(freq).sum()
    dfoutput.sort_index(inplace=True)
    dfoutput.dropna(inplace=True)
    return dfoutput

def convert_tz(inputdf, src='SG', tar='US'):
    """
    Convert the timezone of datatime index.
    Supported regions: SG, US, CN, UK, Europe, JP


    :args
    inputdf: it is the input dataframe with the columns:
                1. index:   datetime in pd.datetime format
    src: the abbreviation of source time zone
    tar: the abbreviation of target time zone

    :return
    the dataframe with the new time zone
    """
    output_df = inputdf.copy()
    output_df.index = output_df.index.tz_localize(TZ_Dict[src])  \
                               .tz_convert(TZ_Dict[tar])  \
                               .tz_localize(None)
    return output_df

def filter_df_time(inputdf,
                   time_range=[('09:30', '15:59')]):
    """
    Filter the inputdf based on time and hours.

    :args
    inputdf: it is the input dataframe with the columns:
                1. index:   datetime in pd.datetime format
    time_range: a list of tuple (st, et)
                each time is in %h:%m formats
                the points on st and et will be sampled

    :return
    subdataframe
    """
    outputdf = inputdf.copy()
    all_df = []
    for sub_range in time_range:
        st, et = sub_range[0], sub_range[1]
        subdf = outputdf.between_time(st, et)
        all_df.append(subdf)
    outputdf = pd.concat(all_df)
    outputdf.sort_index(inplace=True)
    return outputdf


def sample_pnl(inputdf, freq='1D', cum_mode=True):
    """
    the function that sample the pnl dataframe based on the input sampling
    frequency. S, T, H, D, M denotes second, minute, hour, day and month

    :args
    inputdf: it is the input pnl dataframe:
                1. index:   datetime in pd.datetime format
                2. columns: stat_symbols
    freq:     the sampling frequency, which can be '1D', '5m' and so on
    cum_mode: binary variable, the inputdf contain the cum return if True else normal return

    :return
    the dataframe that is resampled based on freq, which is the normal return
    """
    dfoutput           = pd.DataFrame()
    for colname in inputdf.columns:
        if cum_mode:
            dfoutput[colname] = inputdf[colname].resample(freq).last()  \
                                - inputdf[colname].resample(freq).first()
        else:
            dfoutput[colname] = inputdf[colname].resample(freq).sum()
    dfoutput.sort_index(inplace=True)
    dfoutput.dropna(inplace=True)
    return dfoutput


def detect_duration(inputdf, used_col='rt', num_month=1):
    """
    the function that detect which duration that the model performs best and worst

    :args
    inputdf: it is the daily input dataframe pnl dataframe:
                1. index:   datetime in pd.datetime format
                2. columns: name is used_col, which is return instead of cum return
    num_moth: how long will the duration to be checked.

    :return
    the dataframe that is resampled based on freq, which is the normal return
    """
    # trading days in months is set to be 21
    num_days = num_month * 21
    rt_array  = inputdf['{}'.format(used_col)].values
    if rt_array.shape[0] < num_days:
        print('data length is not enough')
        return None
    else:
        max_sum     = sum(rt_array[0:num_days])
        min_sum     = sum(rt_array[0:num_days])
        current_sum = sum(rt_array[0:num_days])
        profit_idx  = num_days - 1
        loss_idx    = num_days - 1
        for idx_left in range(num_days, rt_array.shape[0]):
            current_sum = current_sum - rt_array[idx_left-num_days] + rt_array[idx_left]
            if current_sum > max_sum:
                profit_idx = idx_left
                max_sum = current_sum
            if current_sum < min_sum:
                loss_idx = idx_left
                min_sum = current_sum
        return {'profit': [inputdf.index[profit_idx-num_days+1], inputdf.index[profit_idx]],
                'loss':   [inputdf.index[loss_idx-num_days+1], inputdf.index[loss_idx]]}


def bs_plot(inputdf, used_col=['open', 'bs'], file_name='test', folder_name=""):
    """
    visualze the buy sell points

    :args
    inputdf: it is the input dataframe bs dataframe:
                1. has the buy sell column
                2. has the price column
    used_col: two columns will be used
    file_name: the figure names

    :return
    save the figure
    """
    start_time = inputdf.index.date[0]
    end_time   = inputdf.index.date[-1]
    idx_long = []
    idx_short= []
    trade_signal = inputdf['{}'.format(used_col[1])].tolist()
    closex       = inputdf['{}'.format(used_col[0])].tolist()
    for idx, ele in enumerate(trade_signal):
        if ele == 1:
            idx_long.append(idx)
        elif ele == -1:
            idx_short.append(idx)
    fig = plt.figure()
    ax  = fig.add_subplot(1, 1, 1)
    for longidx, ele in enumerate(idx_long):
        if ele + 1 < len(closex):
            ax.axvspan(ele, ele+1, alpha=0.5, color='red')
            if longidx == 0:
                ax.plot(ele, closex[ele], marker='x', color='black')
            else:
                if (ele -1) != idx_long[longidx-1]:
                    ax.plot(ele, closex[ele],marker='x', color='black')

    for shortidx, ele in enumerate(idx_short):
        if ele + 1 < len(closex):
            ax.axvspan(ele, ele+1, alpha=0.5, color='green')
            if shortidx == 0:
                ax.plot(ele, closex[ele], marker='x', color='black')
            else:
                if (ele -1) != idx_short[shortidx-1]:
                    ax.plot(ele, closex[ele],marker='x', color='black')
    ax.legend(['short is green, long is red\nfrom {} to {}'.format(start_time, end_time)])
    ax.plot(range(len(closex)), closex)
    if folder_name != "":
        plt.savefig(folder_name + 'bspoint_{}.png'.format(file_name))
    else:
        plt.savefig('bspoint_{}.png'.format(file_name))


def combine_pnls(dfpnl, weights=None):
    """

    :args
    dfpnllist:
    a list of dataframe that each dataframe has the datetime as the index
    and the column "pnl" contain all the value.

    used_col: two columns will be used
    file_name: the figure names

    :return
    return the final dataframe
    """
    if weights == None:
        weights = [1.0/len(dfpnl)] * len(dfpnl)
    for idx in range(len(dfpnl)):
        dfpnl[idx]['pnl'] = dfpnl[idx]['pnl']*weights[idx]
    finaldf = dfpnl[0].copy()
    for idx in range(2, len(dfpnl)):
        finaldf = finaldf.merge(dfpnl[idx], how='outer', on='datetime')
    finaldf.sort_index(inplace=True)
    finaldf.fillna(value=0, inplace=True)
    finaldf['pnl'] = finaldf.sum(axis = 1)
    return finaldf[['pnl']]

import pandas as pd
import numpy as np
import streamlit as st
from io import StringIO
import requests
from dtaidistance import dtw
import plotly.graph_objects as go
from datetime import datetime
import math
st.set_option('deprecation.showPyplotGlobalUse', False)

SECRET_KEY = ''

def calculate_date_distance(dt, date_str1, date_str2):
    """
    Calculate the absolute distance in days between two dates provided as strings
    @param date_str1: a string representing the start date in the format specified by date_format
    @param date_str2: a string representing the end date in the format specified by date_format
    @return: The absolute distance in days between the two dates
    """
    date_distance = len(dt.loc[date_str1: date_str2])
    return date_distance

def sigmoid(x):
    """
    Compute the sigmoid function
    @param x: Input value
    @return: Output value between 0 and 1
    """
    return 1 / (1 + math.exp(-x))

def compute_distance(dt, users_target, users_compare, user_distance):
    """
    Compute a distance matrix using Dynamic Time Warping between a target and a comparison time series
    @param dt: dataFrame containing time series data indexed by dates
    @param users_target: list containing two strings representing the start and end dates of the target time series
    @param users_compare: list containing two strings representing the start and end dates of the comparison time series
    @return matrix: a dictionary representing the distance matrix.
    """
    matrix = {}
    target_data = dt.loc[users_target[0]: users_target[1]]
    target_values = np.array(target_data.values).reshape(-1)
    target_values -= target_values[0]
    compare_data = dt.loc[users_compare[0]: users_compare[1]]
    for i in range(len(compare_data) - user_distance + 1):
        sliced_data = compare_data.iloc[i: i + user_distance, 0]
        compare_values = np.array(sliced_data).reshape(-1)
        compare_values -= compare_values[0]
        dtw_distance = dtw.distance_fast(target_values, compare_values)
        pcorr_coef = np.corrcoef(target_values, compare_values)[0, 1]
        score = abs(pcorr_coef) / (dtw_distance + 1e-10)
        matrix[sliced_data.index[0].strftime("%Y-%m-%d")] = score
    return matrix

def dates_score(dt, date_score_dict, user_distance):
    """
    Extract minimum dates, corresponding dates, and values from a similarity dictionary
    @param date_score_dict: a dictionary containing similarity values for different dates
    @return result: a list of tuples containing minimum dates, corresponding dates, and values
    """
    result = []
    for from_date in date_score_dict:
        score = date_score_dict[from_date]
        started_data = dt.loc[from_date:][:user_distance]
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        to_date = started_data.index[-1]
        result.append((from_date, to_date, score))
    return result

def have_overlap(range1, range2):
    """
    Check if two ranges overlap
    @param range1: a tuple representing the first range, consisting of start, end, and any additional data
    @param range2: a tuple representing the second range, consisting of start, end, and any additional data
    @return: True if the ranges overlap, False otherwise
    """
    start1, end1, _ = range1
    start2, end2, _ = range2
    return start1 <= end2 and start2 <= end1

def filter_overlaps(ranges):
    """
    Filter out overlapping ranges from a list of ranges
    @param ranges: a list of tuples representing ranges, each tuple consisting of start, end, and any additional data
    @return: a list of non-overlapping ranges
    """
    non_overlapping = [ranges[0]]
    for r1 in ranges[1:]:
        overlap = False
        for r2 in non_overlapping:
            if have_overlap(r1, r2):
                overlap = True
                break
        if not overlap:
            non_overlapping.append(r1)
    return non_overlapping

def normalize_df(df):
    """
    Normalize the values of a pandas DataFrame using z-score normalization.
    @param df: the DataFrame to be normalized
    @return df_normalized: the normalized DataFrame
    """
    df_normalized = (df - df.mean()) / df.std()
    return df_normalized

def data_select(selected_data):
    file_path = "chartHtml/assets/data/prototype.csv"
    data = pd.read_csv(file_path, index_col=0)
    if isinstance(selected_data, list):
        data = data[selected_data]
    else:
        data = data[[selected_data]]
    data = data.dropna()
    return data

def n_steps_ahead(sample_data, values_list, n_steps = 0, N = 5):
    changes = []
    for _, (_, end_date, _) in enumerate(values_list[:N], 1):
        sliced_data = sample_data.loc[end_date:].iloc[:n_steps]
        sliced_data.reset_index(drop = True, inplace = True)
        change = sliced_data.iloc[-1] - sliced_data.iloc[0]
        changes.append(change[0])
    df = pd.DataFrame(changes)
    df = df.T
    df.columns = [f'Graph {i}' for i in range(1, len(df.columns) + 1)]
    df.index = ['Change']
    st.table(df)

def create_figure(sample_data, target_date, selected_data, values_list, subtract=False, n_steps = 0, N = 5):
    """
    Create a Plotly figure with optional subtraction operation.
    @param sample_data: DataFrame containing sample data
    @param target_date: list containing start and end dates for the target data
    @param selected_data: column name of the selected data series
    @param values_list: list of tuples containing start and end dates for other data series
    @param title: title of the Plotly figure
    @param subtract: flag to perform subtraction operation (default: False)
    @param n_steps: n-step ahead (in days)
    @return fig: Plotly figure object
    """
    WIDTH, HEIGHT = 800, 600

    fig = go.Figure()

    if n_steps > 0:
        get_length = len(sample_data.loc[target_date[0]: target_date[1]])
        target_data = sample_data[target_date[0]:][: get_length + n_steps]
        target_data.reset_index(drop=True, inplace=True)
        fig.add_vline(x=get_length, line_dash="dash", line_color="black", line_width=1.5)
    else:
        target_data = sample_data.loc[target_date[0]: target_date[1]]
        target_data.reset_index(drop=True, inplace=True)

    if subtract:
        target_trace = target_data[selected_data] - target_data[selected_data].iloc[0]
    else:
        target_trace = target_data[selected_data]
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print(target_data[selected_data])        
    print(target_trace)

    fig.add_trace(go.Scatter(x=target_data.index, y=target_trace, mode='lines', name=f"Target: {target_date[0]} to {target_date[1]}"))
    
    for i, (start_date, end_date, score) in enumerate(values_list[:N], 1):
        if n_steps > 0:
            get_length = len(sample_data.loc[start_date:end_date]) 
            sliced_data = sample_data[start_date:][:get_length + n_steps]
            sliced_data.reset_index(drop=True, inplace=True)
            fig.add_vline(x=get_length, line_dash="dash", line_color="black", line_width=1.5)
        else:
            sliced_data = sample_data.loc[start_date:end_date]
            sliced_data.reset_index(drop=True, inplace=True)

        if subtract:
            sliced_trace = sliced_data[selected_data] - sliced_data[selected_data].iloc[0]
        else:
            sliced_trace = sliced_data[selected_data]
        fig.add_trace(go.Scatter(x=sliced_data.index, y=sliced_trace, mode='lines', name=f'Graph {i}: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'))
        # fig.add_trace(go.Scatter(x=sliced_data.index, y=sliced_trace, mode='lines', name=f'Graph {i}: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")} ({round(score, 7)})'))

    fig.update_layout(
        width=WIDTH,
        height=HEIGHT,
        xaxis=dict(showline=True, linewidth=1, linecolor='black', showgrid=True, gridwidth=1, gridcolor='gray'),
        yaxis=dict(showline=True, linewidth=1, linecolor='black', showgrid=True, gridwidth=1, gridcolor='gray'),
    )
    fig.update_xaxes(showticklabels=False)
    return fig


def main():
    st.sidebar.title('단일 유사기간 분석툴')
    selected_data = st.sidebar.selectbox(
            'Time Series Data:', 
            ('GT2 Govt', 'GT5 Govt', 'GT10 Govt', 'GT30 Govt', 'USYC2Y10 Index', 'USYC5Y30 Index', 'USYC1030 Index',
            'USGGBE10 Index', 'GTII10 Govt', 'GTDEM2Y Govt', 'GTDEM5Y Govt', 'GTDEM10Y Govt', 'DEYC2Y10 Index',
            'DEYC5Y30 Index', 'DEGGBE10 Index', 'GTDEMII10Y Govt', 'GTESP10Y Govt', 'GTITL10Y Govt', 'GTGBP10Y Govt',
            'GTCAD10Y Govt', 'GTAUD10Y Govt', 'GTJPY10Y Govt', 'CCSWNI5 BGN Curncy', 'IRSWNI5 BGN Curncy', 'ODF29 Comdty',
            'MPSW5E BGN Curncy', 'GVSK3YR Index', 'GVSK10YR Index', 'DXY Index', 'KRW Curncy', 'EUR Curncy', 'JPY Curncy',
            'CNH Curncy', 'BRL Curncy', 'INR Curncy', 'MXN Curncy', 'SPX Index', 'CCMP Index', 'DAX Index', 'BCOM Index',
            'XAU Curncy', 'USCRWTIC Index', 'TSFR3M Index', 'USGG3M Index', 'US0003M Index', 'UREPTA30 Index', 'LQD US Equity',
            'HYG US Equity', 'CDX IG CDSI GEN 5Y Corp', 'CDX HY CDSI GEN 5Y SPRD Corp', 'EMLC US Equity', 'EMB US Equity',
            'VIX Index', 'MOVE Index', '.VIXVXN Index', 'GFSIFLOW Index', 'JLGPUSPH Index', 'JLGPEUPH Index', 'MRIEM Index',
            'ACMTP10 Index', 'FWISUS55 Index', 'ILM3NAVG Index', 'ECRPUS 1Y Index', 'CESIUSD Index', 'CESIUSH Index', 'CESIUSS Index',
            'CESIEUR Index', 'CESIEUH Index', 'CESIEUS Index', 'CESIEM Index', 'CESIEMXP Index', 'CESIEMFW Index'
            )
                                        )
    
    if selected_data is not None:
        original_data = data_select(selected_data)
        original_data.index = pd.to_datetime(original_data.index)
        original_data = original_data.sort_index(ascending=True)

        sample_data = normalize_df(original_data)
        sample_data.index = pd.to_datetime(sample_data.index)
        sample_data = sample_data.sort_index(ascending=True)
        target_date = st.sidebar.date_input(
            "Target Date Range",
            (datetime(2023, 11, 1), datetime(2024, 1, 1)),
            format="YYYY/MM/DD"
        )
        
        target_date = [date.strftime("%Y-%m-%d") for date in target_date]
        user_target_distance = calculate_date_distance(sample_data, target_date[0], target_date[1])
        
        print("*****************************")
        print(target_date)
        

        # max_year, max_month, max_day = sample_data.index[-1].year, sample_data.index[-1].month, sample_data.index[-1].day
        min_year, min_month, min_day = sample_data.index[0].year, sample_data.index[0].month, sample_data.index[0].day

        compare_date = st.sidebar.date_input(
            "Date Range for Analysis (* Set To Auto Min Date)",
            (datetime(min_year, min_month, min_day), datetime(2023, 9, 30)),
            format="YYYY/MM/DD"
        )
        compare_date = [date.strftime("%Y-%m-%d") for date in compare_date]

        print(compare_date)
        nsteps = st.sidebar.slider('N-Steps Ahead (in days)', min_value=0, max_value=100, value=0, step=10)

        if st.sidebar.button('Generate'):
            N = 5
            similarity_score = compute_distance(sample_data, target_date, compare_date, user_target_distance)
            dates_score_list = dates_score(sample_data, similarity_score, user_target_distance)
            sorted_dates_score_list = sorted(dates_score_list, key=lambda x: x[2], reverse = True)
            filtered_dates = filter_overlaps(sorted_dates_score_list)
            
            values_list = [(pd.to_datetime(start), pd.to_datetime(end), distance) for start, end, distance in filtered_dates]
            print("values_list=====")
            print(values_list)
            st.write("##### Original")
            fig_superimpose_target_original = create_figure(original_data, target_date, selected_data, values_list, subtract=False, n_steps = nsteps, N = N)
            print("fffffffffffffffffffff")
            print(fig_superimpose_target_original)
            st.plotly_chart(fig_superimpose_target_original)

            st.write("##### Aligned")
            fig_superimpose_target_aligned = create_figure(original_data, target_date, selected_data, values_list, subtract=True, n_steps = nsteps, N = N)
            st.plotly_chart(fig_superimpose_target_aligned)

            if nsteps > 0:
                st.write("##### 유사기간 이후 변화")
                n_steps_ahead(original_data, values_list, n_steps = nsteps, N = N)
if __name__ == "__main__":
    main()
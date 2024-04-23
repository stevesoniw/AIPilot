import pandas as pd
import numpy as np
from dtaidistance import dtw
import plotly.graph_objects as go
from plotly.io import to_json
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from pydantic import BaseModel
from fastapi import HTTPException, APIRouter
from scipy.stats import pearsonr
from fastapi.responses import JSONResponse
import math
import json

import logging

#SECRET_KEY = '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'

logging.basicConfig(level=logging.DEBUG)
smController = APIRouter()

#################################################### [유사국면 - 단일지수 처리] Starts #################################################
def calculate_date_distance(dt, date_str1, date_str2):
    """
    Calculate the absolute distance in days between two dates provided as strings
    @param date_str1: a string representing the start date in the format specified by date_format
    @param date_str2: a string representing the end date in the format specified by date_format
    @return: The absolute distance in days between the two dates
    """
    date_distance = len(dt.loc[date_str1: date_str2])
    return date_distance
    
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
        distance = dtw.distance_fast(target_values, compare_values, window=int(user_distance * 0.2), inner_dist='squared euclidean')
        pearson_corr = pearsonr(target_values, compare_values)[0]
        score = (1 / (1 + distance)) * 0.5 + 0.5 * abs(pearson_corr)
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

def have_overlap2(range1, range2):
    start1, end1 = range1  # Adjusted to expect two values
    start2, end2 = range2

    # Assuming the dates do not overlap if one starts after the other ends
    return not (end1 < start2 or end2 < start1)

def filter_overlaps2(dates):
    filtered_dates = []
    for r1 in dates:
        overlap = False
        for r2 in filtered_dates:
            if have_overlap2(r1, r2):
                overlap = True
                break
        if not overlap:
            filtered_dates.append(r1)
    return filtered_dates


def normalize_df(df):
    """
    Normalize the values of a pandas DataFrame using Min-Max scaling.
    @param df: the dataFrame to be normalized
    @return df_normalized: the normalized dataFrame
    """
    scaler = MinMaxScaler()
    df_values = scaler.fit_transform(df.values.reshape(-1, 1))
    df_normalized = pd.DataFrame(df_values, index=df.index, columns=df.columns)
    return df_normalized

def data_select(selected_data):
    file_path = "mainHtml/assets/data/prototype.csv"
    data = pd.read_csv(file_path, index_col=0)
    if isinstance(selected_data, list):
        data = data[selected_data]
    else:
        data = data[[selected_data]]
    data = data.dropna()
    return data

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
    print("target_tracetarget_tracetarget_tracetarget_tracetarget_tracetarget_tracetarget_trace")
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

#streamlit으로 만든 plotly 차트를 fastapi형태로 변환하는게 자꾸에러남. 그냥 json 으로 바꿔서 클라로 내려주자. 
def create_figure2(sample_data, target_date, selected_data, values_list, title, subtract=False, n_steps=0):
    fig_data = {
        "title": title,
        "datasets": []
    }

    # Handle target data
    target_data = sample_data.loc[target_date[0]:target_date[1]]
    if subtract:
        target_data[selected_data] -= target_data[selected_data].iloc[0]
    fig_data["datasets"].append({
        "label": "Target",
        "data": [{"x": str(index.date()), "y": row} for index, row in target_data[selected_data].items()],
        "borderColor": "#007bff", 
        "fill": False
    })

    # Handle comparison periods
    for start_date, end_date, _ in values_list:
        additional_data = sample_data.loc[start_date: end_date]
        if subtract:
            additional_data[selected_data] -= additional_data[selected_data].iloc[0]
        fig_data["datasets"].append({
            "label": f"From {start_date} to {end_date}",  # Adjust this label as necessary
            "data": [{"x": str(index.date()), "y": row} for index, row in additional_data[selected_data].items()],
            "borderColor": "#28a745",  
            "fill": False
        })
    return fig_data


class AnalysisRequest(BaseModel):
    selected_data: str
    target_date_start: str
    target_date_end: str
    compare_date_start: str
    compare_date_end: str
    n_graphs: int 
    n_steps: int
    #n_graphs: int        
@smController.post("/similarity/univariate-analyze/")
def analyze(request: AnalysisRequest):
    original_data = data_select(request.selected_data)
    if original_data is None:
        raise HTTPException(status_code=404, detail="Data not found")
    original_data.index = pd.to_datetime(original_data.index)
    original_data = original_data.sort_index(ascending=True)
    
    N = 5
    sample_data = normalize_df(original_data)
    sample_data.index = pd.to_datetime(sample_data.index)
    sample_data = sample_data.sort_index(ascending=True)
    
    user_target_distance = calculate_date_distance(sample_data, request.target_date_start, request.target_date_end)
    
    similarity_score = compute_distance(sample_data, [request.target_date_start, request.target_date_end], [request.compare_date_start, request.compare_date_end], user_target_distance)
    dates_score_list = dates_score(sample_data, similarity_score, user_target_distance)
    sorted_dates_score_list = sorted(dates_score_list, key=lambda x: x[2], reverse=True)
    filtered_dates = filter_overlaps(sorted_dates_score_list)
    values_list = [(pd.to_datetime(start), pd.to_datetime(end), distance) for start, end, distance in filtered_dates]
    fig_superimpose_target_original = create_figure(original_data, [request.target_date_start, request.target_date_end], request.selected_data, values_list, subtract=False, n_steps = request.n_steps, N = N)
    fig_superimpose_target_aligned = create_figure(original_data, [request.target_date_start, request.target_date_end], request.selected_data, values_list, subtract=True, n_steps = request.n_steps, N = N)
    
    print(fig_superimpose_target_original)
    chart_data = {
        "original": fig_superimpose_target_original.to_json(),
        "aligned": fig_superimpose_target_aligned.to_json()
    }
        
    return {"chart_data": chart_data} 
    
#################################################### [유사국면 - 단일지수 처리] Ends #################################################

#################################################### [유사국면 - 복수지수 처리] Starts ###############################################

def same_sign(a, b):
    return (a >= 0 and b >= 0) or (a < 0 and b < 0)


def find_similar_dates(df, target_change, date_distance):
    results = []
    for i in range(len(df) - date_distance + 1):
        sliced_data = df.iloc[i: i + date_distance, 0]
        sliced_change = sliced_data.values[-1] - sliced_data.values[0]
        if math.isclose(target_change[0], sliced_change):
            start_date = sliced_data.index[0].strftime("%Y-%m-%d")
            end_date = sliced_data.index[-1].strftime("%Y-%m-%d")
            results.append([start_date, end_date])
    return results

def data_select2(selected_data):
    file_path = "mainHtml/assets/data/prototype.csv"
    data = pd.read_csv(file_path, index_col='Date', parse_dates=True)
    data = data.dropna()
    if selected_data in data.columns:
        return data
    else:
        return pd.DataFrame() 
    
    
def create_multi_figure(sample_data, target_date, selected_data, values_list, subtract=False, n_steps = 0):

    chart_data = {
        "chart": {"type": "line"},
        "title": {"text": "Time Series Analysis"},
        "xAxis": {"categories": []},
        "yAxis": {"title": {"text": "Value"}},
        "series": []
    }

    if n_steps > 0:
        get_length = len(sample_data.loc[target_date[0]: target_date[1]])
        target_data = sample_data[target_date[0]:][: get_length + n_steps]
        target_data.reset_index(drop=True, inplace=True)
    else:
        target_data = sample_data.loc[target_date[0]: target_date[1]]
        target_data.reset_index(drop=True, inplace=True)

    if subtract:
        target_trace = target_data[selected_data] - target_data[selected_data].iloc[0]
    else:
        target_trace = target_data[selected_data]

    chart_data["xAxis"]["categories"] = target_data.index.tolist()
    chart_data["series"].append({"name": f"Target: {target_date[0]} to {target_date[1]}", "data": target_trace.tolist()})

    for i, (start_date, end_date) in enumerate(values_list, 1):
        if n_steps > 0:
            get_length = len(sample_data.loc[start_date:end_date])
            sliced_data = sample_data[start_date:][:get_length + n_steps]
            sliced_data.reset_index(drop=True, inplace=True)
        else:
            sliced_data = sample_data.loc[start_date:end_date]
            sliced_data.reset_index(drop=True, inplace=True)

        if subtract:
            sliced_trace = sliced_data[selected_data] - sliced_data[selected_data].iloc[0]
        else:
            sliced_trace = sliced_data[selected_data]

        chart_data["series"].append({"name": f'Graph {i}: {start_date} to {end_date}', "data": sliced_trace.tolist()})

    return chart_data

def get_data(index_name: str) -> pd.DataFrame:
    file_path = "mainHtml/assets/data/prototype.csv"
    dt = pd.read_csv(file_path, index_col=0)[[index_name]].dropna()
    dt.index = pd.to_datetime(dt.index)
    dt = dt.sort_index(ascending=True)
    return dt

class AnalysisRequestMulti(BaseModel):
    selected_data: str
    target_date_start: str
    target_date_end: str
    compare_date_start: str
    compare_date_end: str
    n_graphs: int 
    n_steps: int
    #n_graphs: int      
@smController.post("/similarity/variation-variate-analyze/")
def analyze_time_series(request: AnalysisRequestMulti):

    print("*********************************************************")
    print(request.selected_data)
    print(request.target_date_start)
    print(request.target_date_end)
    print(request.compare_date_start)
    print(request.compare_date_end)
    print(request.n_steps)
    print(request.n_graphs)
    print("*********************************************************")

    target_start = request.target_date_start
    target_end = request.target_date_end
    compare_start = request.compare_date_start
    compare_end = request.compare_date_end
    
    #target_date = (request.target_date_start,  request.target_date_end)
    #compare_date = (request.compare_date_start, request.compare_date_end)
    
    if target_start > target_end or compare_start > compare_end:
        print("Invalid date ranges provided.")
        raise HTTPException(status_code=400, detail="Invalid date ranges provided.")

    original_data = get_data(request.selected_data)
    original_data.index = pd.to_datetime(original_data.index).normalize()
   
    target_data = original_data.loc[target_start:target_end]
    analysis_data = original_data.loc[compare_start:compare_end]
    
    target_date = (target_start, target_end)
    compare_date = (compare_start, compare_end)
    
    #target_data = original_data.loc[request.target_date_start: request.target_date_end]
    #analysis_data = original_data.loc[request.compare_date_start: request.compare_date_end]
    print("AAAAAAAAAAAAAAAAAAAAAA")
    print(target_data)
    print("AAAAAAAAAAAAAAAAAAAAAA")

    if target_data.empty or analysis_data.empty:
        print("No data available for the given date ranges.")
        raise HTTPException(status_code=404, detail="No data available for the given date ranges.")
    
    print("Target data example:", target_data.head())
    print("Analysis data example:", analysis_data.head())
    
    try:
        target_change = target_data.iloc[-1] - target_data.iloc[0]
        similar_dates = find_similar_dates(analysis_data, target_change, len(target_data))
        
        print("***********************")
        print(target_change)
        print("***********************")
        print(similar_dates)
    except IndexError:
        raise HTTPException(status_code=404, detail="Not enough data points in the target or analysis range.")
    
    if len(similar_dates) == 0:
        print("abcccccccccccccccccccccccccccc")
        raise HTTPException(status_code=404, detail="해당 변동 지수와 동일한 변동폭을 가진 과거 데이터가 없습니다. Target Date를 다시 지정하거나, 분석 지표를 다시 선택해주세요.")

    filtered_dates = filter_overlaps2(similar_dates)
    values_list = [(pd.to_datetime(start), pd.to_datetime(end)) for start, end in filtered_dates][:request.n_graphs]

    fig_superimpose_target_original = create_multi_figure(original_data, target_date, request.selected_data, values_list, subtract=False, n_steps = request.n_steps)
    fig_superimpose_target_aligned = create_multi_figure(original_data, target_date, request.selected_data, values_list, subtract=True, n_steps = request.n_steps)
    
    print(fig_superimpose_target_original)
    
    '''chart_data = {
        "original": fig_superimpose_target_original,
        "aligned": fig_superimpose_target_aligned
    }'''
    return JSONResponse(content={
        "chart_data": {
            "original": fig_superimpose_target_original,  # assuming this is already a dict
            "aligned": fig_superimpose_target_aligned     # assuming this is already a dict
        }
    })    
           


'''
request_data = AnalysisRequestMulti(
    selected_data="GT2 Govt",
    target_date_start="2020-01-10",
    target_date_end="2020-02-20",
    analysis_date_start="2015-01-21",
    analysis_date_end="2019-01-10",
    n_steps=10,
    n_graphs=2
)

# 함수 호출
try:
    result = analyze_time_series(request_data)
    print(result)
except HTTPException as e:
    print(f"HTTPException: {e.detail}")
except Exception as e:
    print(f"An error occurred: {e}")'''

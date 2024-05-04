from datetime import datetime
import pandas as pd
import numpy as np
from typing import List, Tuple
import math
import yfinance as yf
import finnhub
import plotly.graph_objects as go
from plotly.io import to_json
from sklearn.preprocessing import MinMaxScaler
from pydantic import BaseModel
from scipy.stats import pearsonr
import scipy.stats
from dtaidistance import dtw
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse
import requests
import json
import logging
import config

#SECRET_KEY = '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'

logging.basicConfig(level=logging.DEBUG)
smController = APIRouter()
rapidAPI = config.RAPID_API_KEY
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
CONTROLLER = True

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
    values_list = [(pd.to_datetime(start), pd.to_datetime(end), distance) for start, end, distance in filtered_dates][:request.n_graphs]
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
def calculate_corr_dtw(target_features, compare_features, weights):
    result = []
    for dim in range(target_features.shape[1]):
        distance = dtw.distance_fast(target_features[:, dim], compare_features[:, dim])
        corr_coef = abs(np.corrcoef(target_features[:, dim], compare_features[:, dim])[0, 1])
        score = (1 / (1 + (distance))) * 0.5 + corr_coef * 0.5
        if len(weights) != 0:
            result.append(score * weights[dim])
        else:
            result.append(score/ target_features.shape[1])
    return sum(result)

def compute_distance_multi(dt, users_target, users_compare, user_distance, weights):
    matrix = {}
    target_data = dt.loc[users_target[0]: users_target[1]]
    target_data = target_data.divide(target_data.iloc[0])
    target_data -= target_data.iloc[0]
    target_values = target_data.values

    compare_data = dt.loc[users_compare[0]: users_compare[1]]
    for i in range(len(compare_data) - user_distance + 1):
        sliced_data = compare_data.iloc[i: i + user_distance]
        sliced_data = sliced_data.divide(sliced_data.iloc[0])
        sliced_data -= sliced_data.iloc[0]
        compare_values = sliced_data.values
        score = calculate_corr_dtw(target_values, compare_values, weights)
        matrix[sliced_data.index[0].strftime("%Y-%m-%d")] = score
    return matrix

def normalize_df_multi(df):
    return (df - df.mean()) / df.std()

def generate_data(options):
    analysis_df = data_select(options)
    analysis_df = analysis_df.sort_index(ascending=True)
    analysis_df = analysis_df.loc[:,~analysis_df.columns.duplicated()]
    analysis_df.index = pd.to_datetime(analysis_df.index)
    analysis_df = analysis_df.dropna()
    return analysis_df

def create_figures(sample_data, target_dates, values_list, options, title_prefix, subtract=False, n_steps = 0):
    chart_data_list = []
    for column in options:
        chart_data = {
            "chart": {"type": "line"},
            "title": {"text": f"{title_prefix} {column}"},
            "xAxis": {"categories": []},
            "yAxis": {"title": {"text": "Value"}},
            "series": []
        }
        if n_steps > 0:
            get_length = len(sample_data.loc[target_dates[0]: target_dates[1]])
            target_data = sample_data[target_dates[0]:][: get_length + n_steps]
            target_data.reset_index(drop=True, inplace=True)
        else:
            target_data = sample_data.loc[target_dates[0]: target_dates[1]]
            target_data.reset_index(drop=True, inplace=True)
        if subtract:
            target_trace = (target_data[column] / target_data[column].iloc[0])
            target_trace = (target_trace - target_trace[0])
        else:
            target_trace = target_data[column]

        chart_data["xAxis"]["categories"] = target_data.index.tolist()
        print(target_data.index.tolist())
        chart_data["series"].append({"name": f"Target: {column.split('_')[-1]}", "data": target_trace.tolist()})

        print("77")
        for i, (start_date, end_date, score) in enumerate(values_list, 1):
            if n_steps > 0:
                print("88")
                get_length = len(sample_data.loc[start_date:end_date])
                sliced_data = sample_data[start_date:][:get_length + n_steps]
                sliced_data.reset_index(drop=True, inplace=True)
            else:
                print("99")
                sliced_data = sample_data.loc[start_date:end_date]
                sliced_data.reset_index(drop=True, inplace=True)

            if subtract:
                sliced_trace = (sliced_data[column] / sliced_data[column].iloc[0])
                sliced_trace = (sliced_trace - sliced_trace[0])
            else:
                sliced_trace = sliced_data[column]

            chart_data["series"].append({"name": f"Graph {i}: {start_date} to {end_date} ({round(score, 5)})", "data": sliced_trace.tolist()})
        chart_data_list.append(chart_data)

    return json.dumps(chart_data_list)

def n_steps_ahead(data, target_date, values_list, options, n_steps=0):
    concatenated_df = pd.DataFrame()
    target_changes = []
    for column in options:
        changes = []
        original_data = data[column]
        target_data = data[column].loc[target_date[0]: target_date[1]]
        target_change = (target_data.iloc[-1] - target_data.iloc[0])
        target_changes.append(round(target_change, 5))
        for _, (_, end_date, _) in enumerate(values_list, 1):
            sliced_data = original_data.loc[end_date:].iloc[:n_steps]
            sliced_data.reset_index(drop=True, inplace=True)
            change = sliced_data.iloc[-1] - sliced_data.iloc[0]
            changes.append(change)
        df = pd.DataFrame(changes)
        df.index = [f'Graph {i}' for i in range(1, len(df) + 1)]
        concatenated_df = pd.concat([concatenated_df, df], axis=1) 
    concatenated_df.columns = options

    target_df = pd.DataFrame(target_changes).T
    target_df.columns = options
    target_df.index = ['Delta']
    return target_df, concatenated_df

def compute_individual_dtw(dt, target_dates, graph_list):
    matrix = {}
    target_data = dt.loc[target_dates[0]: target_dates[1]]
    target_data = target_data.divide(target_data.iloc[0])
    target_data -= target_data.iloc[0]
    target_values = target_data.values

    matrix = {}
    for idx in range(target_data.shape[1]):
        target_compare = target_values[:, idx]
        result = []
        for x, y, _ in graph_list:
            sliced_data = dt.loc[x: y].iloc[:, idx]  
            sliced_data = sliced_data.divide(sliced_data.iloc[0])
            sliced_data -= sliced_data.iloc[0]
            compare_values = sliced_data.values
            distance = dtw.distance_fast(target_compare, compare_values)
            corr_coef = abs(np.corrcoef(target_compare, compare_values)[0, 1])
            score = (1 / (1 + (distance))) * 0.5 + corr_coef * 0.5
            result.append(score)
        sorted_result = sorted(result, reverse= CONTROLLER)
        rank_dict = {value: rank for rank, value in enumerate(sorted_result, start=1)}
        ranks = ["Graph "+ str(rank_dict[value]) + "(" + str(round(score, 5)) + ")" for value, score in zip(result, sorted_result)]
        matrix[target_data.columns[idx]] = ranks
    return pd.DataFrame(matrix)

class AnalysisRequestMulti(BaseModel):
    selected_data: List[str]
    target_date_start: str
    target_date_end: str
    compare_date_start: str
    compare_date_end: str
    n_graphs: int 
    n_steps: int
    weights: List[float]
@smController.post("/similarity/multivariate-analyze/")
async def analyze_multi_series(data: AnalysisRequestMulti):
    print("*********************************************************")
    print(data.selected_data)
    print(data.target_date_start)
    print(data.target_date_end)
    print(data.compare_date_start)
    print(data.compare_date_end)
    print(data.n_steps)
    print(data.n_graphs)
    print(data.weights)
    print("*********************************************************")

    #target_date = (request.target_date_start,  request.target_date_end)
    #compare_date = (request.compare_date_start, request.compare_date_end)
    
    original_data = generate_data(data.selected_data)
    original_data.index = pd.to_datetime(original_data.index).normalize()
    
    target_start_date = data.target_date_start
    target_end_date = data.target_date_end
    analysis_start_date = data.compare_date_start
    analysis_end_date = data.compare_date_end
    
    target_distance = calculate_date_distance(original_data, target_start_date, target_end_date)
    similarity_distance = compute_distance_multi(original_data, [target_start_date, target_end_date], 
                                           [analysis_start_date, analysis_end_date], target_distance, data.weights)
    dates_score_list = dates_score(original_data, similarity_distance, target_distance)
    sorted_dates_score_list = sorted(dates_score_list, key=lambda x: x[2], reverse=CONTROLLER)
    filtered_dates = filter_overlaps(sorted_dates_score_list)
    values_list = [(start_date, end_date, distance) for start_date, end_date, distance in filtered_dates][:data.n_graphs]
    
    #print(values_list)
    #print(data.selected_data)
    
    original_figs = create_figures(original_data, [target_start_date, target_end_date], values_list, data.selected_data, "(Original)", subtract=False, n_steps=data.n_steps)
    aligned_figs = create_figures(original_data, [target_start_date, target_end_date], values_list, data.selected_data, "(Aligned)", subtract=True, n_steps=data.n_steps)

    #individual_table = compute_individual_dtw(original_data, [target_start_date, target_end_date], values_list)
    if data.n_graphs > 0:
        target_df, change_df = n_steps_ahead(original_data, [target_start_date, target_end_date], values_list, data.selected_data, n_steps= data.n_graphs)
    
    return JSONResponse(content={
        "chart_data": {
            "original": original_figs,  
            "aligned": aligned_figs     
        }
    })  

#################################################### [유사국면 - 복수지수 처리] Ends ###############################################

###################################################### [유사 변동 분석 처리] Starts ###################################################
def same_sign(a, b):
    return (a >= 0 and b >= 0) or (a < 0 and b < 0)

def have_overlap_variation(range1, range2):
    start1, end1 = range1  # Adjusted to expect two values
    start2, end2 = range2

    # Assuming the dates do not overlap if one starts after the other ends
    return not (end1 < start2 or end2 < start1)

def filter_overlaps_variation(dates):
    filtered_dates = []
    for r1 in dates:
        overlap = False
        for r2 in filtered_dates:
            if have_overlap_variation(r1, r2):
                overlap = True
                break
        if not overlap:
            filtered_dates.append(r1)
    return filtered_dates


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
    
    
def create_variation_figure(sample_data, target_date, selected_data, values_list, subtract=False, n_steps = 0):

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

class AnalysisRequestVariation(BaseModel):
    selected_data: str
    target_date_start: str
    target_date_end: str
    compare_date_start: str
    compare_date_end: str
    n_graphs: int 
    n_steps: int
    #n_graphs: int      
@smController.post("/similarity/variation-variate-analyze/")
def analyze_time_series(request: AnalysisRequestVariation):

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
    #print("AAAAAAAAAAAAAAAAAAAAAA")
    #print(target_data)
    #print("AAAAAAAAAAAAAAAAAAAAAA")

    if target_data.empty or analysis_data.empty:
        print("No data available for the given date ranges.")
        raise HTTPException(status_code=404, detail="No data available for the given date ranges.")
    
    #print("Target data example:", target_data.head())
    #print("Analysis data example:", analysis_data.head())
    
    try:
        target_change = target_data.iloc[-1] - target_data.iloc[0]
        similar_dates = find_similar_dates(analysis_data, target_change, len(target_data))
        
        #print(similar_dates)
    except IndexError:
        raise HTTPException(status_code=404, detail="Not enough data points in the target or analysis range.")
    
    if len(similar_dates) == 0:
        raise HTTPException(status_code=404, detail="해당 변동 지수와 동일한 변동폭을 가진 과거 데이터가 없습니다. Target Date를 다시 지정하거나, 분석 지표를 다시 선택해주세요.")

    filtered_dates = filter_overlaps_variation(similar_dates)
    values_list = [(pd.to_datetime(start), pd.to_datetime(end)) for start, end in filtered_dates][:request.n_graphs]

    fig_superimpose_target_original = create_variation_figure(original_data, target_date, request.selected_data, values_list, subtract=False, n_steps = request.n_steps)
    fig_superimpose_target_aligned = create_variation_figure(original_data, target_date, request.selected_data, values_list, subtract=True, n_steps = request.n_steps)
    
    print(fig_superimpose_target_original)
    
    '''chart_data = {
        "original": fig_superimpose_target_original,
        "aligned": fig_superimpose_target_aligned
    }'''
    return JSONResponse(content={
        "chart_data": {
            "original": fig_superimpose_target_original,  
            "aligned": fig_superimpose_target_aligned     # this is already a dict
        }
    })    
           
###################################################### [유사 변동 분석 처리] Ends ###################################################

#################################################### ["해외주식" >> 유사국면 분석] Starts #################################################
def fs_have_overlap(range1, range2):
    start1, end1, _ = range1
    start2, end2, _ = range2
    return start1 <= end2 and start2 <= end1

def fs_remove_overlaps(ranges):
    non_overlapping = [ranges[0]]
    for r1 in ranges[1:]:
        overlap = False
        for r2 in non_overlapping:
            if fs_have_overlap(r1, r2):
                overlap = True
                break
        if not overlap:
            non_overlapping.append((pd.to_datetime(r1[0]), pd.to_datetime(r1[1]), r1[2])) # Start, End, Distance
    return non_overlapping

def fs_get_start_end_score(df, dateScore, target_distance):
    result = []
    for from_date in dateScore:
        score = dateScore[from_date]
        started_data = df.loc[from_date:][:target_distance]
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        to_date = started_data.index[-1]
        result.append((from_date, to_date, score))
    return result

def fs_compute_distance(df: pd.DataFrame, target_input: Tuple[str, str], compare_input: Tuple[str, str], target_distance: int) -> dict:
    matrix = {}
    target_data = df.loc[target_input[0]: target_input[1]]
    target_data = target_data / target_data.values[0]
    target_values = np.array(target_data.values).reshape(-1)
    target_values -= target_values[0]
    compare_data = df.loc[compare_input[0]: compare_input[1]]

    for i in range(len(compare_data) - target_distance + 1):
        sliced_data = compare_data.iloc[i: i + target_distance, 0]
        sliced_data = sliced_data / sliced_data.values[0]
        compare_values = np.array(sliced_data).reshape(-1)
        compare_values -= compare_values[0]
        distance = dtw.distance_fast(target_values, compare_values, window = int(target_distance * 0.2), inner_dist = 'squared euclidean')
        pearson_corr = scipy.stats.pearsonr(target_values, compare_values)[0]
        matrix[sliced_data.index[0].strftime("%Y-%m-%d")] = (1 / (1 + distance)) * 0.5 + 0.5 * abs(pearson_corr)
    return matrix


def fs_create_figure(sample_data, target_date, selected_data, values_list, subtract=False, n_steps = 0):

    chart_data = {
        "chart": {"type": "line"},
        "title": {"text": "Graphs"},
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
        target_trace = (target_data[selected_data] / target_data[selected_data].iloc[0])
        target_trace = (target_trace - target_trace[0])
    else:
        target_trace = target_data[selected_data]

    chart_data["xAxis"]["categories"] = target_data.index.tolist()
    chart_data["series"].append({"name": f"Target: {target_date[0]} to {target_date[1]}", "data": target_trace.tolist()})

    for i, (start_date, end_date, score) in enumerate(values_list, 1):
        if n_steps > 0:
            get_length = len(sample_data.loc[start_date:end_date])
            sliced_data = sample_data[start_date:][:get_length + n_steps]
            sliced_data.reset_index(drop=True, inplace=True)
        else:
            sliced_data = sample_data.loc[start_date:end_date]
            sliced_data.reset_index(drop=True, inplace=True)

        if subtract:
            sliced_trace = (sliced_data[selected_data] / sliced_data[selected_data].iloc[0])
            sliced_trace = (sliced_trace - sliced_trace[0])
        else:
            sliced_trace = sliced_data[selected_data]

        chart_data["series"].append({"name": f"Graph {i}: {start_date} to {end_date} ({round(score, 5)})", "data": sliced_trace.tolist()})

    return json.dumps(chart_data)


class AnalysisRequestFrStock(BaseModel):
    selected_data: str
    target_date_start: str
    target_date_end: str
    compare_date_start: str
    compare_date_end: str
    n_graphs: int 
    n_steps: int
    threshold: float
@smController.post("/similarity/foreign-stock-analyze/")
async def analyze_time_series(data: AnalysisRequestFrStock):
    target_start_date = data.target_date_start
    target_end_date = data.target_date_end
    analysis_start_date = data.compare_date_start
    analysis_end_date = data.compare_date_end
        
    target_date = [target_start_date, target_end_date]
    compare_date =  [analysis_start_date, analysis_end_date]

    if pd.to_datetime(target_date[0]) <= pd.to_datetime(compare_date[1]):
        raise HTTPException(status_code=400, detail="TARGET DATE RANGE and DATE RANGE FOR ANALYSIS should not overlap!")

    print("*********************************************************")
    print(data.selected_data)
    print(data.target_date_start)
    print(data.target_date_end)
    print(data.n_steps)
    print(data.n_graphs)
    print(data.threshold)
    print("*********************************************************")

    df = yf.download(data.selected_data)['Adj Close']
    df = df.reset_index()
    df.columns = ['Date', data.selected_data]
    df.index = pd.to_datetime(df['Date'])
    df.drop(columns = ['Date'], axis=1, inplace = True)
    df = df.sort_index(ascending=True)

    target_distance = len(df.loc[target_date[0]: target_date[1]])

    similarity_scores = fs_compute_distance(df, target_date, compare_date, target_distance)
    start_end_distance_list = fs_get_start_end_score(df, similarity_scores, target_distance)
    start_end_distance_list = sorted(start_end_distance_list, key=lambda x: x[2], reverse=CONTROLLER)
    filtered_start_end_distance_list = fs_remove_overlaps(start_end_distance_list)

    filtered_start_end_distance_list = [entry for entry in filtered_start_end_distance_list if entry[2] >= data.threshold][:data.n_graphs]

    fs_superimpose_target_original = fs_create_figure(df, target_date, data.selected_data, filtered_start_end_distance_list, subtract=False, n_steps = data.n_steps)
    fs_superimpose_target_aligned = fs_create_figure(df, target_date, data.selected_data, filtered_start_end_distance_list, subtract=True, n_steps = data.n_steps)

    print(fs_superimpose_target_original)
    print("********************")
    print(fs_superimpose_target_aligned)
    print("********************")
    
    #chart_data = {
    #    "original": fs_superimpose_target_original.to_json(),
    #    "aligned": fs_superimpose_target_aligned.to_json()
    #}
        
    return JSONResponse(content={
        "chart_data": {
            "original": fs_superimpose_target_original,  
            "aligned": fs_superimpose_target_aligned     
        }
    })  
########### [과거 뉴스 검색] ###########   
# seeking alpha 뉴스에서 쓸데없는 파라미터들 없애기
def extract_news_data(news_json):
    extracted_data = []
    for item in news_json['data']:
        news_item = item['attributes']
        links = item['links']
        # URL 처리: 'self' 키의 값에 'https://seekingalpha.com'를 조건부로 추가
        self_link = links.get('self')
        full_link = f'https://seekingalpha.com{self_link}' if self_link else None

        extracted_item = {
            'title': news_item.get('title', 'No title provided'),
            'publishOn': news_item.get('publishOn', None),
            'gettyImageUrl': news_item.get('gettyImageUrl', None),
            'link': full_link
        }
        extracted_data.append(extracted_item)
    return extracted_data


def rapidapi_indicator_news(ticker, from_date, to_date ):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list-by-symbol"
    querystring = {"id": ticker , "until": to_date, "since" : from_date, "size": "25", "number": "1"}
    headers = {
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }    
        
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()    

# Finnhub 뉴스는 Free Tier인 경우 1년치만 줌. 일단 보류 
def finnhub_company_news(ticker, from_date, to_date):
    past_news = finnhub_client.company_news(ticker, _from=from_date, to=to_date)
    #print("*****************")
    #print(past_news)
    #print("*****************")
    return past_news
    
    
# 과거 뉴스 검색해오기 
class DateRange(BaseModel):
    ticker : str
    from_date: int
    to_date: int
@smController.post("/similarity/frstPastNews/")
async def frst_past_news(date_range: DateRange):
    try:
        ticker = date_range.ticker
        from_date = date_range.from_date
        to_date = date_range.to_date        
        news_json = rapidapi_indicator_news(ticker, from_date, to_date)
        #news_json = finnhub_company_news(ticker, from_date, to_date)
        #print(news_json)
        extracted_data = extract_news_data(news_json) 
        print(extracted_data)
        return extracted_data
    except Exception as e:
        # 오류 처리
        print("Error fetching bond news:", e)
        return {"error": "Failed to fetch bond news"}



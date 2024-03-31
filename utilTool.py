from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
from pandas import Timestamp
from io import BytesIO
import base64
import json 

# 현재날짜 계산
def get_curday():
    return date.today().strftime("%Y-%m-%d")

# Timestamp 객체를 문자열로 변환하는 함수
def timestamp_to_str(ts):
    if isinstance(ts, Timestamp):
        return ts.strftime('%Y-%m-%d')
    return ts

# 날짜 데이터가 들어있는 리스트를 변환
def convert_data_for_json(data):
    dates_converted = [timestamp_to_str(date) for date in data.index]
    values = data.values.tolist()
    return dates_converted, values

# 차트를 Base64 인코딩된 문자열로 변환하는 기본 함수
def get_chart_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # 차트 닫기
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# plotly figure를 이미지로 변환하고 Base64로 인코딩
def get_chart_base64_plotly(fig):
    img_bytes = fig.to_image(format="png")
    return base64.b64encode(img_bytes).decode('utf-8')

# json으로 저장시키기
def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
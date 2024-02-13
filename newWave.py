import streamlit as st
import time
import json
import random
import finnhub
# import datasets
import pandas as pd
import numpy as np 
import yfinance as yf
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
from openai import OpenAI


st.title('AI가 말해주는 주식 정보 (해외)')
st.subheader("by AI")

st.write("")

ticker = st.text_input('주식 심볼을 입력하세요 (예: AAPL)', 'AAPL')



finnhub_client = finnhub.Client(api_key=st.secrets["FINNHUB_KEY"])
client = OpenAI(api_key = st.secrets["OPENAI_API_KEY"])



def get_curday():
    return date.today().strftime("%Y-%m-%d")


def get_news (ticker, Start_date, End_date, count=20):
    news=finnhub_client.company_news(ticker, Start_date, End_date)
    if len(news) > count :
        news = random.sample(news, count)
    sum_news = ["[헤드라인]: {} \n [요약]: {} \n".format(
        n['headline'], n['summary']) for n in news]
    return sum_news 

def gen_term_stock (ticker, Start_date, End_date):
    df = yf.download(ticker, Start_date, End_date)['Close']
    term = '상승하였습니다' if df.iloc[-1] > df.iloc[0] else '하락하였습니다'
    terms = '{}부터 {}까지 {}의 주식가격은, $ {}에서 $ {}으로 {}. 관련된 뉴스는 다음과 같습니다.'.format(Start_date, End_date, ticker, int(df.iloc[0]), int(df.iloc[-1]), term)
    return terms 


# combine case1 and case2 
def get_prompt_earning (ticker):
    curday = get_curday()
    
    profile = finnhub_client.company_profile2(symbol=ticker)
    company_template = "[기업소개]:\n\n{name}은 {ipo}에 상장한 {finnhubIndustry}섹터의 기업입니다. "
    intro_company = company_template.format(**profile)    
    
    # find announce calendar 
    Start_date_calen = (datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
    End_date_calen = (datetime.strptime(curday, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")  # 현재 시점 + 1개월 
    announce_calendar= finnhub_client.earnings_calendar(_from=Start_date_calen, to=End_date_calen, symbol=ticker, international=False).get('earningsCalendar')[0]
    
    
    # get information from earning announcement
    date_announce= announce_calendar.get('date')
    eps_actual=announce_calendar.get('epsActual')
    eps_estimate=announce_calendar.get('epsEstimate')
    earning_y = announce_calendar.get('year')
    earning_q = announce_calendar.get('quarter')
    revenue_estimate=round(announce_calendar.get('revenueEstimate')/1000000)
    
    
    if eps_actual == None : # [Case2] 실적발표 전 
        # create Prompt 
        head = "{}의 {}년 {}분기 실적 발표일은 {}으로 예정되어 있습니다. 시장에서 예측하는 실적은 매출 ${}M, eps {}입니다. ".format(profile['name'], earning_y,earning_q, date_announce, revenue_estimate, eps_estimate)
        
        # [case2] 최근 3주간 데이터 수집  
        Start_date=(datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date=curday
        
        # 뉴스 수집 및 추출 
        news = get_news (ticker, Start_date, End_date)
        terms_ = gen_term_stock(ticker, Start_date, End_date)
        prompt_news = "최근 3주간 {}: \n\n ".format(terms_)
        for i in news:
            prompt_news += "\n" + i 
        
        info = intro_company + '\n' + head 
        prompt = info + '\n' + prompt_news + '\n' + f"\n\n Based on all the information (from {Start_date} to {End_date}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price of target companies, \
            Then, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "
    
    
    
    
    
    else : # [Case1] 실적발표 후
    
        # get additional information         
        excess_eps = round(abs(eps_actual / eps_estimate -1)* 100,1)
        revenue_actual=round(announce_calendar.get('revenueActual')/1000000)
        excess_revenue = round(abs(revenue_actual/revenue_estimate-1)*100,1)
        
        
        # create Prompt 
        term1 = '상회하였으며' if revenue_actual > revenue_estimate else '하회하였으며'
        term2 = '상회하였습니다.' if eps_actual > eps_estimate else '하회하였습니다'
        head = "\n [실적발표 요약]: \n {}에 {}년{}분기 {}의 실적이 발표되었습니다. 실적(매출)은 ${}M으로 당초 예측한 ${}M 대비 {}% {}, eps는 예측한 {}대비 {}으로 eps는 {}% {} ".format(date_announce,earning_y,earning_q, profile['name'], revenue_actual, revenue_estimate,excess_revenue,term1,eps_estimate, eps_actual, excess_eps, term2)
        
        
        # 기준점 산출 (세가지 시점)
        Start_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        Start_date_after = date_announce
        if datetime.strptime(curday, "%Y-%m-%d") < (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            End_date_after = curday
        else :
            Start_date_after = date_announce
            End_date_after = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            Start_date_after7 = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            End_date_after7 = curday
        
        # 뉴스 수집 및 추출 (세가지 구간)
        news_before = get_news (ticker, Start_date_before, End_date_before)
        terms_before = gen_term_stock(ticker, Start_date_before, End_date_before)
        prompt_news_before = "Earning call 전, {}: \n\n ".format(terms_before)
        for i in news_before:
            prompt_news_before += "\n" + i 
        
        news_after = get_news (ticker, Start_date_after, End_date_after)
        terms_after = gen_term_stock(ticker, Start_date_after, End_date_after)
        prompt_news_after = "Earning call 후, {}: \n\n ".format(terms_after)
        for i in news_after:
            prompt_news_after += "\n" + i 

        
        if datetime.strptime(curday, "%Y-%m-%d") > (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            news_after7 = get_news (ticker, Start_date_after7, End_date_after7)
            terms_after7 = gen_term_stock(ticker, Start_date_after7, End_date_after7)
            prompt_news_before = "Earning call 발표 7일 이후, {}: \n\n ".format(terms_after7)
            for i in news_after7:
                prompt_news_after7 += "\n" + i 
        else :
            prompt_news_after7 = 'Not enough time since the earnings announcement to monitor trends'
            
        
        info = intro_company + '\n' + head 
        prompt_news = prompt_news_before + '\n' + prompt_news_after + '\n' + prompt_news_after7  
        prompt = info + '\n' +  prompt_news + '\n' + f"\n\n Based on all the information before earning call (from {Start_date_before} to {End_date_before}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Then, based on all the information after earning call (from {date_announce} to {curday}), let's find 5-6 points that meet expectations and points that fall short of expectations when compared before the earning call. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price before an earning call of target companies, \
            then provide an market reaction with respect to the earning call. Finally, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Market Reaction After Earning Aall]:\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "


    return info, prompt_news, prompt, SYSTEM_PROMPT




def query_gpt4(ticker):
    info, prompt_news, prompt, SYSTEM_PROMPT = get_prompt_earning(ticker)

    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
            ]
    )
    return info, prompt_news, completion





def get_historical_eps(ticker, limit=4):
    earnings = finnhub_client.company_earnings(ticker, limit)
    earnings_json = [
        {
            "period":earning["period"],
            "actual":earning["actual"],
            "estimate":earning["estimate"],
            "surprisePercent":earning["surprisePercent"]
        } for earning in earnings 
    ]
    earnings_json.sort(key = lambda x:x['period'])
    df_earnings=pd.DataFrame(earnings_json)
    
    fig, ax = plt.subplots(figsize=(8,5))
    ax.scatter(df_earnings['period'], df_earnings['actual'],c='green', s=500, alpha=0.3, label='actual')
    ax.scatter(df_earnings['period'], df_earnings['estimate'],c='blue', s=500, alpha=0.3, label='estimate')
    ax.set_xlabel('announcement date', fontsize=15)
    ax.set_ylabel('eps', fontsize=15)
    ax.set_title('{} - Historical eps Surprise'.format(ticker), fontsize=17)
    ax.grid()
    ax.legend()

    for i in range(len(df_earnings)):
        plt.text(df_earnings['period'][i], df_earnings['actual'][i], ('Missed by ' if df_earnings['surprisePercent'][i] <0 else 'Beat by ')+ "{:.2f}".format(df_earnings['surprisePercent'][i])+"%",
                color='black' if df_earnings['surprisePercent'][i] <0 else 'red' , fontsize=11, ha='left', va='bottom')
    return fig
    
def get_recommend_trend (ticker) : 
    recommend_trend = finnhub_client.recommendation_trends(ticker)
    df_recommend_trend = pd.DataFrame(recommend_trend).set_index('period').drop('symbol', axis=1).sort_index()

    fig, ax = plt.subplots(figsize=(8,5))
    width = 0.6  
    
    bottom=np.zeros(len(df_recommend_trend))
    p1= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongSell'], label='strong Sell', color='red', width=width, bottom=bottom)
    bottom +=df_recommend_trend['strongSell']
    p2= ax.bar(df_recommend_trend.index,  df_recommend_trend['sell'], label='Sell', color='orange',width=width,bottom=bottom)
    bottom +=df_recommend_trend['sell']
    p3= ax.bar(df_recommend_trend.index,  df_recommend_trend['hold'], label='Hold', color='grey',width=width,bottom=bottom)
    bottom +=df_recommend_trend['hold']
    p4= ax.bar(df_recommend_trend.index,  df_recommend_trend['buy'], label='Buy', color='skyblue',width=width,bottom=bottom)
    bottom +=df_recommend_trend['buy']
    p5= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongBuy'], label='strong Buy', color='blue',width=width,bottom=bottom)
    
    if df_recommend_trend['strongSell'].sum() > 0 :
        ax.bar_label(p1, label_type='center')
    if df_recommend_trend['sell'].sum() > 0 :
        ax.bar_label(p2, label_type='center')
    if df_recommend_trend['hold'].sum() > 0 :
        ax.bar_label(p3, label_type='center')
    if df_recommend_trend['buy'].sum() > 0 :
        ax.bar_label(p4, label_type='center')
    if df_recommend_trend['strongBuy'].sum() > 0 :
        ax.bar_label(p5, label_type='center')
    
    plt.title('{} recommendation trend'.format(ticker), fontsize=12)
    plt.ylabel('Number of analysts')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
    return fig




def get_one_year_before(end_date):
  end_date = datetime.strptime(end_date, "%Y-%m-%d")
  one_year_before = end_date - timedelta(days=365)
  return one_year_before.strftime("%Y-%m-%d")
def get_stock_data_daily(symbol):
  EndDate = get_curday()
  StartDate = get_one_year_before(EndDate)
  stock_data = yf.download(symbol, StartDate, EndDate)
  return stock_data[["Adj Close", "Volume"]]


def get_stock_data_fig (ticker):
    data = get_stock_data_daily(ticker)
    fig, ax1 = plt.subplots(figsize=(14, 5))

    ax1.plot(data['Adj Close'], label='Price(USD)', color='blue')
    ax1.set_xlabel('date')
    ax1.set_ylabel('Price(USD)', color='blue')
    ax1.tick_params('y', colors='blue')
    ax1.set_title(f'{ticker} Stock price and Volume Chart (recent 1 year)')
    ax2 = ax1.twinx()
    ax2.bar(data.index, data['Volume'], label='Volume', alpha=0.2, color='green')
    ax2.set_ylabel('Volume', color='green')
    ax2.tick_params('y', colors='green')

    return fig 
    

if st.button("실행하기"):

    with st.status("Processing data...", expanded=True) as status :                
        fig1 = get_historical_eps(ticker)
        fig2 = get_recommend_trend(ticker)
        st.write('\n :sunglasses: {}의 :orange[최근 실적발표 History]입니다. '.format(ticker))
        st.pyplot(fig1)
        st.divider()
        st.write('\n :sunglasses: {}에 대한 :orange[애널리스트들의 추천 트렌드]입니다. '.format(ticker))
        st.pyplot(fig2)
        status.update(label="Processing completed!!")
                    
    with st.status("Processing data... (It takes time to get AI respose. )", expanded=True) as status :    
        st.divider()
        st.write(f':sunglasses: {ticker}에 대한 :orange[AI분석결과]는 다음과 같습니다.')
        st.info("최근 실적발표가 있었던 경우에는, 실적발표 전/후 반응을 나누어 비교 분석합니다. 실적 발표 예정인 경우에는 이전 정보 기준으로만 분석합니다.",
            icon="💡")
        info, prompt_news, completion = query_gpt4(ticker)            
        st.divider()
        st.write(info)
        st.divider()
        st.write(completion.choices[0].message.content)
        st.divider()
        st.write('\n \n :sunglasses: AI분석의 :orange[근거가 되는 정보]는 아래와 같습니다. (:orange[최신 영문 기사] 기반으로 수행되었습니다.)')
        st.write(prompt_news)
        status.update(label="Processing completed!!")
        st.divider()
        
    with st.status("Processing data... ", expanded=True) as status :    
        st.write('\n :sunglasses: 최근 1년 주가 흐름과 거래량 추이를 참조하세요. ')
        fig3= get_stock_data_fig (ticker)
        st.pyplot(fig3)
        status.update(label="Processing completed!!")



            

import tweepy
import config
import pandas as pd

consumer_key = config.TWEETER_CLIENT_ID
consumer_secret = config.TWEETER_CLIENT_SECRET
bearer_token = config.TWEETER_BEARER_TOKEN
access_token = config.TWEETER_ACCESS_TOKEN
access_token_secret = config.TWEETER_CLIENT_SECRET


client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret, access_token=access_token, access_token_secret=access_token_secret)

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

try :
    api.verify_credentials()
    print("success")
except :
    print("Failed auth")

def get_trending_topics():
    trends_available = client.available_trends()
    print(f"Number of Trends availables: {len(trends_available)}")
    rj_trends = client.get_place_trends(id =1132599) # WOEID of Seoul; 1132599
    trends = []
    for trend in rj_trends[0]['trends']:
        if trend['tweet_volume'] is not None and trend['tweet_volume'] > 5000:
            trends.append((trend['name'], trend['tweet_volume']))

    trends.sort(key=lambda x:-x[1])
    print(trends)
    return trends

    
#get_trending_topics()

        
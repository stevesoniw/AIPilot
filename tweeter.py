import tweepy
import config
import pandas as pd
from tweepy import OAuthHandler


consumer_key = config.TWEETER_CLIENT_ID
consumer_secret = config.TWEETER_CLIENT_SECRET
bearer_token = config.TWEETER_BEARER_TOKEN
access_token = config.TWEETER_ACCESS_TOKEN
access_token_secret = config.TWEETER_CLIENT_SECRET


auth = tweepy.AppAuthHandler(
    consumer_key, consumer_secret
)
auth.set_access_token(access_token, access_token_secret)

client = tweepy.Client(bearer_token=bearer_token)
apiv2 = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret, access_token=access_token, access_token_secret=access_token_secret)
api = tweepy.API(auth)
user = api.get_user(id="SteveSon194948" , screen_name="SteveSon194948")

try :
    print(user.screen_name)
    print(user.followers_count)
    print("success")
except :
    print("Failed auth")

def get_trending_topics():
    trends_available = api4.available_trends()
    print(f"Number of Trends availables: {len(trends_available)}")
    rj_trends = api4.get_place_trends(id =1132599) # WOEID of Seoul; 1132599
    trends = []
    for trend in rj_trends[0]['trends']:
        if trend['tweet_volume'] is not None and trend['tweet_volume'] > 5000:
            trends.append((trend['name'], trend['tweet_volume']))

    trends.sort(key=lambda x:-x[1])
    print(trends)
    return trends

def get_test():
    query = 'COVID19 place_country:GB'
    start_time = '2018-01-01T00:00:00Z'
    end_time = '2018-08-03T00:00:00Z'
    tweets = api3.search_all_tweets(query=query, tweet_fields=['context_annotations', 'created_at', 'geo'], place_fields=['place_type', 'geo'], user_fields=['location'], expansions='author_id,geo.place_id', start_time=start_time, end_time=end_time, max_results=10)
    places = {p["id"]: p for p in tweets.includes['places']}
    users = {u["id"]: u for u in tweets.includes['users']}
    for tweet in tweets.data:
        print(tweet.id)
        print(tweet.created_at)
        print(tweet.text)
        print(tweet.author_id)
        if users[tweet.author_id]:
            user = users[tweet.author_id]
            print(user.location) #note that users can add whatever they want as location
        if places[tweet.geo['place_id']]:
            place = places[tweet.geo['place_id']]
            print(place.full_name)

    


        
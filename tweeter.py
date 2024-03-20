import tweepy
import config
import json
import pandas as pd
from tweepy import OAuthHandler
from requests_oauthlib import OAuth1Session
import requests

consumer_key = config.TWEETER_API_KEY
consumer_secret = config.TWEETER_API_SECRET
client_key = config.TWEETER_CLIENT_ID
client_secret = config.TWEETER_CLIENT_SECRET
bearer_token = config.TWEETER_BEARER_TOKEN
access_token = config.TWEETER_ACCESS_TOKEN
access_token_secret = config.TWEETER_CLIENT_SECRET
payload = {"text": "Hello world!"}


def writeTweet():
    # Get request token
    request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)



    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError:
        print(
            "There may have been an issue with the consumer_key or consumer_secret you entered."
        )

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print("Got OAuth token: %s" % resource_owner_key)

    # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")

    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)

    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Make the request
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    # Making the request
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
    )

    if response.status_code != 201:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))

    # Saving the response as JSON
    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))

def get_params():
    return {"user.fields": "created_at"}

def create_url():
    tweet_fields = "tweet.fields=lang,author_id"
    # Tweet fields are adjustable.
    # Options include:
    # attachments, author_id, context_annotations,
    # conversation_id, created_at, entities, geo, id,
    # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    # source, text, and withheld
    ids = "ids=1278747501642657792,1255542774432063488"
    # You can adjust ids to include a single Tweets.
    # Or you can add to up to 100 comma-separated IDs
    url = "https://api.twitter.com/2/tweets?{}&{}".format(ids, tweet_fields)
    return url

def connect_to_endpoint(url):
    response = requests.request("GET", url, auth=bearer_oauth)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2TweetLookupPython"
    return r


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

    
def lookup_tweets():
    url = create_url()
    json_response = connect_to_endpoint(url)
    print(json.dumps(json_response, indent=4, sort_keys=True))


lookup_tweets()        
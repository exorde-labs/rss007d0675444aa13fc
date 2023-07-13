from datetime import datetime
from typing import AsyncGenerator
import logging
import aiohttp
from . import ArticleClass
from ArticleClass import Article
from ExtractContent import request_random_content
from exorde_data import (
    Item,
    Content,
    Author,
    CreatedAt,
    Title,
    Url,
    Domain
)

async def get_json_dict():
    url = "https://raw.githubusercontent.com/exorde-labs/TestnetProtocol/main/targets/FeedSources.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json(content_type=None)

    return data

def convert_to_iso8601_utc(datetime_str: str) -> str:
    # Convert the input string to a datetime object
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    # Convert the datetime object to the desired format
    iso8601_utc = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return iso8601_utc

# default values
DEFAULT_OLDNESS_SECONDS = 360
DEFAULT_MAXIMUM_ITEMS = 25
DEFAULT_MIN_POST_LENGTH = 10
DEFAULT_MAX_TRIALS = 10

def read_parameters(parameters):
    # Check if parameters is not empty or None
    if parameters and isinstance(parameters, dict):
        try:
            max_oldness_seconds = parameters.get("max_oldness_seconds", DEFAULT_OLDNESS_SECONDS)
        except KeyError:
            max_oldness_seconds = DEFAULT_OLDNESS_SECONDS

        try:
            maximum_items_to_collect = parameters.get("maximum_items_to_collect", DEFAULT_MAXIMUM_ITEMS)
        except KeyError:
            maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS

        try:
            min_post_length = parameters.get("min_post_length", DEFAULT_MIN_POST_LENGTH)
        except KeyError:
            min_post_length = DEFAULT_MIN_POST_LENGTH

        try:
            max_extraction_trials = parameters.get("max_extraction_trials", DEFAULT_MAX_TRIALS)
        except KeyError:
            max_extraction_trials = DEFAULT_MAX_TRIALS
    else:
        # Assign default values if parameters is empty or None
        max_oldness_seconds = DEFAULT_OLDNESS_SECONDS
        maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS
        min_post_length = DEFAULT_MIN_POST_LENGTH
        max_extraction_trials = DEFAULT_MAX_TRIALS

    return max_oldness_seconds, maximum_items_to_collect, min_post_length, max_extraction_trials


async def query(parameters: dict) -> AsyncGenerator[Item, None]:
    # read parameters dict
    max_oldness_seconds, maximum_items_to_collect, min_post_length, max_extraction_trials = read_parameters(parameters)

    number_of_articles = maximum_items_to_collect
    max_number_of_tries = max_extraction_trials
    max_age_of_article_in_seconds = max_oldness_seconds
    try:
        data = await get_json_dict()
    except Exception as e:
        logging.info(f"[RSS newsfeed] Error when fetching the FeedSource.json: {e}")
    """
    Article data is accessible following this structure:
        self.rss_source // the RSS feed name that we are collecting from
        self.rss_description // the description of the RSS feed we are collecting from
        self.language // the RSS feed's language, and therefore the language of the article
        self.title // the title of the article 
        self.url // the URL link to the article
        self.publish_date // the publish date of the article
        self.description // the description (summary) of the article
        self.content // the content of the article that was collected
    """
    try:
        articles = request_random_content(number_of_articles, max_age_of_article_in_seconds, data, max_number_of_tries)
    except Exception as e:
        logging.info(f"[RSS newsfeed] Error when requesting content: {e}")
        articles = []

    for article in articles:
        try:
            logging.info(f"[RSS newsfeed] FOUND ARTICLE: ")    
            logging.info(f"[RSS newsfeed]\tSource = {article.rss_source}")
            logging.info(f"[RSS newsfeed]\tURL = {article.url}")
            created_at_formatted = convert_to_iso8601_utc(article.publish_date)
            logging.info(f"[RSS newsfeed]\tDate = {created_at_formatted}")
            logging.info(f"[RSS newsfeed]\tTitle = {article.title}")
            logging.info(f"[RSS newsfeed]\tArticle content = {str(article.content)}")        
            new_item = Item(
                content=Content(str(article.content)),
                author=Author(article.rss_source),
                created_at=CreatedAt(created_at_formatted),
                title=Title(article.title),
                domain=Domain("news.exorde"),
                url=Url(article.url)
            )
            yield new_item
        except Exception as e:
            logging.info(f"[RSS newsfeed] Error during article yield: {e}")

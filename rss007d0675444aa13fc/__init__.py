from datetime import datetime
from typing import AsyncGenerator
import logging
import aiohttp
import json
import random
import feedparser
import tldextract
import re
import pytz
from datetime import datetime
from dateutil import parser
from io import BytesIO
from newspaper import Article as Newspaper
from exorde_data import (
    Item,
    Content,
    Author,
    CreatedAt,
    Title,
    Url,
    Domain
)

################################################################################################################
"""
The Article Class is used to fully describe an article so it can be passed as a standalone element. This is used
when extracting content from an article for example. Essentially, it combines the RSS ID class and the Link class together.
"""
class Article:

    def __init__(self, _rss_source, _rss_description, _rss_language, _article_title, _article_url,
                 _article_publish_date, _article_description):

        self.rss_source = _rss_source
        self.rss_description = _rss_description
        self.language = _rss_language
        self.title = _article_title
        self.url = _article_url
        self.publish_date = _article_publish_date
        self.description = _article_description
        self.content = None

    def update_content(self, _content):
        self.content = _content

"""
The Link Class defines all the underlying links' parameters within an RSS feed. This is used with RssID Class within the
Rss Class to fully define articles within an existing RSS feed.
"""
class Link:
    def __init__(self, _title, _link, _publish_date=None, _description=None):
        self.title = _title
        self.link = _link
        self.publish_date = _publish_date
        self.description = _description

"""
The RSS Class defines all the parameters associated to an Rss Feed for future integration.
"""
class RSS:
    def __init__(self, _rss_id):
        self.rss_id = _rss_id
        self.link_array = []

"""
The DocId class is used to describe an RSS Feed. This structure is a temporary class used to create
Article classes.
"""
class RssID:

    def __init__(self, _source, _description, _language, _rss_url, _last_build_date=None):
        self.source = _source
        self.description = _description
        self.language = _language
        self.rss_url = _rss_url
        self.last_build_date = _last_build_date

    def to_json(self):
        return {
            "Source": self.source,
            "Description": self.description,
            "Language": self.language,
            "URL": self.rss_url,
            "Last Build Date": self.last_build_date
        }

    @classmethod
    def from_json(cls, json_data):
        return cls(json_data["Source"], json_data["Category"], json_data["Language"], json_data["URL"],
                   json_data["Las Build Date"])


# Define a custom JSONEncoder subclass
class RssEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, RssID):
            return obj.to_json()
        return super().default(obj)

################################################################################################################

def convert_to_standard_timezone(_date):
    """
    Takes an unparsed date and normalizes is to a UTC + 000 format
    :param _date: Unparsed date that we need to convert to standard timezone format
    :return: Standardized date format
    """
    dt = parser.parse(_date)  # parse date so we can exploit its data (can't use fuzzy param here to avoid false negatives)
    dt = dt.astimezone(pytz.timezone('UTC'))  # convert to UTC timezone
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_reference_json_data(_json_file_data):
    """
    Same thing as the previous parse_reference_json but only with the data as the JSON file is accessed beforehand
    Take the data of a JSON file formatted with RSS IDs to extract RSS ID class objects from it
    :param _json_file_data: The JSON file's data we are currently analyzing
    :return: A list of RSSid classes extracted from this file
    """

    all_feeds = []

    # Extract fields from each element
    for item in _json_file_data:
        source = item["Source"]
        description = item["Description"]
        language = item["Language"]
        url = item["URL"]
        last_build_date = None
        if "Last_Build_Date" in item:
            last_build_date = item["Last_Build_Date"]
        all_feeds.append(RssID(source, description, language, url, last_build_date))

    return all_feeds


def extract_latest_items(_rss,
                         _start_date=convert_to_standard_timezone("Wednesday, 01 Jan 1000 00:00:01 +0000"),
                         _end_date=convert_to_standard_timezone("Friday, 01 Jan 2100 00:00:01 +0000")):
    """
    Extracts the latest items from the RSS feed within the time window specified
    :param _rss: the Rss feed from which we will be extracting the latest articles
    :param _start_date: the start date from which we will collect data, if un-specified, all data will be collected
    :param _end_date: the end date to which we will collect data, if un-specified all data will be collected
    :return: returns a list of elements that each have a title, a link and a publish date
    """

    # Parse the XML feed
    try:
        feed = feedparser.parse(_rss.rss_id.rss_url)
    except Exception as e:
        print("Error: " + str(e))
        return

    # Extract data from each item
    for item in feed.entries:

        if hasattr(item, "published") or hasattr(item, "pubDate") or hasattr(item, "updated"):
            s_publish_date = item.get("published") or item.get("pubDate") or item.get("updated")
            if s_publish_date:
                try:
                    formatted_date = convert_to_standard_timezone(s_publish_date)
                except Exception:
                    formatted_date = None
                    pass
            else:
                formatted_date = None

            # Skip dates that are defined and not within the established time window
            # Note that undefined dates won't be removed here

            if formatted_date is not None and _start_date <= formatted_date <= _end_date:  # don't keep links with no associated date as we will not parse the article for a date
                if hasattr(item, "title") and hasattr(item, "link"):
                    title = item.title
                    link = item.link
                    if hasattr(item, "description"):
                        description = item.description
                    else:
                        description = None
                else:
                    continue
                _rss.link_array.append(Link(title, link, formatted_date, description))  # add the link to the RSS archive


################################################################################################################

"""
To perform our scraping, we use the Scrapy python library. This library fully supports asynchronous requests and is
key in being able to perform the tasks that we wish to carry out with this script.

Unfortunately, this library relies on the Twisted library which creates a Singleton instance declared globally. This means
you cannot run spiders "on the go". Once a scraping job is assigned, it must return as completed, before another one can
be assigned to the same machine.

In other words, asking machine X to perform Y scraping job and then asking X to perform Z scraping job 20s later before
Y is completed, will cause an error.

Hence, in a distributed system it is paramount to correctly assign the scraping jobs right from the start and be ready to
wait for the return statement of the worker before assigning a new task.

This following program utilizes a curated list of RSS Feeds organized under the form of a JSON file. All the links
present within this feed should have already been checked against existing entries with the RssAgglomerator.py script
and further checked on content availability and format by the RssChecker.py.

At this stage, this script will be used only to start a scraping job on a list of RSS Feeds that were selected for a
node of the distributed network. Note that certain RSS Feeds can have hundreds of entries, and in that sense, it is
paramount to correctly assess the expanse of the task before assigning it as scrapy spiders can only scrape so much
content, and certain tasks may end up taking a lot more time and resources than others.

Note that one spider will be launched for every URL submitted to avoid putting too much charge on a single spider.

Author: Térence Gras, CEO @ Exorde Labs
"""


def extract_content(_dict):  # using Newspaper3k

    content = [[] for i in range(len(_dict))]
    for i in range(0, len(_dict)):
        a = Newspaper(_dict[i][0], language=_dict[i][1])
        a.download()
        try:
            a.parse()
            content[i].append(a.text)
        except:
            content[i].append("")
    return content


def request_random_content(_n_articles, _max_age, _json_data, _max_number_of_tries):
    """
    Requests random articles from the database that fit the entry params.
    :param _n_articles: The random number of articles we wish to extract from the RSS feeds.
    :param _max_age: The max age in seconds of these articles in comparison to now.
    :return: A list of articles composed of [source, language, description, url, content, publish date]
    """

    rss_ids = parse_reference_json_data(_json_data)
    articles = find_random_articles_with_max_age(_n_articles, rss_ids, _max_age, _max_number_of_tries)

    dict = []

    for article in articles:
        dict.append((article.url, article.language[:2]))

    raw_content = extract_content(dict)

    for i in range(0, len(raw_content)):
        for article in articles:
            if dict[i][0] == article.url:
                article.update_content(raw_content[i])
                break  # move to next content

    return articles


def find_random_articles_with_max_age(_n_articles, _rss_id_list, _max_age, _max_number_of_tries):
    """
    Finds a random number of article urls within the reference JSON feed.
    :param _max_age:
    :param _n_articles:
    :param _rss_id_list: The Rss ID list we will be selecting a random article from
    :return: A random article's rss_id & Link info
    """

    articles = []
    appended_urls = []
    now_time = datetime.now()
    now_time = now_time.strftime("%Y-%m-%d %H:%M:%S")  # format correctly
    cumulative_tries = 0
    current_try_count = 0

    while len(articles) < _n_articles:

        if current_try_count > _max_number_of_tries:  # stop here
            return articles

        rss_id = random.choice(_rss_id_list)

        rss = RSS(rss_id)
        extract_latest_items(rss)

        for link in rss.link_array:
            current_try_count += 1
            cumulative_tries += 1
            if cumulative_tries > 5:
                cumulative_tries = 0
                break # break out of this for loop and move on to the next one
            if is_within_max_age(now_time, link.publish_date, _max_age) and link.link not in appended_urls:
                cumulative_tries = 0  # reset this parameter to zero as we have selected an article
                appended_urls.append(link.link)
                articles.append(Article(rss_id.source, rss_id.description, rss_id.language, link.title, link.link, link.publish_date, link.description))
                if len(articles) == _n_articles:
                    break
    return articles


def is_within_max_age(_now_time, _date, _max_age):
    """
    Finds the difference in seconds between a present date and time and the date and time of the _date variable
    :param _now_time: The time of here and now under this format "2023-06-08 19:30:00"
    :param _date: The time we wish to compare now to
    :param _max_age: The threshold in seconds that we are not allowed to cross
    :return: True if _now_time - _date <= _max_age, False otherwise
    """

    # Convert date strings to datetime objects
    d1 = datetime.strptime(_now_time, "%Y-%m-%d %H:%M:%S")
    d2 = datetime.strptime(_date, "%Y-%m-%d %H:%M:%S")
    time_diff = d1 - d2
    if time_diff.total_seconds()<= _max_age:
        return True
    else:
        return False

################################################################################################################
################################################################################################################

async def get_json_dict():
    url = "https://raw.githubusercontent.com/exorde-labs/TestnetProtocol/main/targets/FeedSources.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json(content_type=None)

    return data

def extract_domain_name(url):
    try:
        domain_parts = tldextract.extract(url)
        domain = domain_parts.domain + '.' + domain_parts.suffix
        domain = re.sub(r"[^a-zA-Z0-9.-]", "", domain)
        return domain
    except Exception:
        pass

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
    logging.info(f"[RSS newsfeed] Trying to find {number_of_articles} article(s) under {max_age_of_article_in_seconds} in {max_number_of_tries} max trials...")    
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
            source_domain = extract_domain_name(article.rss_source)
            logging.info(f"[RSS newsfeed]\tURL = {article.url}")
            created_at_formatted = convert_to_iso8601_utc(article.publish_date)
            logging.info(f"[RSS newsfeed]\tDate = {created_at_formatted}")
            logging.info(f"[RSS newsfeed]\tTitle = {article.title}")
            logging.info(f"[RSS newsfeed]\tArticle content = {str(article.content)}")        
            new_item = Item(
                content=Content(str(article.content)[:800),
                # author=Author(str(source_domain)),
                created_at=CreatedAt(created_at_formatted),
                title=Title(article.title),
                domain=Domain("news.exorde"),
                url=Url(article.url)
            )
            yield new_item
        except Exception as e:
            logging.info(f"[RSS newsfeed] Error during article yield: {e}")

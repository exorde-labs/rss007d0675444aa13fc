import feedparser
import json
import random
import requests
import pytz
from datetime import datetime
from LinkClass import Link
from dateutil import parser
from RssIDClass import RssID
from io import BytesIO


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
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
"""
from datetime import datetime
import random
from ArticleClass import Article
from RssClass import RSS
from XmlParser import parse_reference_json, extract_latest_items, convert_to_standard_timezone
from GlobalVariables import JSON_FILE, USER_AGENT_LIST

from newspaper import Article as Newspaper
from newspaper import Config


def extract_content(_dict):  # using Newspaper3k

    content = [[] for i in range(len(_dict))]
    for i in range(0, len(_dict)):
        try:
            rand = random.choice(USER_AGENT_LIST)
            config = Config()
            config.browser_user_agent = rand
            a = Newspaper(_dict[i][0], language=_dict[i][1], config=config)
            print("Downloading " + str(_dict[i][0]))
            a.download()
            a.parse()
            content[i].append(a.text)
        except Exception as e:
            content[i].append("")
    return content


def request_content(_n_articles, _max_age):
    """
    Requests random articles from the database that fit the entry params.
    :param _n_articles: The random number of articles we wish to extract from the RSS feeds.
    :param _max_age: The max age in seconds of these articles in comparison to now.
    :return: A list of articles composed of [source, language, description, url, content, publish date]
    """

    rss_ids = parse_reference_json(JSON_FILE)
    articles = find_random_articles_with_max_age(_n_articles, rss_ids, _max_age)

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


def find_random_articles_with_max_age(_n_articles, _rss_id_list, _max_age):
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

    while len(articles) < _n_articles:

        rss_id = random.choice(_rss_id_list)

        rss = RSS(rss_id)
        extract_latest_items(rss)

        for link in rss.link_array:
            if is_within_max_age(now_time, link.publish_date, _max_age) and link.link not in appended_urls:
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


if __name__ == '__main__':

    articles = request_content(10, 86400)
    print("\n\n\n\n\n")
    print("***********************************************************************************************************")
    for article in articles:
        print("Feed: " + article.rss_source)
        print("Feed Descrition: " + article.rss_description)
        print("Article Title: " + article.title)
        print("Article URL: " + article.url)
        print("Article Language: " + article.language)
        print("Article Publish Date: " + article.publish_date)
        print("Article Description: " + article.description)
        print("Article Content: ")
        for element in article.content:
            print(element)
        print(
            "***********************************************************************************************************\n")

    # content = extract_content(["https://www.asahi.com/articles/ASR695HL3R69UHBI00N.html?ref=rss"])
    # for cont in content:
    #     for element in cont["visible_text"]:
    #         print(element)




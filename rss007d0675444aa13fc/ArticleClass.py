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


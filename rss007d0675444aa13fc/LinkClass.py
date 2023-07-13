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

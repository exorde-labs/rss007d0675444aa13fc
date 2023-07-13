import json

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

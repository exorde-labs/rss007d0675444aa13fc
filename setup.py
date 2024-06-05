from setuptools import find_packages, setup

setup(
    name="rss007d0675444aa13fc",
    version="0.2.15",
    packages=find_packages(),
    install_requires=[
        "exorde_data",
        "aiohttp",
        "tldextract>=3.1.0",
        "feedparser>=6.0.8",
        "newspaper4k>=0.9.3.1",
        "pytz>=2023.3",
        "python_dateutil>=2.8.2",
        "lxml_html_clean>=0.1.1"
    ],
    extras_require={"dev": ["pytest", "pytest-cov", "pytest-asyncio"]},
)

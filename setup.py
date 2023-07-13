from setuptools import find_packages, setup

setup(
    name="rss007d0675444aa13fc",
    version="0.0.2",
    packages=find_packages(),
    install_requires=[
        "exorde_data",
        "aiohttp",
        "feedparser>=6.0.8",
        "newspaper3k>=0.2.8",
        "pytz>=2023.3",
        "python_dateutil>=2.8.2"
    ],
    extras_require={"dev": ["pytest", "pytest-cov", "pytest-asyncio"]},
)
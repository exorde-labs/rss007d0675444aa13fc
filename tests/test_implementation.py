from rss007d0675444aa13fc import query
from exorde_data.models import Item
import pytest


@pytest.mark.asyncio
async def test_query():
    try:
        # Example parameters dictionary
        parameters = {
            "max_oldness_seconds":10000,
            "maximum_items_to_collect": 1
        }
        async for item in query(parameters):
            assert isinstance(item, Item)
    except ValueError as e:
        print(f"Error: {str(e)}")

import asyncio
asyncio.run(test_query())
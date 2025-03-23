# tests/test_direct_api_call.py
import asyncio
from linkedin import SearchCriteria, search_linkedin_profiles

async def test_live_linkedin_api_call():
    criteria = SearchCriteria(
        keyword="venture capital",
        industry="Energy",
        partial_match=True
    )

    result = await search_linkedin_profiles(criteria)
    print("\n=== API Response ===")
    print(result)
    assert result is not None, "API call returned None"
    assert "results" in result, "No 'results' in API response"
    assert isinstance(result["results"], list), "'results' is not a list"

if __name__ == "__main__":
    asyncio.run(test_live_linkedin_api_call())

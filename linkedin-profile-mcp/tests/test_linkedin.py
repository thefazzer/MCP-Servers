import pytest
from unittest.mock import patch, AsyncMock
from linkedin import SearchCriteria, search_linkedin_profiles

@pytest.fixture
def mock_profile_data():
    return {
        "results": [
            {
                "full_name": "John Smith",
                "title": "Seed Investor at VC Fund",
                "industry": "Financial Services",
                "location": "London, UK"
            },
            {
                "full_name": "Jane Doe",
                "title": "Angel Investor & Managing Partner",
                "industry": "Venture Capital",
                "location": "New York, US"
            }
        ]
    }

@pytest.mark.asyncio
async def test_search_criteria_exact_match():
    criteria = SearchCriteria(
        keyword="investor",
        partial_match=False
    )
    profile_text = "Senior Investor at Growth Fund"
    assert criteria.matches_criteria(profile_text) == True

@pytest.mark.asyncio
async def test_search_criteria_partial_match():
    criteria = SearchCriteria(
        keyword="invest",
        partial_match=True,
        min_similarity=70
    )
    profile_text = "Investment Director at Seed Fund"
    assert criteria.matches_criteria(profile_text) == True

@pytest.mark.asyncio
async def test_search_criteria_synonym_match():
    criteria = SearchCriteria(
        keyword="VC",
        partial_match=True
    )
    profile_text = "Venture Capital Partner"
    assert criteria.matches_criteria(profile_text) == True

@pytest.mark.asyncio
async def test_search_linkedin_profiles_no_results():
    criteria = SearchCriteria(
        keyword="nonexistent",
        industry="Nonexistent Industry"
    )

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("API Error")
        result = await search_linkedin_profiles(criteria)
        assert result is None


@pytest.mark.asyncio
async def test_search_linkedin_profiles():
    mock_response = {
        "results": [
            {
                "full_name": "John Smith",
                "title": "Seed Investor",
                "industry": "Financial Services"
            }
        ]
    }

    criteria = SearchCriteria(
        keyword="seed investor",
        industry="Financial Services"
    )

    async def mock_raise_for_status():
        return None

    # Create mock response
    mock_response_obj = AsyncMock()
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_response_obj.raise_for_status = mock_raise_for_status

    # Create mock client
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response_obj)

    with patch('httpx.AsyncClient') as client_class:
        client_class.return_value.__aenter__.return_value = mock_client

        result = await search_linkedin_profiles(criteria)
        
        # Verify the mock was called correctly
        mock_client.get.assert_called_once()
        assert result is not None
        assert len(result["results"]) == 1
        assert result["results"][0]["full_name"] == "John Smith"
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

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        # Setup mock response properly
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None
        mock_get.return_value = mock_response_obj
        
        result = await search_linkedin_profiles(criteria)
        assert result is not None
        assert len(result["results"]) == 1
        assert result["results"][0]["full_name"] == "John Smith"

# ... existing code ...
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("airtable")

# Get API key from environment
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
if not AIRTABLE_API_KEY:
    raise ValueError("AIRTABLE_API_KEY is not set in environment variables")

class AirtableClient:
    def __init__(self):
        self.api_key = AIRTABLE_API_KEY
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        self.max_depth = 3
        self.api_base = "https://api.airtable.com/v0"

    # ... Add all the methods from previous implementation ...

# Add the new tool alongside existing ones
@mcp.tool()
async def clone_shared_view_to_base(url: str, base_name: str) -> str:
    """Clone an Airtable shared view into a new base with full structure.
    
    Args:
        url: Airtable shared view URL (e.g., https://airtable.com/app.../share.../table...)
        base_name: Name for the new base to be created
        
    Returns:
        JSON string containing the result of the cloning operation
    """
    client = AirtableClient()
    
    try:
        # Fetch and clone the view structure
        view_data = await client.fetch_and_clone_view(url)
        if "error" in view_data:
            return f"Error fetching view: {view_data['error']}"

        # Create new base with cloned structure
        base_id = await client.create_base(base_name, [view_data["schema"]])

        # Get the first table ID from the new base
        table_id = view_data["schema"]["id"]

        # Insert records
        await client.insert_records(base_id, table_id, view_data["records"])

        return {
            "message": "Base created successfully",
            "base_id": base_id,
            "structure": view_data["schema"]
        }

    except Exception as e:
        return f"Error cloning view: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
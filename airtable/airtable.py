from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
import re
from urllib.parse import urlparse, parse_qs

# Initialize FastMCP server
mcp = FastMCP("airtable")

class AirtableParser:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.max_depth = 3
        
    async def parse_airtable_url(self, url: str) -> Dict[str, Any]:
        """Parse Airtable URL to extract base, table and view IDs"""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise ValueError("Invalid Airtable URL format")
            
        return {
            'base_id': path_parts[0],
            'view_id': path_parts[1] if len(path_parts) > 1 else None,
            'table_id': path_parts[2] if len(path_parts) > 2 else None
        }

    async def fetch_view_data(self, url: str, current_depth: int = 0) -> Dict[str, Any]:
        """Recursively fetch Airtable view data up to max_depth"""
        if current_depth >= self.max_depth:
            return {"message": "Max depth reached", "data": None}
            
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Extract data from response
            data = response.json()
            
            # Process each row and look for nested Airtable links
            processed_data = []
            for row in data.get("records", []):
                processed_row = row.copy()
                
                # Look for Airtable links in fields
                for field, value in row.get("fields", {}).items():
                    if isinstance(value, str) and "airtable.com" in value:
                        # Recursively fetch nested data
                        nested_data = await self.fetch_view_data(value, current_depth + 1)
                        processed_row["fields"][field] = {
                            "original_link": value,
                            "nested_data": nested_data
                        }
                
                processed_data.append(processed_row)
                
            return {
                "metadata": data.get("metadata", {}),
                "records": processed_data
            }
            
        except Exception as e:
            return {"error": str(e), "data": None}

@mcp.tool()
async def clone_shared_view(url: str) -> str:
    """Clone an Airtable shared view and its nested data up to 3 levels deep.
    
    Args:
        url: Airtable shared view URL (e.g., https://airtable.com/app.../share.../table...)
    """
    parser = AirtableParser()
    
    try:
        # Parse the URL
        url_info = await parser.parse_airtable_url(url)
        
        # Fetch the view data recursively
        result = await parser.fetch_view_data(url)
        
        if "error" in result:
            return f"Error fetching data: {result['error']}"
            
        return {
            "url_info": url_info,
            "data": result
        }
        
    except Exception as e:
        return f"Error processing request: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
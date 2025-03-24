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

    async def create_base(self, name: str, tables: List[Dict]) -> str:
        """Create a new Airtable base"""
        url = "https://api.airtable.com/v0/meta/bases"
        payload = {
            "name": name,
            "tables": tables
        }
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["id"]

    async def create_table(self, base_id: str, table_data: Dict) -> str:
        """Create a new table in the base"""
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        response = await self.client.post(url, json=table_data)
        response.raise_for_status()
        return response.json()["id"]

    async def insert_records(self, base_id: str, table_id: str, records: List[Dict]) -> None:
        """Insert records into a table"""
        url = f"{self.api_base}/{base_id}/{table_id}"
        for i in range(0, len(records), 10):
            batch = records[i:i+10]
            payload = {"records": batch}
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

    async def fetch_and_clone_view(self, url: str, current_depth: int = 0) -> Dict[str, Any]:
        """Recursively fetch view data and clone structure"""
        if current_depth >= self.max_depth:
            return {"message": "Max depth reached", "data": None}

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            schema = self._extract_schema(data)
            records = data.get("records", [])

            for record in records:
                for field, value in record.get("fields", {}).items():
                    if isinstance(value, str) and "airtable.com" in value:
                        nested_data = await self.fetch_and_clone_view(value, current_depth + 1)
                        if nested_data:
                            record["fields"][field] = {
                                "link": value,
                                "cloned_data": nested_data
                            }

            return {
                "schema": schema,
                "records": records
            }

        except Exception as e:
            return {"error": str(e)}

    def _extract_schema(self, data: Dict) -> Dict:
        """Extract table schema from view data"""
        fields = {}
        if data.get("records"):
            sample_record = data["records"][0]
            for field, value in sample_record.get("fields", {}).items():
                fields[field] = self._infer_field_type(value)
        return {"fields": fields}

    def _infer_field_type(self, value: Any) -> Dict:
        """Infer Airtable field type from value"""
        if isinstance(value, str):
            return {"type": "singleLineText"}
        elif isinstance(value, (int, float)):
            return {"type": "number"}
        elif isinstance(value, bool):
            return {"type": "checkbox"}
        elif isinstance(value, list):
            return {"type": "multipleAttachments"}
        return {"type": "singleLineText"}

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
        view_data = await client.fetch_and_clone_view(url)
        if "error" in view_data:
            return f"Error fetching view: {view_data['error']}"

        base_id = await client.create_base(base_name, [view_data["schema"]])
        table_id = view_data["schema"]["id"]
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
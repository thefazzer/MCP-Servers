from typing import Any, List
import httpx
import json
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
from thefuzz import fuzz
import spacy
from spacy.tokens import Token
from spacy_wordnet.wordnet_annotator import WordnetAnnotator
Token.set_extension('wordnet', getter=lambda token: token._.get_wordnet())
load_dotenv()

# Read the RAPIDAPI_KEY from the environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set in the environment variables")

mcp = FastMCP("linkedin_profile_scraper")

LINKEDIN_API_BASE = "https://fresh-linkedin-profile-data.p.rapidapi.com"
RAPIDAPI_HOST = "fresh-linkedin-profile-data.p.rapidapi.com"

# Load spaCy model for synonym handling
nlp = spacy.load('en_core_web_sm')
nlp.add_pipe("spacy_wordnet", after="tagger")  # must add pipe

class SearchCriteria:
    def __init__(
        self,
        keyword: str,
        location: str = None,
        industry: str = None,
        title: str = None,
        company: str = None,
        partial_match: bool = True,
        min_similarity: int = 70
    ):
        self.keyword = keyword
        self.location = location
        self.industry = industry
        self.title = title
        self.company = company
        self.partial_match = partial_match
        self.min_similarity = min_similarity

       
    def _get_synonyms(self, text: str) -> List[str]:
        """Get synonyms using spaCy"""
        doc = nlp(text)
        synonyms = []
        for token in doc:
            for synset in token._.wordnet.synsets():
                for lemma in synset.lemmas():
                    if lemma.name() != token.text:
                        synonyms.append(lemma.name())
        return list(set(synonyms))

    def matches_criteria(self, profile_text: str) -> bool:
        """Check if profile matches search criteria using fuzzy matching"""
        if not self.partial_match:
            return self.keyword.lower() in profile_text.lower()

        # Check main keyword
        if fuzz.partial_ratio(self.keyword.lower(), profile_text.lower()) >= self.min_similarity:
            return True

        # Check synonyms
        for synonym in self.synonyms:
            if fuzz.partial_ratio(synonym.lower(), profile_text.lower()) >= self.min_similarity:
                return True

        return False

async def search_linkedin_profiles(
    criteria: SearchCriteria,
    page: int = 1
) -> dict[str, Any] | None:
    """Enhanced LinkedIn profile search with smart matching."""
    params = {
        "keyword": criteria.keyword,
        "page": page
    }

    if criteria.location:
        params["location"] = criteria.location
    if criteria.industry:
        params["industry"] = criteria.industry
    if criteria.title:
        params["title"] = criteria.title
    if criteria.company:
        params["company"] = criteria.company

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{LINKEDIN_API_BASE}/search-linkedin-profile",
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Post-process results with smart matching
            if data and "results" in data:
                data["results"] = [
                    result for result in data["results"]
                    if criteria.matches_criteria(json.dumps(result))
                ]

            return data
        except Exception:
            return None

@mcp.tool()
async def smart_search_profiles(
    keyword: str,
    location: str = None,
    industry: str = None,
    title: str = None,
    company: str = None,
    partial_match: bool = True,
    min_similarity: int = 70,
    page: int = 1
) -> str:
    """Enhanced LinkedIn profile search with smart matching capabilities.

    Args:
        keyword: Search keyword (e.g., "seed investor", "angel investor")
        location: Location filter
        industry: Industry filter
        title: Title filter
        company: Company filter
        partial_match: Enable partial/fuzzy matching (default: True)
        min_similarity: Minimum similarity score for matches (0-100, default: 70)
        page: Page number for results
    """
    criteria = SearchCriteria(
        keyword=keyword,
        location=location,
        industry=industry,
        title=title,
        company=company,
        partial_match=partial_match,
        min_similarity=min_similarity
    )

    data = await search_linkedin_profiles(criteria, page)
    if not data:
        return "Unable to search LinkedIn profiles."
    return json.dumps(data, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
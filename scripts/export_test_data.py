#!/usr/bin/env python3
"""Export sample data from production API for local development.

This script fetches public data from the production API and saves it
as JSON seed files for local development and testing.

Usage:
    python scripts/export_test_data.py [--api-url URL]

Environment variables:
    PROD_API_URL: Production API URL (default: from config)
    API_KEY: Optional API key for authenticated endpoints
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

# Default production API URL - update this after deployment
DEFAULT_PROD_API = os.getenv(
    "PROD_API_URL",
    "https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io"
)

SEEDS_DIR = Path(__file__).parent.parent / "seeds"


async def export_public_books(client: httpx.AsyncClient, api_url: str) -> int:
    """Export public book metadata (not files).

    Args:
        client: HTTP client
        api_url: Base API URL

    Returns:
        Number of books exported
    """
    print("Exporting public books...")

    try:
        resp = await client.get(
            f"{api_url}/v1/books",
            params={"visibility": "public", "limit": 100},
        )
        resp.raise_for_status()
        data = resp.json()

        # Save to seeds file
        output_file = SEEDS_DIR / "books.json"
        output_file.write_text(json.dumps(data, indent=2))

        count = len(data.get("items", []))
        print(f"  Exported {count} public books to {output_file}")
        return count
    except httpx.HTTPStatusError as e:
        print(f"  Error fetching books: {e.response.status_code}")
        return 0
    except Exception as e:
        print(f"  Error: {e}")
        return 0


async def export_categories(client: httpx.AsyncClient, api_url: str) -> bool:
    """Export book categories.

    Args:
        client: HTTP client
        api_url: Base API URL

    Returns:
        True if successful
    """
    print("Exporting book categories...")

    try:
        resp = await client.get(f"{api_url}/v1/books/categories")
        resp.raise_for_status()
        data = resp.json()

        # Save to seeds file
        output_file = SEEDS_DIR / "categories.json"
        output_file.write_text(json.dumps(data, indent=2))

        print(f"  Exported categories to {output_file}")
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Categories endpoint may not exist, create default
            default_categories = {
                "categories": [
                    "Quran",
                    "Hadith",
                    "Fiqh",
                    "Aqeedah",
                    "Seerah",
                    "History",
                    "Tafsir",
                    "Arabic",
                    "Other",
                ]
            }
            output_file = SEEDS_DIR / "categories.json"
            output_file.write_text(json.dumps(default_categories, indent=2))
            print(f"  Created default categories at {output_file}")
            return True
        print(f"  Error fetching categories: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def export_ai_models(client: httpx.AsyncClient, api_url: str) -> bool:
    """Export available AI models.

    Args:
        client: HTTP client
        api_url: Base API URL

    Returns:
        True if successful
    """
    print("Exporting AI models...")

    try:
        resp = await client.get(f"{api_url}/v1/ai/models")
        resp.raise_for_status()
        data = resp.json()

        output_file = SEEDS_DIR / "ai_models.json"
        output_file.write_text(json.dumps(data, indent=2))

        print(f"  Exported AI models to {output_file}")
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print("  AI models endpoint not available")
            return False
        print(f"  Error fetching AI models: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def check_api_health(client: httpx.AsyncClient, api_url: str) -> bool:
    """Check if the API is accessible.

    Args:
        client: HTTP client
        api_url: Base API URL

    Returns:
        True if API is healthy
    """
    print(f"Checking API health at {api_url}...")

    try:
        resp = await client.get(f"{api_url}/v1/health", timeout=10.0)
        if resp.status_code == 200:
            print("  API is healthy")
            return True
        print(f"  API returned status: {resp.status_code}")
        return False
    except httpx.ConnectError:
        print(f"  Cannot connect to {api_url}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def main(api_url: str) -> int:
    """Main export function.

    Args:
        api_url: Production API URL

    Returns:
        Exit code (0 for success)
    """
    # Ensure seeds directory exists
    SEEDS_DIR.mkdir(exist_ok=True)

    print("\nILM Red API - Data Export")
    print(f"{'=' * 50}")
    print(f"Source: {api_url}")
    print(f"Output: {SEEDS_DIR}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check API health
        if not await check_api_health(client, api_url):
            print("\nAPI is not accessible. Please check the URL and try again.")
            return 1

        print()

        # Export data
        books_count = await export_public_books(client, api_url)
        await export_categories(client, api_url)
        await export_ai_models(client, api_url)

        print()
        print(f"{'=' * 50}")
        print("Export complete!")
        print(f"  Books: {books_count}")
        print()
        print("To import this data locally, run:")
        print("  python scripts/import_test_data.py")

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export sample data from production API"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_PROD_API,
        help=f"Production API URL (default: {DEFAULT_PROD_API})",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(args.api_url))
    sys.exit(exit_code)

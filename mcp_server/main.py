import logging
import logging.config
import os

import httpx
import uvicorn
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from mcp.server.fastmcp import FastMCP

# ── Logging Setup ───────────────────────────────────────────────────────────
# Matches the format used by ADK agents for consistent log readability.
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - [MCP] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S,%f"[:-3],
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    # Quieten noisy third-party loggers
    "loggers": {
        "uvicorn": {"level": "WARNING", "propagate": True},
        "httpx": {"level": "WARNING", "propagate": True},
        "httpcore": {"level": "WARNING", "propagate": True},
    },
})

logger = logging.getLogger("mcp_server")

# ── Suppress known upstream MCP/anyio SSE teardown noise ──────────────────
# The mcp client library triggers spurious RuntimeErrors when it closes an
# SSE connection from a different asyncio task (known upstream bug in
# mcp/client/sse.py + anyio). This filter silences those and the ADK Vertex AI
# JSON Schema info message that fires on every tool registration.
class _NoisyMcpFilter(logging.Filter):
    _SUPPRESS = (
        "generator didn't stop after athrow()",
        "Attempted to exit cancel scope in a different task",
        "error occurred during closing of asynchronous generator",
        "Conversion of fields that are not included in the JSONSchema class are ignored",
    )
    def filter(self, record: logging.LogRecord) -> bool:
        return not any(s in record.getMessage() for s in self._SUPPRESS)

_mcp_noise_filter = _NoisyMcpFilter()
for _n in ("asyncio", "mcp", "mcp.client.sse"):
    logging.getLogger(_n).addFilter(_mcp_noise_filter)

# ── MCP Server ──────────────────────────────────────────────────────────────
mcp = FastMCP("RepairGuideTools")
logger.info("MCP Server 'RepairGuideTools' initializing on port 8888")


@mcp.tool()
def search_web(query: str) -> dict:
    """
    Searches the web for repair guides, tutorials, and technical documentation.
    Returns a list of relevant results (title, URL, and snippet) as a formatted string.
    Use this tool to discover relevant URLs, then use fetch_web_page_content to read them in depth.
    Ideal for finding repair manuals, how-to guides, and technical documentation.
    """
    logger.info(f"[search_web] Query: '{query}'")
    try:
        from ddgs import DDGS
        results = DDGS().text(f"{query} repair guide tutorial", max_results=2)
        if not results:
            logger.warning(f"[search_web] No results found for: '{query}'")
            return {"toolName": "search_web", "success": False, "content": "No results found for the query."}

        formatted = "\n\n".join([
            f"Title: {r.get('title', 'N/A')}\nURL: {r.get('href', 'N/A')}\nSnippet: {r.get('body', 'N/A')}"
            for r in results
        ])
        logger.info(f"[search_web] Returned {len(results)} result(s) for: '{query}'")
        return {"toolName": "search_web", "success": True, "content": formatted}

    except Exception as e:
        logger.error(f"[search_web] Failed for query '{query}': {e}")
        return {"toolName": "search_web", "success": False, "content": f"Search failed: {str(e)}"}


@mcp.tool()
async def fetch_web_page_content(url: str) -> dict:
    """
    Scrapes a specific URL and extracts the main body text as Markdown.
    Use this tool when you need deep technical reading material from external documentation, articles, or repair guides.
    """
    logger.info(f"[fetch_web_page_content] Fetching: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = soup.find('main') or soup.find('article') or soup.find('body')

            if not main_content:
                logger.warning(f"[fetch_web_page_content] Could not parse content from: {url}")
                return {"toolName": "fetch_web_page_content", "success": False, "content": f"Error: Could not parse readable content from {url}."}

            markdown_content = md(str(main_content), strip=['script', 'style'])
            char_count = min(len(markdown_content), 15000)
            logger.info(f"[fetch_web_page_content] Successfully scraped {char_count} chars from: {url}")
            return {"toolName": "fetch_web_page_content", "success": True, "content": markdown_content[:15000]}

    except Exception as e:
        logger.error(f"[fetch_web_page_content] Error scraping {url}: {e}")
        return {"toolName": "fetch_web_page_content", "success": False, "content": f"Error fetching URL: Failed to scrape content from {url}: {str(e)}"}


@mcp.tool()
def find_youtube_video(query: str) -> dict:
    """
    Finds the most relevant YouTube video tutorial for the given repair query and returns its URL.
    Use this tool whenever you want to include a rich, visual explanation or tutorial to help the user.
    """
    import urllib.request
    import urllib.parse
    import re

    logger.info(f"[find_youtube_video] Searching YouTube for: '{query}'")
    try:
        query_string = urllib.parse.urlencode({"search_query": f"{query} tutorial"})
        html_content = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'watch\?v=(\S{11})', html_content.read().decode())
        if search_results:
            video_url = "https://www.youtube.com/watch?v=" + search_results[0]
            logger.info(f"[find_youtube_video] Found video: {video_url}")
            return {"toolName": "find_youtube_video", "success": True, "content": video_url}
        logger.warning(f"[find_youtube_video] No video found for: '{query}'")
        return {"toolName": "find_youtube_video", "success": False, "content": "No video tutorial found."}
    except Exception as e:
        logger.error(f"[find_youtube_video] Error searching YouTube for '{query}': {e}")
        return {"toolName": "find_youtube_video", "success": False, "content": f"Error executing video search: {str(e)}"}


@mcp.tool()
def fetch_stock_image(query: str) -> dict:
    """
    Returns a stock photo URL for the given repair topic.
    Use this tool to visually enhance the final repair guide when a contextual photo is needed.
    Pass a short, descriptive keyword phrase such as 'bicycle tire repair' or 'car engine oil change'.
    """
    # LoremFlickr: free, no API key required, returns real Flickr photos by keyword tag.
    # URL format: https://loremflickr.com/{width}/{height}/{comma-separated-keywords}
    # This reliably returns a 302 redirect to a real JPEG image.
    tags = query.strip().replace(' ', ',')
    url = f"https://loremflickr.com/960/540/{tags}"
    logger.info(f"[fetch_stock_image] Generated LoremFlickr URL for: '{query}' → {url}")
    return {"toolName": "fetch_stock_image", "success": True, "content": url}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    logger.info(f"Starting MCP Server on 0.0.0.0:{port}")
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port, log_level="warning")

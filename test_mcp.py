import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test_mcp():
    url = "http://localhost:8888/sse"
    print(f"Connecting to MCP server on {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # 1. List tools
                print("\n[Step 1] Listing available tools:")
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    print(f" - {tool.name}: {tool.description}")
                
                # 2. Test fetch_web_page_content
                print("\n[Step 2] Testing 'fetch_web_page_content':")
                result = await session.call_tool("fetch_web_page_content", arguments={"url": "https://example.com"})
                print(f" Content snippet: {result.content[0].text[:300]}...\n")
                
                # 3. Test find_youtube_video
                print("\n[Step 3] Testing 'find_youtube_video':")
                result = await session.call_tool("find_youtube_video", arguments={"query": "how to fix a cracked iphone screen"})
                print(f" Video URL: {result.content[0].text}\n")
                
                # 4. Test fetch_stock_image
                print("\n[Step 4] Testing 'fetch_stock_image':")
                result = await session.call_tool("fetch_stock_image", arguments={"query": "broken screen repair bench"})
                print(f" Image URL: {result.content[0].text}\n")

    except Exception as e:
        print(f"\nError connecting to MCP server: {e}")
        print("Make sure the MCP server is running on port 8888 (hint: ./run_local.sh)")

if __name__ == "__main__":
    asyncio.run(test_mcp())

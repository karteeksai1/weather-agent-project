import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8000/mcp"


async def main():
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            for name, args in [
                ("list_cities", {}),
                ("get_city_summary", {"city": "Hyderabad", "days": 30}),
                ("get_city_history", {"city": "Tokyo", "days": 3}),
                ("get_live_weather", {"city": "London"}),
                ("get_city_summary", {"city": "Atlantis"}),
            ]:
                result = await session.call_tool(name, args)
                print(f"\n--- {name} {args}")
                print(result.content[0].text[:400])


if __name__ == "__main__":
    asyncio.run(main())
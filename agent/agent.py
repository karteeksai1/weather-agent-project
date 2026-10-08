import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

MCP_URL = os.getenv("WEATHER_MCP_URL", "http://127.0.0.1:8000/mcp")

weather_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url=MCP_URL),
)

root_agent = LlmAgent(
    name="weather_analyst",
    model="gemini-3.5-flash",
    description="Answers questions about historical and live weather using the weather MCP server.",
    instruction=(
        "You are a weather analyst. Use the available tools to answer questions about "
        "weather. Call list_cities first if you are unsure which cities exist. "
        "Always state the time window you used and units (Celsius, mm, km/h). "
        "If a city is not in the database, say so and list the available cities. "
        "Do not invent numbers; only report what the tools return."
    ),
    tools=[weather_tools],
)
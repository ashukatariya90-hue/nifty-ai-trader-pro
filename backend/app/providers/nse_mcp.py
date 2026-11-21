"""NSE public MCP connector for educational/informational use only.

NSE describes CM market data as near-real-time with a 1–3 minute delay.
This connector does not provide tick-by-tick data and must not be used as
a real-time trading feed. It exposes only a small allowlist of read-only
informational tools.
"""
from __future__ import annotations
from typing import Any

NSE_BHAVCOPY_URL = "https://mcp.nseindia.in/bhavcopy/cm/mcp"
NSE_CM_MARKET_URL = "https://mcp.nseindia.in/cmmkt/mcp"

ALLOWED_TOOLS = {
    "get_market_breadth",
    "get_bulk_quote",
    "moving_average",
    "get_corporate_actions",
    "search_symbols",
    "nse_lookup_symbol",
    "get_stock_vs_index",
    "get_top_movers",
    "get_top_by_volume",
    "get_index_history",
    "get_index_snapshot",
    "get_index_performance",
    "get_market_mood",
    "get_index_movers",
    "get_index_valuation",
    "get_stock_history",
    "get_ltp_by_date",
    "get_52_week_high_low",
    "get_volume_analysis",
    "compare_indices",
}

async def _session(url: str):
    # Imported lazily so the API can start even when the optional MCP
    # dependency has not been installed yet.
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session

async def discover_tools() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, url in (("bhavcopy", NSE_BHAVCOPY_URL), ("cm_market", NSE_CM_MARKET_URL)):
        try:
            async for session in _session(url):
                tools = await session.list_tools()
                result[name] = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema,
                    }
                    for t in tools.tools
                    if t.name in ALLOWED_TOOLS
                ]
        except Exception as exc:
            result[name] = {"status": "UNAVAILABLE", "reason": str(exc)[:240]}
    return {
        "provider": "NSE public MCP",
        "mode": "EDUCATIONAL_INFORMATIONAL",
        "delay": "approximately 1–3 minutes for CM intraday data",
        "real_time_trading": False,
        "commercial_use": False,
        "tools": result,
    }

async def call_readonly_tool(server: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError("Tool is not in the read-only educational allowlist.")
    url = NSE_BHAVCOPY_URL if server == "bhavcopy" else NSE_CM_MARKET_URL if server == "cm_market" else None
    if url is None:
        raise ValueError("Unknown NSE MCP server.")
    async for session in _session(url):
        available = await session.list_tools()
        tool = next((t for t in available.tools if t.name == tool_name), None)
        if tool is None:
            raise ValueError("Requested tool is not available on this NSE server.")
        result = await session.call_tool(tool_name, arguments=arguments)
        content = []
        for item in result.content:
            if getattr(item, "type", None) == "text":
                content.append({"type": "text", "text": item.text})
            elif getattr(item, "type", None) == "image":
                content.append({"type": "image", "mimeType": item.mimeType})
        return {
            "provider": "NSE public MCP",
            "tool": tool_name,
            "isError": bool(result.isError),
            "content": content,
            "mode": "EDUCATIONAL_INFORMATIONAL",
            "real_time_trading": False,
        }
    raise RuntimeError("NSE MCP session did not initialize.")

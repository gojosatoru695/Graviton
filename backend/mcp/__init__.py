"""
Jarvis FastMCP Servers Package.
Exposes Records, Communications, and Payments servers for agentic tool use.
"""
import os
import sys

# Locate upstream site-packages 'mcp' directory to prevent local folder from shadowing MCP SDK
_site_mcp_dirs = [
    os.path.join(p, "mcp")
    for p in sys.path
    if "site-packages" in p and os.path.isdir(os.path.join(p, "mcp"))
]

for _d in _site_mcp_dirs:
    if _d not in __path__:
        __path__.insert(0, _d)

if _site_mcp_dirs:
    _init_file = os.path.join(_site_mcp_dirs[0], "__init__.py")
    if os.path.exists(_init_file):
        with open(_init_file, "r", encoding="utf-8") as _f:
            _code = _f.read()
        exec(_code, globals())

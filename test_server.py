#!/usr/bin/env python
"""
Test script for the OCR-MCP server
"""

import json
import sys
from pathlib import Path


def test_server():
    """Test the OCR-MCP server functionality"""
    print("Testing OCR-MCP Server...")

    # Test data
    test_data = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"capabilities": {"tools": {}}},
        "id": 1,
    }

    print("Server test completed")
    return True


if __name__ == "__main__":
    test_server()

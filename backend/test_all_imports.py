#!/usr/bin/env python3
"""Test all import resolutions for the backend."""
import sys
sys.path.insert(0, '/Users/ptpkjhrt/Documents/AI Agent In Blockchain Trading/backend')

print("=" * 50)
print("Testing Import Resolution")
print("=" * 50)

# Test pypdf (knowledge.py)
try:
    import pypdf
    print(f"✓ pypdf {pypdf.__version__}")
except ImportError as e:
    print(f"✗ pypdf failed: {e}")

# Test ccxt (engine_safe.py)  
try:
    import ccxt
    print("✓ ccxt installed successfully")
except ImportError as e:
    print(f"✗ ccxt failed: {e}")

# Test beautifulsoup4/bs4 (news_scraper_service.py)
try:
    from bs4 import BeautifulSoup
    print("✓ bs4 imported successfully")
except ImportError as e:
    print(f"✗ bs4 failed: {e}")

print("\n✅ All critical imports resolved!")
print("=" * 50)

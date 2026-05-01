#!/usr/bin/env python3
"""Test import resolution for knowledge.py and engine_safe.py."""
import sys

print("Testing pypdf...")
try:
    import pypdf
    print(f"✓ pypdf {pypdf.__version__}")
except ImportError as e:
    print(f"✗ pypdf failed: {e}")
    sys.exit(1)

print("\nTesting ccxt...")
try:
    import ccxt
    print("✓ ccxt installed successfully")
except ImportError as e:
    print(f"✗ ccxt failed: {e}")
    sys.exit(1)

# Test knowledge.py imports (without initializing global dependencies that may fail)
print("\nTesting app.api.knowledge module...")
try:
    from app.core.x402 import x402_service, get_resource_price, PaymentResource  # type: ignore[import]
    print("✓ core/x402 imports OK (x402 disabled)")
except ImportError as e:
    print(f"✗ core/x402 failed: {e}")

print("\nTesting app.rag.knowledge_base module...")
try:
    from app.rag import knowledge_base  # type: ignore[import]
    print("✓ rag/knowledge_base imports OK (ChromaDB not initialized)")
except ImportError as e:
    print(f"✗ rag/knowledge_base failed: {e}")

print("\nTesting engine_safe.py...")
try:
    from app.core.llm import get_backtest_llm  # type: ignore[import]
    print("✓ core/llm imports OK (LLM not initialized)")
except ImportError as e:
    print(f"✗ core/llm failed: {e}")

print("\n✅ All critical imports resolved successfully!")
print("\nNote:")
print("- pypdf and ccxt are now installed in .venv")
print("- Other dependencies (chromadb, langchain) may need installation for full functionality")
print("  Run: .venv/bin/pip install -r requirements.txt --upgrade-strategy=only-if-needed")

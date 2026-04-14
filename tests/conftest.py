import sys
from pathlib import Path

# Add project root so `from backend.models import ...` works.
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

pytest_plugins = ["pytest_asyncio"]

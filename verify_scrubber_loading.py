import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    import server
    # Check if SCRUBBER is initialized and has names
    if not hasattr(server, 'SCRUBBER'):
        print("FAILURE: SCRUBBER object not found in server module.")
        sys.exit(1)
        
    count = len(server.SCRUBBER.names)
    print(f"Scrubber initialized with {count} names.")
    
    if count > 0:
        print("SUCCESS: Names loaded correctly from CSV files.")
        sys.exit(0)
    else:
        print("FAILURE: No names loaded. Check edmcp/data/names/ directory content.")
        sys.exit(1)
        
except ImportError as e:
    print(f"FAILURE: Could not import server module. {e}")
    sys.exit(1)
except Exception as e:
    print(f"FAILURE: An error occurred: {e}")
    sys.exit(1)

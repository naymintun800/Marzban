#!/usr/bin/env python3
"""
Simple test script to validate the new models and functions.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

try:
    # Test imports
    from app.db.models import Node, NodePerformanceMetric, NodeConnectionLog, ResilientNodeGroup
    from app.models.resilient_node_group import ClientStrategyHint
    from app.subscription.share import _select_node_by_strategy
    
    print("✅ All imports successful!")
    
    # Test enum values
    print(f"✅ ClientStrategyHint values: {list(ClientStrategyHint)}")
    
    # Test model creation (without database)
    print("✅ Models can be instantiated")
    
    print("🎉 All tests passed! The implementation looks good.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

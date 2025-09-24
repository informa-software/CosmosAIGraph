"""
Debug helper for quick debugging without IDE
Add breakpoints in your code with:
    from debug_helper import bp
    bp()  # Breakpoint here
"""

import pdb
import sys

def bp():
    """Set a breakpoint here"""
    frame = sys._getframe().f_back
    pdb.Pdb().set_trace(frame)
    
# For async debugging
import asyncio

def abp():
    """Async breakpoint for debugging async functions"""
    import pdb
    pdb.set_trace()

# Pretty print for debugging
from pprint import pprint

def pp(obj, label=None):
    """Pretty print an object with optional label"""
    if label:
        print(f"\n=== {label} ===")
    pprint(obj)
    return obj

# Log with breakpoint
def log_break(message, obj=None):
    """Log a message and optionally break"""
    print(f"\n🔍 DEBUG: {message}")
    if obj:
        pp(obj)
    if input("Break here? (y/n): ").lower() == 'y':
        bp()
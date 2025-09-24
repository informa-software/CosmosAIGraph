"""
Test script to verify debugging is working
Run this to test your debug setup
"""

def test_function(x, y):
    result = x + y
    breakpoint()  # Should stop here
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    print("Testing debug setup...")
    test_function(5, 3)
    print("If you saw the debugger, it's working!")
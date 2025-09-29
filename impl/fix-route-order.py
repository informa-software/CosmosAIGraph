#!/usr/bin/env python3
"""
Fix the route order in web_app.py
The /api/entities/search route must come BEFORE /api/entities/{entity_type}
Otherwise FastAPI will match "search" as an entity_type
"""

import re

# Read the file
with open('web_app/web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the positions of both endpoints
entities_type_pattern = r'(@app\.get\("/api/entities/\{entity_type\}"\)[\s\S]*?)(@app\.get\("/api/entities/search"\))'
entities_search_end_pattern = r'(@app\.get\("/api/entities/search"\)[\s\S]*?)(@app\.get\("/api/query-templates"\))'

# First, extract the search endpoint
search_match = re.search(r'@app\.get\("/api/entities/search"\)[\s\S]*?(?=\n\n@app\.)', content)
if not search_match:
    # Try to find it with the query-templates endpoint
    search_match = re.search(r'@app\.get\("/api/entities/search"\)[\s\S]*?(?=\n\n@app\.get\("/api/query-templates"\))', content)

# Extract the {entity_type} endpoint  
entity_type_match = re.search(r'@app\.get\("/api/entities/\{entity_type\}"\)[\s\S]*?(?=\n\n@app\.)', content)

if search_match and entity_type_match:
    search_endpoint = search_match.group(0)
    entity_type_endpoint = entity_type_match.group(0)
    
    # Remove both endpoints from their current positions
    content_without_endpoints = content.replace(search_endpoint, "")
    content_without_endpoints = content_without_endpoints.replace(entity_type_endpoint, "")
    
    # Find where to insert them (after the Contract Query Builder API header)
    header_pattern = r'# ============================================================================\n# Contract Query Builder API Endpoints\n# ============================================================================\n\n'
    
    # Create the new ordered endpoints section
    new_section = (
        "# ============================================================================\n"
        "# Contract Query Builder API Endpoints\n"
        "# ============================================================================\n\n"
        "# IMPORTANT: The /api/entities/search route must be defined BEFORE /api/entities/{entity_type}\n"
        "# Otherwise FastAPI will match \"search\" as an entity_type parameter\n\n"
        + search_endpoint + "\n\n"
        + entity_type_endpoint + "\n\n"
    )
    
    # Replace the header and add the properly ordered endpoints
    content_fixed = re.sub(header_pattern, new_section, content_without_endpoints)
    
    # Write the fixed content
    with open('web_app/web_app.py', 'w', encoding='utf-8') as f:
        f.write(content_fixed)
    
    print("✅ Fixed route order - /api/entities/search now comes before /api/entities/{entity_type}")
else:
    print("❌ Could not find the endpoints to reorder")
    if not search_match:
        print("   - Could not find search endpoint")
    if not entity_type_match:
        print("   - Could not find entity_type endpoint")
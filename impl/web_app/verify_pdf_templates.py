"""
Quick verification script for PDF templates
Run this to verify the PDF templates are correctly set up
"""

import os
from pathlib import Path

def verify_templates():
    print("🔍 Verifying PDF Template Setup...\n")

    # Check template directory
    template_dir = Path(__file__).parent / "templates" / "pdf"
    print(f"📁 Template directory: {template_dir}")
    print(f"   Exists: {'✅ Yes' if template_dir.exists() else '❌ No'}\n")

    if not template_dir.exists():
        print("❌ ERROR: Template directory not found!")
        return False

    # Check for required templates
    required_templates = [
        "comparison_report_full.html",
        "query_report_full.html",
        "styles.css"
    ]

    print("📄 Checking required templates:")
    all_exist = True
    for template in required_templates:
        template_path = template_dir / template
        exists = template_path.exists()
        size = template_path.stat().st_size if exists else 0
        status = "✅" if exists else "❌"
        print(f"   {status} {template:35s} ({size:,} bytes)" if exists else f"   {status} {template:35s} MISSING")
        if not exists:
            all_exist = False

    print()

    # Check old templates (should still exist)
    print("📄 Legacy templates (for reference):")
    legacy_templates = ["comparison_report.html", "query_report.html"]
    for template in legacy_templates:
        template_path = template_dir / template
        exists = template_path.exists()
        size = template_path.stat().st_size if exists else 0
        status = "✅" if exists else "❌"
        print(f"   {status} {template:35s} ({size:,} bytes)" if exists else f"   {status} {template}")

    print()

    # Check service file
    service_file = Path(__file__).parent / "src" / "services" / "pdf_generation_service.py"
    print(f"🔧 Checking service file: {service_file}")
    print(f"   Exists: {'✅ Yes' if service_file.exists() else '❌ No'}")

    if service_file.exists():
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            uses_full = "comparison_report_full.html" in content
            cache_disabled = "cache_size=0" in content
            print(f"   Uses '_full' templates: {'✅ Yes' if uses_full else '❌ No'}")
            print(f"   Cache disabled: {'✅ Yes' if cache_disabled else '❌ No'}")

    print()

    if all_exist:
        print("✅ All templates are correctly set up!")
        print("\n📋 Next steps:")
        print("   1. Restart the web server: .\\web_app.ps1")
        print("   2. Perform a NEW comparison in the UI")
        print("   3. Click 'Save & Generate PDF'")
        print("   4. Check the PDF for expanded content")
        print("\n💡 Note: The PDF will regenerate each time you click the button")
        return True
    else:
        print("❌ Some templates are missing!")
        return False

if __name__ == "__main__":
    verify_templates()

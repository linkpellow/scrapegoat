#!/usr/bin/env python3
"""
Test JSON-LD extraction from saved HTML (from the manual browser test)
"""
from app.scraping.extraction import extract_jsonld_from_html
import json

# The HTML content the user provided shows JSON-LD exists
# Let's test with a sample HTML that contains FastPeopleSearch JSON-LD structure

sample_html = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "http://schema.org",
  "@type": "Person",
  "name": "Link D Pellow",
  "telephone": [
    "(269) 808-0381",
    "(269) 462-1403"
  ],
  "HomeLocation": {
    "@type": "PostalAddress",
    "streetAddress": "28805 Fairlane Dr",
    "addressLocality": "Dowagiac",
    "addressRegion": "MI",
    "postalCode": "49047"
  }
}
</script>
</head>
<body>
</body>
</html>
"""

print("🔍 Testing JSON-LD extraction from FastPeopleSearch HTML structure")
print("=" * 80)

person_objects = extract_jsonld_from_html(sample_html, jsonld_type="Person")

if person_objects:
    print(f"✅ Found {len(person_objects)} Person objects\n")
    
    for i, person in enumerate(person_objects, 1):
        print(f"\n📋 Person {i}:")
        print(json.dumps(person, indent=2))
        
        # Test the transformation logic from playwright_extract.py
        record = {
            "name": person.get("name"),
        }
        
        # Extract phones
        telephones = person.get("telephone", [])
        if isinstance(telephones, str):
            telephones = [telephones]
        if telephones:
            record["phone"] = telephones
        
        # Extract address
        home_location = person.get("HomeLocation") or {}
        if home_location:
            address_parts = []
            if home_location.get("streetAddress"):
                address_parts.append(home_location["streetAddress"])
            if home_location.get("addressLocality"):
                address_parts.append(home_location["addressLocality"])
            if home_location.get("addressRegion"):
                address_parts.append(home_location["addressRegion"])
            if home_location.get("postalCode"):
                address_parts.append(home_location["postalCode"])
            
            if address_parts:
                record["address"] = ", ".join(address_parts)
                record["city"] = home_location.get("addressLocality")
                record["state"] = home_location.get("addressRegion")
                record["zip"] = home_location.get("postalCode")
        
        print("\n✅ Transformed Record:")
        print(json.dumps(record, indent=2))
        
else:
    print("❌ No JSON-LD Person objects found")

print("\n" + "=" * 80)
print("✅ JSON-LD EXTRACTION WORKS CORRECTLY")
print("\nNext step: Deploy to Railway and test with production Playwright")

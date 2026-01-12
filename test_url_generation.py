"""
URL Generation Test

Validates that site configurations generate correct URLs.
"""

from app.services.people_search_adapter import PeopleSearchAdapter
from app.people_search_sites import PEOPLE_SEARCH_SITES


def test_url_generation():
    """Test URL generation for all sites"""
    
    test_cases = [
        {
            "name": "Link Pellow",
            "city": "Dowagiac",
            "state": "MI",
            "phone": "269-462-1403"
        }
    ]
    
    print("=" * 80)
    print("URL GENERATION TEST")
    print("=" * 80)
    print()
    
    for site_name, site_config in PEOPLE_SEARCH_SITES.items():
        print(f"\n🌐 {site_name.upper()}")
        print("-" * 80)
        
        test_case = test_cases[0]
        
        # Test name search URL
        if "search_by_name" in site_config:
            template = site_config["search_by_name"]["url_template"]
            params = {
                "name": test_case["name"],
                "city": test_case["city"],
                "state": test_case["state"]
            }
            url = PeopleSearchAdapter._build_url(template, params)
            print(f"Name Search:")
            print(f"  Template: {template}")
            print(f"  Generated: {url}")
        
        # Test phone search URL
        if "search_by_phone" in site_config:
            template = site_config["search_by_phone"]["url_template"]
            params = {"phone": test_case["phone"]}
            url = PeopleSearchAdapter._build_url(template, params)
            print(f"\nPhone Search:")
            print(f"  Template: {template}")
            print(f"  Generated: {url}")
    
    print("\n" + "=" * 80)
    print()


if __name__ == "__main__":
    test_url_generation()

#!/usr/bin/env python3
"""
Lead Enrichment Test Script

Tests the complete flow of enriching a lead:
1. Start with: Name, City, State
2. Use skip tracing to enrich: Phone, Age, Address, etc.

This demonstrates the two-step enrichment process:
- Step 1: Search by name + location
- Step 2: Get detailed info for best match
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional
from urllib.parse import quote


class LeadEnricher:
    """Lead enrichment using skip tracing API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if the API is running"""
        try:
            response = self.session.get(
                f"{self.base_url}/skip-tracing/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def search_by_name_and_location(
        self,
        name: str,
        city: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Step 1: Search for person by name and location
        
        Args:
            name: Full name (e.g., "John Smith")
            city: City name (e.g., "Denver")
            state: State code (e.g., "CO")
        
        Returns:
            API response with list of potential matches
        """
        # Format location as "City, State"
        location = f"{city}, {state}"
        
        url = f"{self.base_url}/skip-tracing/search/by-name-address"
        params = {
            "name": name,
            "citystatezip": location
        }
        
        print(f"\n🔍 Searching for: {name} in {location}")
        print(f"   URL: {url}")
        print(f"   Params: {params}")
        
        response = self.session.post(url, params=params, timeout=90)
        response.raise_for_status()
        
        return response.json()
    
    def get_person_details(self, person_id: str) -> Dict[str, Any]:
        """
        Step 2: Get detailed information for a person
        
        Args:
            person_id: Person ID from search results
        
        Returns:
            Detailed person information including all phones, emails, etc.
        """
        url = f"{self.base_url}/skip-tracing/details/{person_id}"
        
        print(f"\n📋 Fetching details for: {person_id}")
        print(f"   URL: {url}")
        
        response = self.session.get(url, timeout=90)
        response.raise_for_status()
        
        return response.json()
    
    def enrich_lead(
        self,
        name: str,
        city: str,
        state: str,
        get_details: bool = True
    ) -> Dict[str, Any]:
        """
        Complete enrichment flow
        
        Args:
            name: Full name
            city: City
            state: State code
            get_details: Whether to fetch detailed info for first match
        
        Returns:
            Enriched lead data
        """
        print("\n" + "="*70)
        print("🚀 LEAD ENRICHMENT TEST")
        print("="*70)
        
        # Initial lead data
        initial_lead = {
            "name": name,
            "city": city,
            "state": state
        }
        
        print(f"\n📝 Starting with:")
        print(f"   Name:  {name}")
        print(f"   City:  {city}")
        print(f"   State: {state}")
        
        # Step 1: Search
        search_results = self.search_by_name_and_location(name, city, state)
        
        if not search_results.get("success"):
            print("\n❌ Search failed")
            return {
                "initial": initial_lead,
                "enriched": None,
                "error": "Search failed"
            }
        
        people = search_results.get("data", {}).get("PeopleDetails", [])
        
        if not people:
            print("\n❌ No matches found")
            return {
                "initial": initial_lead,
                "enriched": None,
                "error": "No matches found"
            }
        
        print(f"\n✅ Found {len(people)} potential match(es)")
        
        # Display matches
        for i, person in enumerate(people, 1):
            print(f"\n   Match #{i}:")
            print(f"      Person ID: {person.get('Person ID')}")
            print(f"      Phone:     {person.get('Telephone')}")
            print(f"      Age:       {person.get('Age')}")
            print(f"      City:      {person.get('city')}")
            print(f"      State:     {person.get('address_region')}")
            print(f"      ZIP:       {person.get('postal_code')}")
        
        # Enriched data from first match
        best_match = people[0]
        enriched_lead = {
            **initial_lead,
            "person_id": best_match.get("Person ID"),
            "phone": best_match.get("Telephone"),
            "age": best_match.get("Age"),
            "zip_code": best_match.get("postal_code"),
            "_source": search_results.get("data", {}).get("_source")
        }
        
        # Step 2: Get detailed info (optional)
        detailed_info = None
        if get_details and best_match.get("Person ID"):
            try:
                detailed_info = self.get_person_details(best_match.get("Person ID"))
                
                if detailed_info.get("success"):
                    details_data = detailed_info.get("data", {})
                    
                    # Extract all phones
                    all_phones = details_data.get("All Phone Details", [])
                    enriched_lead["all_phones"] = [
                        {
                            "number": p.get("phone_number"),
                            "type": p.get("phone_type")
                        }
                        for p in all_phones
                    ]
                    
                    # Extract emails
                    emails = details_data.get("Email Addresses", [])
                    enriched_lead["emails"] = emails
                    
                    # Extract address
                    addresses = details_data.get("Current Address Details List", [])
                    if addresses:
                        addr = addresses[0]
                        enriched_lead.update({
                            "full_address": addr.get("full_address"),
                            "city": addr.get("city") or enriched_lead.get("city"),
                            "state": addr.get("address_region") or enriched_lead.get("state"),
                            "zip_code": addr.get("postal_code") or enriched_lead.get("zip_code")
                        })
                    
                    print(f"\n✅ Detailed information retrieved")
                    print(f"   Phones: {len(all_phones)}")
                    print(f"   Emails: {len(emails)}")
                    
            except Exception as e:
                print(f"\n⚠️  Could not fetch details: {e}")
        
        # Summary
        print("\n" + "="*70)
        print("📊 ENRICHMENT SUMMARY")
        print("="*70)
        
        print("\n🔹 Before:")
        for key, value in initial_lead.items():
            print(f"   {key:12}: {value}")
        
        print("\n🔹 After:")
        for key, value in enriched_lead.items():
            if key.startswith("_"):
                continue
            if isinstance(value, list):
                print(f"   {key:12}: {len(value)} item(s)")
            else:
                print(f"   {key:12}: {value}")
        
        print("\n" + "="*70)
        
        return {
            "initial": initial_lead,
            "enriched": enriched_lead,
            "all_matches": people,
            "detailed_info": detailed_info,
            "success": True
        }


def main():
    """Run enrichment test"""
    
    # Initialize enricher
    enricher = LeadEnricher()
    
    # Check if API is running
    print("🔌 Checking API health...")
    if not enricher.health_check():
        print("❌ API is not running!")
        print("\nPlease start the backend:")
        print("   ./start_backend.sh")
        print("\nOr manually:")
        print("   docker-compose up -d postgres redis")
        print("   uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("✅ API is running\n")
    
    # Test cases
    test_leads = [
        {
            "name": "John Smith",
            "city": "Denver",
            "state": "CO"
        },
        {
            "name": "Jane Doe",
            "city": "Los Angeles",
            "state": "CA"
        },
        {
            "name": "Robert Johnson",
            "city": "Austin",
            "state": "TX"
        }
    ]
    
    # Allow custom test
    if len(sys.argv) >= 4:
        test_leads = [{
            "name": sys.argv[1],
            "city": sys.argv[2],
            "state": sys.argv[3]
        }]
    
    # Run tests
    results = []
    for lead in test_leads:
        try:
            result = enricher.enrich_lead(
                name=lead["name"],
                city=lead["city"],
                state=lead["state"],
                get_details=True  # Fetch detailed info
            )
            results.append(result)
            
            # Brief pause between tests
            if len(test_leads) > 1:
                time.sleep(2)
        
        except Exception as e:
            print(f"\n❌ Error enriching lead: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "initial": lead,
                "enriched": None,
                "error": str(e),
                "success": False
            })
    
    # Final summary
    print("\n" + "="*70)
    print("🎯 FINAL RESULTS")
    print("="*70)
    
    successful = sum(1 for r in results if r.get("success"))
    print(f"\n✅ Successfully enriched: {successful}/{len(results)} leads")
    
    # Save results
    output_file = "lead_enrichment_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Full results saved to: {output_file}")
    print("\n✨ Test complete!\n")


if __name__ == "__main__":
    main()

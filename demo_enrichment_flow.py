#!/usr/bin/env python3
"""
Lead Enrichment Demo

This script demonstrates the enrichment flow with or without running services.
If services are not running, it shows a mock example of what the enrichment would look like.
"""

import json
import sys
from typing import Dict, Any
import requests


def print_section(title: str, char: str = "="):
    """Print a formatted section header"""
    print(f"\n{char * 70}")
    print(f"{title}")
    print(f"{char * 70}\n")


def check_services() -> bool:
    """Check if backend services are running"""
    try:
        response = requests.get("http://localhost:8000/skip-tracing/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def demo_enrichment_flow(name: str, city: str, state: str, use_real_api: bool = False):
    """
    Demonstrate the complete enrichment flow
    
    Args:
        name: Full name (e.g., "John Smith")
        city: City name (e.g., "Denver")
        state: State code (e.g., "CO")
        use_real_api: Whether to use real API or show mock data
    """
    
    print_section("🚀 LEAD ENRICHMENT DEMONSTRATION", "=")
    
    # Step 1: Initial Lead Data
    print_section("📝 STEP 1: Initial Lead Data", "-")
    
    initial_lead = {
        "name": name,
        "city": city,
        "state": state
    }
    
    print("Starting with limited information:")
    print(f"  • Name:  {name}")
    print(f"  • City:  {city}")
    print(f"  • State: {state}")
    print(f"\n❌ Missing: phone, email, age, full address, etc.")
    
    # Step 2: Search by Name + Location
    print_section("🔍 STEP 2: Search by Name + Location", "-")
    
    if use_real_api:
        print(f"Making API call to skip tracing service...")
        print(f"POST /skip-tracing/search/by-name-address")
        print(f"  name: {name}")
        print(f"  citystatezip: {city}, {state}")
        
        try:
            response = requests.post(
                "http://localhost:8000/skip-tracing/search/by-name-address",
                params={"name": name, "citystatezip": f"{city}, {state}"},
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                people = data.get("data", {}).get("PeopleDetails", [])
                print(f"\n✅ Found {len(people)} potential match(es)")
                
                enriched_data = None
                if people:
                    enriched_data = people[0]
            else:
                print("\n❌ Search failed")
                enriched_data = None
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            use_real_api = False  # Fall back to mock
            enriched_data = None
    
    if not use_real_api:
        print("💡 MOCK MODE - Showing example enrichment results")
        print(f"\nSimulating: POST /skip-tracing/search/by-name-address")
        print(f"  name: {name}")
        print(f"  citystatezip: {city}, {state}")
        print(f"\nThis would search:")
        print(f"  ✓ FastPeopleSearch.com (free)")
        print(f"  ✓ TruePeopleSearch.com (free, fallback)")
        
        # Mock enriched data
        enriched_data = {
            "Person ID": "peo_3035551234",
            "Telephone": "(303) 555-1234",
            "Age": 45,
            "city": city,
            "address_region": state,
            "postal_code": "80201"
        }
    
    # Step 3: Display Enriched Basic Info
    print_section("📊 STEP 3: Initial Enrichment Results", "-")
    
    if enriched_data:
        print("✅ Basic enrichment successful!")
        print(f"\nNew information discovered:")
        print(f"  • Person ID: {enriched_data.get('Person ID')}")
        print(f"  • Phone:     {enriched_data.get('Telephone')}")
        print(f"  • Age:       {enriched_data.get('Age')}")
        print(f"  • ZIP Code:  {enriched_data.get('postal_code')}")
    else:
        print("❌ No matches found")
        return
    
    # Step 4: Get Detailed Information
    print_section("📋 STEP 4: Fetch Detailed Information", "-")
    
    person_id = enriched_data.get("Person ID")
    
    if use_real_api:
        print(f"Making API call for detailed info...")
        print(f"GET /skip-tracing/details/{person_id}")
        
        try:
            response = requests.get(
                f"http://localhost:8000/skip-tracing/details/{person_id}",
                timeout=90
            )
            response.raise_for_status()
            details = response.json()
            
            if details.get("success"):
                detailed_data = details.get("data", {})
            else:
                print("\n❌ Details fetch failed")
                detailed_data = None
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            use_real_api = False
            detailed_data = None
    
    if not use_real_api:
        print("💡 MOCK MODE - Showing example detailed results")
        print(f"\nSimulating: GET /skip-tracing/details/{person_id}")
        print(f"\nThis would fetch comprehensive information:")
        
        # Mock detailed data
        detailed_data = {
            "All Phone Details": [
                {
                    "phone_number": "(303) 555-1234",
                    "phone_type": "Wireless",
                    "last_reported": None
                },
                {
                    "phone_number": "(720) 555-5678",
                    "phone_type": "Landline",
                    "last_reported": None
                }
            ],
            "Email Addresses": [
                f"{name.lower().replace(' ', '.')}@example.com",
                f"{name.split()[0].lower()}@company.com"
            ],
            "Current Address Details List": [
                {
                    "full_address": f"123 Main St, {city}, {state} 80201",
                    "city": city,
                    "address_region": state,
                    "postal_code": "80201"
                }
            ],
            "Person Details": [
                {
                    "Name": name,
                    "Age": 45,
                    "Telephone": "(303) 555-1234"
                }
            ]
        }
    
    # Step 5: Complete Enriched Profile
    print_section("✨ STEP 5: Complete Enriched Profile", "-")
    
    if detailed_data:
        phones = detailed_data.get("All Phone Details", [])
        emails = detailed_data.get("Email Addresses", [])
        addresses = detailed_data.get("Current Address Details List", [])
        
        print("✅ Complete enrichment successful!\n")
        
        print("📱 Phone Numbers:")
        for phone in phones:
            print(f"  • {phone.get('phone_number')} ({phone.get('phone_type')})")
        
        print(f"\n📧 Email Addresses:")
        for email in emails:
            print(f"  • {email}")
        
        print(f"\n🏠 Address:")
        if addresses:
            addr = addresses[0]
            print(f"  • {addr.get('full_address', 'N/A')}")
        
        print(f"\n👤 Personal Info:")
        print(f"  • Name:  {name}")
        print(f"  • Age:   {enriched_data.get('Age')}")
        print(f"  • City:  {city}")
        print(f"  • State: {state}")
        print(f"  • ZIP:   {enriched_data.get('postal_code')}")
    
    # Final Summary
    print_section("📈 ENRICHMENT SUMMARY", "=")
    
    print("Before Enrichment:")
    print("  ✓ Name")
    print("  ✓ City")
    print("  ✓ State")
    print("  ✗ Phone")
    print("  ✗ Email")
    print("  ✗ Age")
    print("  ✗ Full Address")
    print("  ✗ ZIP Code")
    
    print("\nAfter Enrichment:")
    print("  ✓ Name")
    print("  ✓ City")
    print("  ✓ State")
    if detailed_data:
        print(f"  ✓ Phone ({len(phones)} numbers)")
        print(f"  ✓ Email ({len(emails)} addresses)")
        print(f"  ✓ Age")
        print(f"  ✓ Full Address")
        print(f"  ✓ ZIP Code")
    
    print_section("", "=")
    
    # Save results
    result = {
        "initial": initial_lead,
        "enriched": {
            "basic": enriched_data,
            "detailed": detailed_data
        },
        "mode": "real" if use_real_api else "mock"
    }
    
    output_file = "enrichment_demo_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


def main():
    """Main entry point"""
    
    print_section("🎯 SKIP TRACING LEAD ENRICHMENT DEMO", "=")
    
    # Check if services are running
    print("🔌 Checking if backend services are running...")
    services_running = check_services()
    
    if services_running:
        print("✅ Backend API is running - will use REAL API\n")
        use_real = True
    else:
        print("⚠️  Backend API is not running - will use MOCK MODE\n")
        print("To use real API, please start services:")
        print("  1. Start Docker: docker-compose up -d")
        print("  2. Start backend: ./start_backend.sh")
        print("  3. Start worker: ./start_worker.sh")
        print("\nSee START_SERVICES.md for detailed instructions.\n")
        use_real = False
    
    # Get lead data
    if len(sys.argv) >= 4:
        name = sys.argv[1]
        city = sys.argv[2]
        state = sys.argv[3]
    else:
        # Default test case
        name = "John Smith"
        city = "Denver"
        state = "CO"
        
        print("Using default test case:")
        print(f"  Name:  {name}")
        print(f"  City:  {city}")
        print(f"  State: {state}")
        print("\nTo use custom lead: python demo_enrichment_flow.py \"Name\" \"City\" \"ST\"")
    
    # Run demo
    try:
        demo_enrichment_flow(name, city, state, use_real)
        
        print("\n✨ Demo complete!")
        
        if not use_real:
            print("\n💡 This was a MOCK demonstration.")
            print("   Start the backend services to see real enrichment!")
            print("   See START_SERVICES.md for instructions.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

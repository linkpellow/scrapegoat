#!/usr/bin/env python3
"""
Minimal ScraperAPI Integration Test

Tests ScraperAPI integration with minimal API calls:
1. Check API key registration status
2. Make ONE enrichment request (will use ScraperAPI if ScrapingBee fails)
3. Verify usage tracking

Usage:
    python test_scraperapi_minimal.py [base_url]
    
Example:
    python test_scraperapi_minimal.py https://scrapegoat-production.up.railway.app
"""

import requests
import json
import sys
from typing import Dict, Any, Optional


class ScraperAPITester:
    """Minimal test for ScraperAPI integration"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 90
    
    def print_section(self, title: str, char: str = "="):
        """Print a formatted section header"""
        print(f"\n{char * 60}")
        print(f"{title}")
        print(f"{char * 60}")
    
    def test_health(self) -> bool:
        """Test if API is running"""
        self.print_section("1. Health Check", "-")
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is running")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return False
    
    def check_api_key_status(self) -> Dict[str, Any]:
        """Check ScraperAPI key registration and usage"""
        self.print_section("2. Check ScraperAPI Key Status", "-")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api-keys/usage",
                params={"provider": "scraperapi"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                keys = data.get("keys", [])
                summary = data.get("summary", {})
                
                print(f"📊 ScraperAPI Keys Found: {summary.get('total_keys', 0)}")
                print(f"✅ Active Keys: {summary.get('active_keys', 0)}")
                print(f"💰 Total Credits: {summary.get('total_credits', 0)}")
                print(f"📈 Used Credits: {summary.get('used_credits', 0)}")
                print(f"💵 Remaining Credits: {summary.get('remaining_credits', 0)}")
                
                if keys:
                    print(f"\n📋 Key Details:")
                    for key in keys:
                        print(f"  - Key ID: {key.get('id')}")
                        print(f"    Status: {'✅ Active' if key.get('is_active') else '❌ Inactive'}")
                        print(f"    Credits: {key.get('used_credits')}/{key.get('total_credits')} used")
                        print(f"    Remaining: {key.get('remaining_credits')}")
                
                return data
            else:
                print("❌ Failed to get API key status")
                return {}
                
        except Exception as e:
            print(f"❌ Error checking API key status: {e}")
            return {}
    
    def make_minimal_enrichment_request(self) -> Dict[str, Any]:
        """
        Make ONE minimal enrichment request.
        This will trigger ScraperAPI if ScrapingBee fails.
        """
        self.print_section("3. Make Minimal Enrichment Request", "-")
        
        # Use a simple, common name to minimize API calls
        test_name = "John Smith"
        test_location = "Denver, CO"
        
        print(f"🔍 Testing enrichment for: {test_name} in {test_location}")
        print(f"📡 This will use ScraperAPI if ScrapingBee is out of credits")
        print(f"⏱️  Making request (this may take 30-60 seconds)...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/skip-tracing/search/by-name-address",
                params={
                    "name": test_name,
                    "citystatezip": test_location
                },
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                people = data.get("data", {}).get("PeopleDetails", [])
                print(f"✅ Request successful!")
                print(f"📊 Found {len(people)} potential match(es)")
                
                if people:
                    first_match = people[0]
                    print(f"\n📋 Sample Result:")
                    print(f"  Name: {first_match.get('Name', 'N/A')}")
                    print(f"  Phone: {first_match.get('Telephone', 'N/A')}")
                    print(f"  Age: {first_match.get('Age', 'N/A')}")
                    print(f"  Location: {first_match.get('city', 'N/A')}, {first_match.get('address_region', 'N/A')}")
                
                return data
            else:
                print(f"❌ Enrichment request failed")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return {}
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out (this may indicate ScraperAPI is working but slow)")
            return {}
        except Exception as e:
            print(f"❌ Error making enrichment request: {e}")
            return {}
    
    def verify_usage_tracking(self) -> bool:
        """Verify that usage was tracked after the enrichment request"""
        self.print_section("4. Verify Usage Tracking", "-")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api-keys/usage",
                params={"provider": "scraperapi"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                summary = data.get("summary", {})
                used_before = getattr(self, '_used_before', 0)
                used_now = summary.get("used_credits", 0)
                
                print(f"📊 Usage Statistics:")
                print(f"   Used Credits: {used_now}")
                print(f"   Remaining Credits: {summary.get('remaining_credits', 0)}")
                
                if used_now > used_before:
                    print(f"✅ Usage tracking working! (Used {used_now - used_before} credit(s))")
                    return True
                else:
                    print(f"⚠️  Usage may not have been tracked (no change detected)")
                    print(f"   This could mean:")
                    print(f"   - Request used free methods (HTTP/Playwright)")
                    print(f"   - ScrapingBee succeeded (didn't need ScraperAPI)")
                    print(f"   - Request failed before reaching ScraperAPI")
                    return False
            else:
                print("❌ Failed to verify usage tracking")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying usage: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all minimal tests"""
        self.print_section("ScraperAPI Minimal Integration Test", "=")
        print(f"🌐 Testing: {self.base_url}")
        
        # Test 1: Health check
        if not self.test_health():
            print("\n❌ API is not running. Please start the server first.")
            return False
        
        # Test 2: Check API key status (before)
        status_before = self.check_api_key_status()
        if status_before:
            summary = status_before.get("summary", {})
            self._used_before = summary.get("used_credits", 0)
        
        # Test 3: Make minimal enrichment request
        enrichment_result = self.make_minimal_enrichment_request()
        
        # Test 4: Verify usage tracking
        usage_verified = self.verify_usage_tracking()
        
        # Final summary
        self.print_section("Test Summary", "=")
        
        if enrichment_result.get("success"):
            print("✅ Enrichment request completed")
        else:
            print("❌ Enrichment request failed")
        
        if usage_verified:
            print("✅ Usage tracking verified")
        else:
            print("⚠️  Usage tracking not verified (may have used free methods)")
        
        print(f"\n💡 Note: If ScrapingBee has credits, the request may use ScrapingBee")
        print(f"   instead of ScraperAPI. ScraperAPI is only used as a fallback.")
        
        return enrichment_result.get("success", False)


def main():
    """Main entry point"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = ScraperAPITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

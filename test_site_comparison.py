"""
Site Comparison Test for Skip Tracing

Tests multiple people search websites and ranks them based on:
- Success rate
- Data completeness
- Response time
- Data accuracy
"""

import requests
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics


BASE_URL = "http://localhost:8000"

# Test cases with known data for validation
TEST_CASES = [
    {
        "name": "Link Pellow",
        "city": "Dowagiac",
        "state": "MI",
        "expected_phone": "269-462-1403",  # For validation
        "expected_age_range": (25, 35)
    },
    # Add more test cases as needed
]


class SiteTestResults:
    """Track results for a single site"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.successes = 0
        self.failures = 0
        self.response_times = []
        self.completeness_scores = []
        self.accuracy_scores = []
        self.errors = []
        
    def add_success(self, response_time: float, completeness: float, accuracy: float):
        self.successes += 1
        self.response_times.append(response_time)
        self.completeness_scores.append(completeness)
        self.accuracy_scores.append(accuracy)
    
    def add_failure(self, error: str):
        self.failures += 1
        self.errors.append(error)
    
    def get_summary(self) -> Dict[str, Any]:
        total = self.successes + self.failures
        return {
            "site": self.site_name,
            "success_rate": self.successes / total if total > 0 else 0,
            "total_tests": total,
            "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
            "avg_completeness": statistics.mean(self.completeness_scores) if self.completeness_scores else 0,
            "avg_accuracy": statistics.mean(self.accuracy_scores) if self.accuracy_scores else 0,
            "errors": self.errors
        }
    
    def get_overall_score(self) -> float:
        """Calculate weighted overall score (0-100)"""
        summary = self.get_summary()
        
        # Weights
        WEIGHT_SUCCESS = 0.35      # Success rate is most important
        WEIGHT_COMPLETENESS = 0.30 # Data completeness
        WEIGHT_ACCURACY = 0.25     # Data accuracy
        WEIGHT_SPEED = 0.10        # Response time (normalized to 0-1)
        
        success_score = summary["success_rate"] * 100
        completeness_score = summary["avg_completeness"] * 100
        accuracy_score = summary["avg_accuracy"] * 100
        
        # Normalize speed (faster is better, cap at 30 seconds)
        avg_time = summary["avg_response_time"]
        speed_score = max(0, 100 - (avg_time / 30 * 100)) if avg_time > 0 else 0
        
        overall = (
            success_score * WEIGHT_SUCCESS +
            completeness_score * WEIGHT_COMPLETENESS +
            accuracy_score * WEIGHT_ACCURACY +
            speed_score * WEIGHT_SPEED
        )
        
        return overall


def calculate_completeness(person_data: Dict[str, Any]) -> float:
    """Calculate data completeness score (0-1)"""
    # Key fields we want populated
    fields = {
        "Person ID": 1.0,
        "Telephone": 2.0,      # More important
        "Age": 1.5,            # Important
        "city": 1.0,
        "address_region": 1.0,
        "postal_code": 1.0
    }
    
    total_weight = sum(fields.values())
    populated_weight = 0
    
    for field, weight in fields.items():
        value = person_data.get(field)
        if value and str(value).strip():
            populated_weight += weight
    
    return populated_weight / total_weight


def calculate_accuracy(person_data: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Calculate accuracy score (0-1) by comparing to expected values"""
    checks = []
    
    # Check phone
    if expected.get("expected_phone"):
        phone = person_data.get("Telephone", "")
        expected_phone = expected["expected_phone"].replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
        actual_phone = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+1", "")
        checks.append(expected_phone in actual_phone or actual_phone in expected_phone)
    
    # Check age range
    if expected.get("expected_age_range"):
        age = person_data.get("Age")
        if age:
            min_age, max_age = expected["expected_age_range"]
            checks.append(min_age <= age <= max_age)
        else:
            checks.append(False)
    
    return sum(checks) / len(checks) if checks else 1.0


def test_site_endpoint(
    site_name: str,
    test_case: Dict[str, Any],
    timeout: int = 90
) -> tuple[bool, float, Optional[Dict[str, Any]], Optional[str]]:
    """
    Test a specific site with a test case.
    
    Returns: (success, response_time, data, error_message)
    """
    try:
        url = f"{BASE_URL}/skip-tracing/test/search-specific-site"
        params = {
            "site_name": site_name,
            "name": test_case["name"],
            "city": test_case.get("city"),
            "state": test_case.get("state")
        }
        
        start_time = time.time()
        response = requests.post(url, params=params, timeout=timeout)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("records_count", 0) > 0:
                return True, elapsed, data, None
            else:
                return False, elapsed, None, "No results found"
        else:
            return False, elapsed, None, f"HTTP {response.status_code}"
    
    except requests.Timeout:
        return False, timeout, None, "Timeout"
    except Exception as e:
        return False, 0, None, str(e)


def run_comparison_tests(sites: List[str], test_cases: List[Dict[str, Any]]) -> Dict[str, SiteTestResults]:
    """Run tests for all sites and return results"""
    results = {site: SiteTestResults(site) for site in sites}
    
    print("=" * 80)
    print("PEOPLE SEARCH SITE COMPARISON TEST")
    print("=" * 80)
    print(f"\nTesting {len(sites)} sites with {len(test_cases)} test cases...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}/{len(test_cases)}: {test_case['name']} ---")
        
        for site in sites:
            print(f"  Testing {site}...", end=" ", flush=True)
            
            success, elapsed, data, error = test_site_endpoint(site, test_case)
            
            if success and data:
                # Extract first person result
                records = data.get("records", [])
                if records:
                    person = records[0]
                    completeness = calculate_completeness(person)
                    accuracy = calculate_accuracy(person, test_case)
                    
                    results[site].add_success(elapsed, completeness, accuracy)
                    print(f"✅ {elapsed:.1f}s (complete: {completeness:.0%}, accurate: {accuracy:.0%})")
                else:
                    results[site].add_failure("No records in response")
                    print(f"❌ No records")
            else:
                results[site].add_failure(error or "Unknown error")
                print(f"❌ {error}")
    
    return results


def print_rankings(results: Dict[str, SiteTestResults]):
    """Print ranked results"""
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    # Calculate scores and rank
    ranked = []
    for site_name, site_results in results.items():
        summary = site_results.get_summary()
        score = site_results.get_overall_score()
        ranked.append((site_name, score, summary))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    
    # Print rankings
    print("\n🏆 RANKINGS:\n")
    for rank, (site_name, score, summary) in enumerate(ranked, 1):
        print(f"{rank}. {site_name.upper()} - Score: {score:.1f}/100")
        print(f"   Success Rate: {summary['success_rate']:.0%}")
        print(f"   Avg Completeness: {summary['avg_completeness']:.0%}")
        print(f"   Avg Accuracy: {summary['avg_accuracy']:.0%}")
        print(f"   Avg Response Time: {summary['avg_response_time']:.1f}s")
        if summary['errors']:
            print(f"   Errors: {', '.join(set(summary['errors']))}")
        print()
    
    # Recommendation
    print("=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    
    winner = ranked[0]
    print(f"\n✨ Best Overall: {winner[0].upper()} (Score: {winner[1]:.1f}/100)")
    
    # Suggest priority order
    if len(ranked) >= 3:
        priority = [r[0] for r in ranked[:3]]
        print(f"\n📋 Suggested Priority Order:")
        for i, site in enumerate(priority, 1):
            print(f"   {i}. {site}")
    
    # Save results to file
    results_file = f"site_comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "rankings": [{"rank": i, "site": s, "score": sc, "summary": sm} for i, (s, sc, sm) in enumerate(ranked, 1)]
        }, f, indent=2)
    print(f"\n💾 Detailed results saved to: {results_file}")


def main():
    """Main test runner"""
    
    # Sites to test
    sites_to_test = [
        "thatsthem",        # User's top choice
        "anywho",
        "searchpeoplefree",
        "zabasearch",
        "fastpeoplesearch",  # Include existing for comparison
        "truepeoplesearch"
    ]
    
    print("\n🔧 Prerequisites:")
    print("   1. Backend server running on http://localhost:8000")
    print("   2. Test endpoint added to skip_tracing.py")
    print("   3. Site configurations added to people_search_sites.py")
    print("\nPress Enter to continue or Ctrl+C to abort...")
    input()
    
    # Run tests
    results = run_comparison_tests(sites_to_test, TEST_CASES)
    
    # Print rankings
    print_rankings(results)


if __name__ == "__main__":
    main()

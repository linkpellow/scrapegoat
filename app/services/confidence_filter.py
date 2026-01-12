"""
Confidence-Based Result Filter

Prevents unnecessary HITL interventions by filtering low-confidence
or ambiguous results.

Key behaviors:
1. Multiple ambiguous matches → return "no_match" (not HITL)
2. Low confidence required fields → return "no_match" (not HITL)
3. Contradictory data signals → return "no_match" (not HITL)

This reduces human confirmation requests and keeps data clean.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.smartfields.types import FieldResult


class ConfidenceFilter:
    """Filters results based on confidence and ambiguity."""
    
    # Confidence thresholds
    MIN_CONFIDENCE_REQUIRED = 0.7  # For required fields
    MIN_CONFIDENCE_OPTIONAL = 0.5  # For optional fields
    
    @staticmethod
    def should_return_no_match(
        items: List[Dict[str, Any]],
        required_fields: List[str],
        search_context: Dict[str, str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if results should be filtered as "no match" instead
        of triggering HITL.
        
        Args:
            items: Extracted items
            required_fields: List of required field names
            search_context: Original search params (name, location, etc.)
        
        Returns:
            (should_filter, reason)
        
        Filters when:
        - Too many ambiguous matches (>10 with low confidence)
        - Required fields have low confidence
        - Contradictory data (age/DOB mismatch, etc.)
        - Poor match to search criteria
        """
        if not items:
            return (False, None)  # No items is different from "no match"
        
        # Check 1: Too many ambiguous matches
        if len(items) > 10:
            # Check if we can narrow down with confidence
            high_confidence_items = [
                item for item in items
                if ConfidenceFilter._item_confidence(item) > 0.8
            ]
            
            if len(high_confidence_items) == 0:
                return (True, "Too many ambiguous matches, no high-confidence results")
            elif len(high_confidence_items) > 5:
                return (True, f"Too many possible matches ({len(high_confidence_items)}) with similar confidence")
        
        # Check 2: Required fields low confidence
        for item in items:
            for field in required_fields:
                confidence = ConfidenceFilter._get_field_confidence(item, field)
                
                if confidence is not None and confidence < ConfidenceFilter.MIN_CONFIDENCE_REQUIRED:
                    return (True, f"Required field '{field}' has low confidence ({confidence:.2f})")
        
        # Check 3: Contradictory data
        for item in items:
            has_contradiction = ConfidenceFilter._has_contradictions(item)
            if has_contradiction:
                return (True, "Contradictory data detected (age/DOB mismatch or location conflict)")
        
        # Check 4: Poor match to search criteria
        if search_context:
            for item in items:
                match_score = ConfidenceFilter._match_score(item, search_context)
                if match_score < 0.5:
                    return (True, f"Poor match to search criteria (score: {match_score:.2f})")
        
        return (False, None)
    
    @staticmethod
    def _item_confidence(item: Dict[str, Any]) -> float:
        """
        Calculate overall confidence for an item.
        
        Uses SmartFields metadata if available.
        """
        smartfields = item.get("_smartfields", {})
        
        if not smartfields:
            return 0.8  # Default if no metadata
        
        confidences = []
        for field_name, field_result in smartfields.items():
            if isinstance(field_result, dict) and "confidence" in field_result:
                confidences.append(field_result["confidence"])
        
        if not confidences:
            return 0.8
        
        # Return average confidence
        return sum(confidences) / len(confidences)
    
    @staticmethod
    def _get_field_confidence(item: Dict[str, Any], field_name: str) -> Optional[float]:
        """Get confidence score for a specific field."""
        smartfields = item.get("_smartfields", {})
        field_result = smartfields.get(field_name)
        
        if isinstance(field_result, dict):
            return field_result.get("confidence")
        
        return None
    
    @staticmethod
    def _has_contradictions(item: Dict[str, Any]) -> bool:
        """
        Detect contradictory data within an item.
        
        Examples:
        - Age doesn't match DOB
        - City doesn't match state
        - Phone area code doesn't match location
        """
        # Age vs DOB check
        age = item.get("age") or item.get("Age")
        dob = item.get("date_of_birth") or item.get("DOB")
        
        if age and dob:
            from datetime import datetime
            try:
                if isinstance(dob, str):
                    dob_parsed = datetime.fromisoformat(dob.replace("Z", "+00:00"))
                    calculated_age = (datetime.utcnow() - dob_parsed).days // 365
                    
                    # Allow ±2 years tolerance
                    if abs(calculated_age - int(age)) > 2:
                        return True
            except:
                pass
        
        # City vs State check (would need geocoding data)
        # For now, skip
        
        # Phone area code vs location (would need area code database)
        # For now, skip
        
        return False
    
    @staticmethod
    def _match_score(item: Dict[str, Any], search_context: Dict[str, str]) -> float:
        """
        Calculate how well item matches search criteria.
        
        Args:
            item: Extracted item
            search_context: Search params like {"name": "John Smith", "city": "Denver"}
        
        Returns:
            Score 0.0-1.0
        """
        score = 0.0
        checks = 0
        
        # Name match
        if "name" in search_context:
            item_name = item.get("name") or item.get("Name") or ""
            search_name = search_context["name"].lower()
            
            if search_name in item_name.lower():
                score += 1.0
            elif any(part in item_name.lower() for part in search_name.split()):
                score += 0.5
            
            checks += 1
        
        # Location match (city)
        if "city" in search_context:
            item_city = item.get("city") or item.get("City") or ""
            search_city = search_context["city"].lower()
            
            if search_city in item_city.lower():
                score += 1.0
            
            checks += 1
        
        # Location match (state)
        if "state" in search_context:
            item_state = item.get("address_region") or item.get("State") or ""
            search_state = search_context["state"].upper()
            
            if search_state in item_state.upper():
                score += 1.0
            
            checks += 1
        
        # Age match (if provided)
        if "age" in search_context:
            item_age = item.get("age") or item.get("Age")
            search_age = int(search_context["age"])
            
            if item_age:
                # Allow ±5 years tolerance
                if abs(int(item_age) - search_age) <= 5:
                    score += 1.0
                elif abs(int(item_age) - search_age) <= 10:
                    score += 0.5
            
            checks += 1
        
        if checks == 0:
            return 0.8  # No criteria to check
        
        return score / checks
    
    @staticmethod
    def filter_ambiguous_results(
        items: List[Dict[str, Any]],
        search_context: Dict[str, str],
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Filter and rank results by confidence and match score.
        
        Returns top N results that meet confidence thresholds.
        """
        scored_items = []
        
        for item in items:
            confidence = ConfidenceFilter._item_confidence(item)
            match_score = ConfidenceFilter._match_score(item, search_context)
            
            # Combined score (weighted)
            combined_score = (confidence * 0.4) + (match_score * 0.6)
            
            scored_items.append({
                "item": item,
                "confidence": confidence,
                "match_score": match_score,
                "combined_score": combined_score
            })
        
        # Sort by combined score
        scored_items.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Filter to top N with minimum confidence
        filtered = [
            x["item"] for x in scored_items
            if x["combined_score"] >= 0.6
        ][:max_results]
        
        return filtered

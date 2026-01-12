"""
Multi-Source Consensus Extraction

Extracts data from multiple evidence channels:
1. HTML CSS selectors (primary)
2. JSON-LD structured data
3. OpenGraph/Twitter meta tags
4. Embedded script data (Next.js __NEXT_DATA__, Apollo, etc.)
5. Response headers (when relevant)

Then applies consensus: accept value if 2-of-3 sources agree.

This dramatically improves SmartFields confidence without ML.
"""

from typing import Dict, Any, List, Optional
import json
import re
from bs4 import BeautifulSoup


class MultiSourceExtractor:
    """
    Extract data from multiple sources and apply consensus logic.
    
    Confidence amplification: if 2+ sources agree → confidence += 0.2
    """
    
    @staticmethod
    def extract_all_sources(
        html: str,
        field_name: str,
        field_type: str,
        primary_value: Any
    ) -> Dict[str, Any]:
        """
        Extract field from all available sources.
        
        Returns:
            {
                "primary": value,
                "json_ld": value | None,
                "meta_tags": value | None,
                "script_data": value | None,
                "consensus_value": value,
                "confidence_boost": float,
                "sources_agreeing": int
            }
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract from each source
        json_ld_value = MultiSourceExtractor._extract_from_json_ld(soup, field_name, field_type)
        meta_value = MultiSourceExtractor._extract_from_meta_tags(soup, field_name, field_type)
        script_value = MultiSourceExtractor._extract_from_script_data(soup, field_name, field_type)
        
        # Collect non-null values
        sources = {
            "primary": primary_value,
            "json_ld": json_ld_value,
            "meta_tags": meta_value,
            "script_data": script_value
        }
        
        # Remove None values
        valid_sources = {k: v for k, v in sources.items() if v is not None}
        
        # Apply consensus
        consensus_value, confidence_boost, sources_agreeing = MultiSourceExtractor._apply_consensus(valid_sources)
        
        return {
            "primary": primary_value,
            "json_ld": json_ld_value,
            "meta_tags": meta_value,
            "script_data": script_value,
            "consensus_value": consensus_value,
            "confidence_boost": confidence_boost,
            "sources_agreeing": sources_agreeing
        }
    
    @staticmethod
    def _extract_from_json_ld(soup: BeautifulSoup, field_name: str, field_type: str) -> Optional[Any]:
        """Extract from JSON-LD structured data"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Common JSON-LD mappings
                if field_name == "title" or field_type == "text":
                    return data.get("name") or data.get("headline")
                
                elif field_name == "description":
                    return data.get("description")
                
                elif field_name == "price" or field_type == "money":
                    offers = data.get("offers", {})
                    if isinstance(offers, dict):
                        return offers.get("price")
                
                elif field_name == "image" or field_type == "image_url":
                    return data.get("image")
                
                elif field_name == "url" or field_type == "url":
                    return data.get("url")
                
                elif field_name == "date" or field_type == "date":
                    return data.get("datePublished") or data.get("dateModified")
                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    @staticmethod
    def _extract_from_meta_tags(soup: BeautifulSoup, field_name: str, field_type: str) -> Optional[Any]:
        """Extract from OpenGraph/Twitter/standard meta tags"""
        # OpenGraph
        og_property = None
        if field_name == "title":
            og_property = "og:title"
        elif field_name == "description":
            og_property = "og:description"
        elif field_name == "image":
            og_property = "og:image"
        elif field_name == "url":
            og_property = "og:url"
        
        if og_property:
            meta = soup.find('meta', property=og_property)
            if meta and meta.get('content'):
                return meta['content']
        
        # Twitter Cards
        twitter_name = None
        if field_name == "title":
            twitter_name = "twitter:title"
        elif field_name == "description":
            twitter_name = "twitter:description"
        elif field_name == "image":
            twitter_name = "twitter:image"
        
        if twitter_name:
            meta = soup.find('meta', attrs={'name': twitter_name})
            if meta and meta.get('content'):
                return meta['content']
        
        # Standard meta tags
        if field_name == "description":
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta and meta.get('content'):
                return meta['content']
        
        return None
    
    @staticmethod
    def _extract_from_script_data(soup: BeautifulSoup, field_name: str, field_type: str) -> Optional[Any]:
        """Extract from embedded JavaScript data (Next.js, Apollo, etc.)"""
        scripts = soup.find_all('script', id=re.compile(r'(__NEXT_DATA__|__APOLLO_STATE__)'))
        
        for script in scripts:
            try:
                if script.get('id') == '__NEXT_DATA__':
                    data = json.loads(script.string)
                    props = data.get('props', {}).get('pageProps', {})
                    
                    # Attempt to extract field
                    if field_name in props:
                        return props[field_name]
                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    @staticmethod
    def _apply_consensus(sources: Dict[str, Any]) -> tuple[Any, float, int]:
        """
        Apply consensus logic: accept value if 2+ sources agree.
        
        Returns:
            (consensus_value, confidence_boost, sources_agreeing)
        """
        if len(sources) < 2:
            # Only one source, return it
            return list(sources.values())[0], 0.0, 1
        
        # Group values by equality (normalize for comparison)
        value_groups = {}
        for source_name, value in sources.items():
            # Normalize value for comparison
            normalized = MultiSourceExtractor._normalize_for_comparison(value)
            if normalized not in value_groups:
                value_groups[normalized] = []
            value_groups[normalized].append((source_name, value))
        
        # Find most common value
        max_agreement = max(len(group) for group in value_groups.values())
        
        if max_agreement >= 2:
            # Consensus reached
            for normalized, group in value_groups.items():
                if len(group) == max_agreement:
                    # Return original value (not normalized)
                    consensus_value = group[0][1]
                    confidence_boost = 0.2 if max_agreement == 2 else 0.3
                    return consensus_value, confidence_boost, max_agreement
        
        # No consensus, return primary
        return sources.get("primary"), 0.0, 1
    
    @staticmethod
    def _normalize_for_comparison(value: Any) -> str:
        """Normalize value for consensus comparison"""
        if value is None:
            return "NULL"
        
        # Convert to string and normalize whitespace/case
        str_value = str(value).strip().lower()
        
        # Remove common noise
        str_value = re.sub(r'\s+', ' ', str_value)
        
        return str_value

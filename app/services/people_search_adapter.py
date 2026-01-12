"""
People Search Adapter

Creates scraper jobs from people search site configurations.
Handles job creation, field mapping, and execution.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.field_map import FieldMap
from app.people_search_sites import get_site_config
import uuid
import re


class PeopleSearchAdapter:
    """Adapter for creating scraper jobs from people search site configs"""
    
    @staticmethod
    def create_search_job(
        db: Session,
        site_name: str,
        search_type: str,
        search_params: Dict[str, str]
    ) -> str:
        """
        Create a scraper job for a people search.
        
        Args:
            db: Database session
            site_name: "fastpeoplesearch" or "truepeoplesearch"
            search_type: "search_by_name" | "search_by_phone" | "person_details"
            search_params: Search parameters (name, phone, person_url, etc.)
        
        Returns:
            job_id (str)
        """
        site_config = get_site_config(site_name)
        search_config = site_config.get(search_type)
        
        if not search_config:
            raise ValueError(f"Search type '{search_type}' not supported by {site_name}")
        
        # Build target URL
        url_template = search_config["url_template"]
        target_url = PeopleSearchAdapter._build_url(url_template, search_params)
        
        # Extract field names
        fields = list(search_config["fields"].keys())
        
        # Create job
        job = Job(
            id=uuid.uuid4(),
            target_url=target_url,
            fields=fields,
            requires_auth=site_config.get("requires_auth", False),
            frequency="on_demand",  # People search jobs are one-time
            strategy="auto",
            crawl_mode=search_config.get("crawl_mode", "single"),
            list_config=search_config.get("list_config", {}),
            engine_mode=search_config.get("engine_mode", "auto"),
            status="validated"
        )
        
        db.add(job)
        db.flush()  # Get job.id
        
        # Create field mappings
        for field_name, field_config in search_config["fields"].items():
            selector_spec = {
                "css": field_config.get("css", ""),
                "attr": field_config.get("attr"),
                "all": field_config.get("all", False)
            }
            
            # Add regex if present
            if field_config.get("regex"):
                selector_spec["regex"] = field_config.get("regex")
            
            field_map = FieldMap(
                id=uuid.uuid4(),
                job_id=job.id,
                field_name=field_name,
                selector_spec=selector_spec,
                field_type=field_config.get("field_type", "string"),
                smart_config=field_config.get("smart_config", {}),
                validation_rules=field_config.get("validation_rules", {})
            )
            db.add(field_map)
        
        db.commit()
        
        return str(job.id)
    
    @staticmethod
    def _build_url(template: str, params: Dict[str, str]) -> str:
        """Build URL from template and parameters"""
        url = template
        
        # Helper to convert state code to full name
        state_names = {
            "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
            "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
            "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
            "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
            "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
            "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
            "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
            "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico", "NY": "new-york",
            "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma",
            "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island", "SC": "south-carolina",
            "SD": "south-dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
            "VT": "vermont", "VA": "virginia", "WA": "washington", "WV": "west-virginia",
            "WI": "wisconsin", "WY": "wyoming", "DC": "district-of-columbia"
        }
        
        # Process all variants of each parameter
        for key, value in params.items():
            # Standard lowercase with dashes
            placeholder = "{" + key + "}"
            if placeholder in url:
                if key == "name":
                    # "John Smith" -> "john-smith"
                    formatted = value.lower().replace(" ", "-")
                    formatted = re.sub(r'[^a-z0-9-]', '', formatted)
                elif key == "phone":
                    # "+1-303-555-0100" -> "13035550100"
                    formatted = re.sub(r'[^0-9]', '', value)
                elif key in ("city", "state"):
                    # "Dowagiac" -> "dowagiac", "MI" -> "mi"
                    formatted = value.lower().replace(" ", "-")
                    formatted = re.sub(r'[^a-z0-9-]', '', formatted)
                elif key == "location":
                    # "Denver, CO 80201" -> leave as-is
                    formatted = value
                else:
                    formatted = value
                
                url = url.replace(placeholder, formatted)
            
            # State uppercase variant (for ThatsThem)
            placeholder_upper = "{" + key + "_upper}"
            if placeholder_upper in url and key == "state":
                formatted = value.upper()
                url = url.replace(placeholder_upper, formatted)
            
            # State full name variant (for ZabaSearch)
            placeholder_full = "{" + key + "_full}"
            if placeholder_full in url and key == "state":
                formatted = state_names.get(value.upper(), value.lower())
                url = url.replace(placeholder_full, formatted)
        
        return url
    
    @staticmethod
    def parse_search_results(
        records: List[Dict[str, Any]],
        site_name: str
    ) -> List[Dict[str, Any]]:
        """
        Parse raw scraper results into standardized format.
        
        Handles:
        - Field name normalization
        - Person ID generation
        - Phone number extraction
        """
        parsed = []
        
        for record in records:
            # Extract phone
            telephone = (
                record.get("phone") or
                record.get("phone_number") or
                record.get("telephone") or
                ""
            )
            
            # Extract age
            age = record.get("age")
            if age and isinstance(age, str):
                # Extract first number from string
                match = re.search(r'\d+', age)
                age = int(match.group()) if match else None
            
            # Generate or extract Person ID
            person_id = record.get("person_id")
            if not person_id:
                # Generate from phone or name
                if telephone:
                    clean_phone = re.sub(r'[^0-9]', '', telephone)
                    person_id = f"peo_{clean_phone}"
                else:
                    person_id = f"peo_{uuid.uuid4().hex[:12]}"
            
            # Build standardized record
            parsed_record = {
                "person_id": person_id,
                "name": record.get("name"),
                "telephone": telephone,
                "age": age,
                "city": record.get("city"),
                "state": record.get("state") or record.get("address_region"),
                "zip_code": record.get("zip_code") or record.get("postal_code"),
                "address": record.get("address"),
                
                # Include SmartFields metadata if present
                "_smartfields": record.get("_smartfields", {}),
                
                # Source tracking
                "_source": site_name,
                "_url": record.get("_url")
            }
            
            parsed.append(parsed_record)
        
        return parsed
    
    @staticmethod
    def parse_person_details(
        record: Dict[str, Any],
        site_name: str
    ) -> Dict[str, Any]:
        """
        Parse detailed person record.
        
        Extracts:
        - All phone numbers + types
        - All email addresses
        - Address details
        """
        # Extract all phones
        all_phones = record.get("all_phones", [])
        if not all_phones and record.get("phone"):
            all_phones = [record.get("phone")]
        
        phone_types = record.get("phone_types", [])
        
        # Build phone details
        phone_details = []
        for i, phone in enumerate(all_phones):
            phone_type = phone_types[i] if i < len(phone_types) else "Unknown"
            
            # Normalize phone type
            phone_type_normalized = PeopleSearchAdapter._normalize_phone_type(phone_type)
            
            phone_details.append({
                "phone_number": phone,
                "phone_type": phone_type_normalized,
                "last_reported": None  # Not typically available
            })
        
        # Extract emails
        emails = record.get("all_emails", [])
        if not emails and record.get("email"):
            emails = [record.get("email")]
        
        # Extract address
        address_details = {
            "address_region": record.get("state") or record.get("address_region"),
            "postal_code": record.get("zip_code") or record.get("postal_code"),
            "city": record.get("city"),
            "full_address": record.get("address")
        }
        
        # Extract age
        age = record.get("age")
        if age and isinstance(age, str):
            match = re.search(r'\d+', age)
            age = int(match.group()) if match else None
        
        return {
            "all_phone_details": phone_details,
            "person_details": {
                "Age": age,
                "Telephone": all_phones[0] if all_phones else None,
                "Name": record.get("name")
            },
            "address_details": [address_details] if address_details.get("city") else [],
            "emails": emails,
            "_smartfields": record.get("_smartfields", {}),
            "_source": site_name
        }
    
    @staticmethod
    def _normalize_phone_type(phone_type: str) -> str:
        """Normalize phone type to standard values"""
        phone_type_lower = phone_type.lower()
        
        if "mobile" in phone_type_lower or "cell" in phone_type_lower or "wireless" in phone_type_lower:
            return "Wireless"
        elif "landline" in phone_type_lower or "home" in phone_type_lower:
            return "Landline"
        elif "voip" in phone_type_lower or "internet" in phone_type_lower:
            return "VoIP"
        else:
            return "Unknown"

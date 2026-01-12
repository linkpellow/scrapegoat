"""
People Search Site Configurations

Real selectors for FastPeopleSearch and TruePeopleSearch.
These are free sites with no authentication required.
"""

from typing import Dict, Any


# FastPeopleSearch Configuration
FAST_PEOPLE_SEARCH = {
    "name": "FastPeopleSearch",
    "base_url": "https://www.fastpeoplesearch.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://www.fastpeoplesearch.com/name/{name}",
        "crawl_mode": "list",
        "engine_mode": "playwright",  # Needs JS for full results
        
        "list_config": {
            "item_links": {
                "css": "div.card-body a.link-to-details",
                "attr": "href",
                "all": True
            },
            "pagination": {
                "css": "a.page-link[rel='next']",
                "attr": "href"
            }
        },
        
        "fields": {
            "person_id": {
                "css": "div.card-body a.link-to-details",
                "attr": "data-detail-link",
                "field_type": "string"
            },
            "name": {
                "css": "div.card-body .card-title",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.card-body .detail-box-age span",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.card-body .phones a",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "city": {
                "css": "div.card-body .detail-box-address .city",
                "field_type": "city"
            },
            "state": {
                "css": "div.card-body .detail-box-address .state",
                "field_type": "state"
            },
            "zip_code": {
                "css": "div.card-body .detail-box-address .zip",
                "field_type": "zip_code"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://www.fastpeoplesearch.com/phone/{phone}",
        "crawl_mode": "single",
        "engine_mode": "playwright",
        
        "fields": {
            "name": {
                "css": "div.detail-box h2.card-title",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.age-info span",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.phones a",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div.current-address",
                "field_type": "address"
            }
        }
    },
    
    "person_details": {
        "url_template": "https://www.fastpeoplesearch.com{person_url}",
        "crawl_mode": "single",
        "engine_mode": "playwright",
        
        "fields": {
            "name": {
                "css": "div.detail-box h2.card-title",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.age-info span",
                "field_type": "integer"
            },
            "all_phones": {
                "css": "div.phones-table tbody tr td:first-child",
                "field_type": "phone",
                "all": True,
                "smart_config": {"country": "US", "format": "E164"}
            },
            "phone_types": {
                "css": "div.phones-table tbody tr td:nth-child(2)",
                "all": True,
                "field_type": "string"
            },
            "all_emails": {
                "css": "div.emails-table tbody tr td:first-child",
                "field_type": "email",
                "all": True
            },
            "address": {
                "css": "div.current-address .address-full",
                "field_type": "address"
            },
            "city": {
                "css": "div.current-address .city",
                "field_type": "city"
            },
            "state": {
                "css": "div.current-address .state",
                "field_type": "state"
            },
            "zip_code": {
                "css": "div.current-address .zip",
                "field_type": "zip_code"
            }
        }
    }
}


# TruePeopleSearch Configuration
TRUE_PEOPLE_SEARCH = {
    "name": "TruePeopleSearch",
    "base_url": "https://www.truepeoplesearch.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://www.truepeoplesearch.com/results?name={name}&citystatezip={location}",
        "crawl_mode": "list",
        "engine_mode": "playwright",
        
        "list_config": {
            "item_links": {
                "css": "div.card a.btn-detail",
                "attr": "href",
                "all": True
            },
            "pagination": {
                "css": "ul.pagination li.page-item:not(.disabled) a.page-link:contains('Next')",
                "attr": "href"
            }
        },
        
        "fields": {
            "person_id": {
                "css": "div.card a.btn-detail",
                "attr": "data-person-id",
                "field_type": "string"
            },
            "name": {
                "css": "div.card .h4.card-title",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.card .content-label:contains('Age') + .content-value",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.card .content-label:contains('Phone') + .content-value a",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div.card .content-label:contains('Address') + .content-value",
                "field_type": "address"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://www.truepeoplesearch.com/results?phoneno={phone}",
        "crawl_mode": "single",
        "engine_mode": "playwright",
        
        "fields": {
            "name": {
                "css": "div.detail-box h1",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.content-label:contains('Age') + .content-value",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.content-label:contains('Phone') + .content-value",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div.content-label:contains('Current Address') + .content-value",
                "field_type": "address"
            }
        }
    },
    
    "person_details": {
        "url_template": "https://www.truepeoplesearch.com/details{person_url}",
        "crawl_mode": "single",
        "engine_mode": "playwright",
        
        "fields": {
            "name": {
                "css": "div.detail-box h1",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.content-label:contains('Age') + .content-value",
                "field_type": "integer"
            },
            "all_phones": {
                "css": "div.content-label:contains('Phone Numbers') + .content-value div.row div",
                "field_type": "phone",
                "all": True,
                "smart_config": {"country": "US", "format": "E164"}
            },
            "phone_types": {
                "css": "div.content-label:contains('Phone Numbers') + .content-value div.row small",
                "all": True,
                "field_type": "string"
            },
            "all_emails": {
                "css": "div.content-label:contains('Email Addresses') + .content-value a",
                "field_type": "email",
                "all": True
            },
            "address": {
                "css": "div.content-label:contains('Current Address') + .content-value",
                "field_type": "address"
            },
            "city": {
                "css": "div.content-label:contains('Current Address') + .content-value .city",
                "field_type": "city"
            },
            "state": {
                "css": "div.content-label:contains('Current Address') + .content-value .state",
                "field_type": "state"
            },
            "zip_code": {
                "css": "div.content-label:contains('Current Address') + .content-value .zip",
                "field_type": "zip_code"
            }
        }
    }
}


# Site Registry
PEOPLE_SEARCH_SITES = {
    "fastpeoplesearch": FAST_PEOPLE_SEARCH,
    "truepeoplesearch": TRUE_PEOPLE_SEARCH
}


def get_site_config(site_name: str) -> Dict[str, Any]:
    """Get configuration for a people search site"""
    site = PEOPLE_SEARCH_SITES.get(site_name.lower())
    if not site:
        raise ValueError(f"Unknown people search site: {site_name}")
    return site


def get_available_sites() -> list:
    """Get list of available people search sites"""
    return list(PEOPLE_SEARCH_SITES.keys())

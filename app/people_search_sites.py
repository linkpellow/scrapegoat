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
        "url_template": "https://www.fastpeoplesearch.com/name/{name}_{city}-{state}",
        "crawl_mode": "single",
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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
        "url_template": "https://www.fastpeoplesearch.com/{phone}",
        "crawl_mode": "single",
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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
        "url_template": "https://www.truepeoplesearch.com/results?name={name}&citystatezip={city}, {state}",
        "crawl_mode": "single",
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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
        "engine_mode": "auto",  # Use auto-escalation (HTTP → Playwright if blocked)
        
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


# ThatsThem Configuration
# Based on real HTML structure from thatsthem.com/name/Link-Pellow/Dowagiac-MI
THATS_THEM = {
    "name": "ThatsThem",
    "base_url": "https://thatsthem.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://thatsthem.com/name/{name}/{city}-{state_upper}",
        "crawl_mode": "single",
        "engine_mode": "auto",  # Start with HTTP, escalate to Playwright if needed, ScrapingBee/ScraperAPI as last resort
        
        "fields": {
            "name": {
                "css": "div.card div.name a.web",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.card div.age",
                "regex": r"\((\d+)\s+years? old\)",  # Extract from "Born January 1997 (29 years old)"
                "field_type": "integer"
            },
            "phone": {
                "css": "div.phone span.number a.web",
                "all": True,
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "city": {
                "css": "span.address span.city",
                "field_type": "city"
            },
            "state": {
                "css": "span.address span.state",
                "field_type": "state"
            },
            "zip_code": {
                "css": "span.address span.zip",
                "field_type": "zip_code"
            },
            "address": {
                "css": "div.subtitle:contains('Current Address:') ~ div.location span.address a.web",
                "field_type": "address"
            },
            "email": {
                "css": "div.email span.inbox a.web",
                "all": True,
                "field_type": "email"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://thatsthem.com/phone/{phone}",
        "crawl_mode": "single",
        "engine_mode": "auto",  # Start with HTTP, escalate to Playwright if needed
        
        "fields": {
            "name": {
                "css": "div.card div.name a.web",
                "field_type": "person_name"
            },
            "age": {
                "css": "div.card div.age",
                "regex": r"\((\d+)\s+years? old\)",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.phone span.number a.web",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div.subtitle:contains('Current Address:') ~ div.location span.address a.web",
                "field_type": "address"
            }
        }
    }
}


# AnyWho Configuration  
# Based on web search results from anywho.com
ANY_WHO = {
    "name": "AnyWho",
    "base_url": "https://www.anywho.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://www.anywho.com/people/{name}/{state}/{city}",
        "crawl_mode": "single",
        "engine_mode": "auto",
        
        "fields": {
            "name": {
                "css": "h2, div[class*='name'], span[class*='name']",
                "field_type": "person_name"
            },
            "age": {
                "css": "div:contains('Age'), span:contains('Age')",
                "regex": r"Age\s*(\d+)",
                "field_type": "integer"
            },
            "phone": {
                "css": "a[href*='phone'], div[class*='phone'], span[class*='phone']",
                "all": True,
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div[class*='address'], p[class*='address'], span[class*='address']",
                "field_type": "address"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://www.anywho.com/phone/{phone}",
        "crawl_mode": "single",
        "engine_mode": "auto",
        
        "fields": {
            "name": {
                "css": "h2, div[class*='name']",
                "field_type": "person_name"
            },
            "age": {
                "css": "div:contains('Age'), span:contains('Age')",
                "regex": r"Age\s*(\d+)",
                "field_type": "integer"
            },
            "phone": {
                "css": "a[href*='phone'], div[class*='phone']",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div[class*='address'], p[class*='address']",
                "field_type": "address"
            }
        }
    }
}


# SearchPeopleFree Configuration
# Based on real HTML structure from searchpeoplefree.com/find/link-pellow/mi/dowagiac
SEARCH_PEOPLE_FREE = {
    "name": "SearchPeopleFree",
    "base_url": "https://www.searchpeoplefree.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://www.searchpeoplefree.com/find/{name}/{state}/{city}",
        "crawl_mode": "list",  # Returns multiple results
        "engine_mode": "auto",
        
        "list_config": {
            "item_selector": "li.toc.l-i",  # Each result is in this container
            "item_links": {
                "css": "h2.h2 a",
                "attr": "href",
                "all": True
            }
        },
        
        "fields": {
            "name": {
                "css": "h2.h2 a",
                "field_type": "person_name"
            },
            "age": {
                "css": "h3.mb-3 span",
                "regex": r"(\d+)",  # Extract first number from "29 (1997 or 1996)"
                "field_type": "integer"
            },
            "phone": {
                "css": "ul.inline.current a[href*='phone-lookup']",
                "all": True,
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "address a",
                "field_type": "address"
            },
            "person_url": {
                "css": "h2.h2 a",
                "attr": "href",
                "field_type": "string"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://www.searchpeoplefree.com/phone-lookup/{phone}",
        "crawl_mode": "single",
        "engine_mode": "auto",
        
        "fields": {
            "name": {
                "css": "h2.h2 a",
                "field_type": "person_name"
            },
            "age": {
                "css": "h3.mb-3 span",
                "regex": r"(\d+)",
                "field_type": "integer"
            },
            "phone": {
                "css": "ul.inline.current a[href*='phone-lookup']",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "address a",
                "field_type": "address"
            }
        }
    }
}


# ZabaSearch Configuration
# Based on real HTML structure from zabasearch.com/people/link-pellow/michigan/dowagiac/
ZABA_SEARCH = {
    "name": "ZabaSearch",
    "base_url": "https://www.zabasearch.com",
    "free": True,
    "requires_auth": False,
    
    "search_by_name": {
        "url_template": "https://www.zabasearch.com/people/{name}/{state_full}/{city}/",
        "crawl_mode": "single",
        "engine_mode": "auto",
        
        "fields": {
            "name": {
                "css": "div#container-name h2 a",
                "field_type": "person_name"
            },
            "age": {
                "css": "div#container-name + div h3",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.section-box h3:contains('Associated Phone Numbers') + ul.showMore-list li a",
                "all": True,
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "email": {
                "css": "div.section-box h3:contains('Associated Email Addresses') + ul.showMore-list li",
                "all": True,
                "field_type": "email"
            },
            "address": {
                "css": "div.section-box h3:contains('Last Known Address') ~ div.flex p",
                "field_type": "address"
            }
        }
    },
    
    "search_by_phone": {
        "url_template": "https://www.zabasearch.com/phone/{phone}/",
        "crawl_mode": "single",
        "engine_mode": "auto",
        
        "fields": {
            "name": {
                "css": "div#container-name h2 a",
                "field_type": "person_name"
            },
            "age": {
                "css": "div#container-name + div h3",
                "field_type": "integer"
            },
            "phone": {
                "css": "div.section-box h3:contains('Associated Phone Numbers') + ul.showMore-list li a",
                "field_type": "phone",
                "smart_config": {"country": "US", "format": "E164"}
            },
            "address": {
                "css": "div.section-box h3:contains('Last Known Address') ~ div.flex p",
                "field_type": "address"
            }
        }
    }
}


# Site Registry
PEOPLE_SEARCH_SITES = {
    "fastpeoplesearch": FAST_PEOPLE_SEARCH,
    "truepeoplesearch": TRUE_PEOPLE_SEARCH,
    "thatsthem": THATS_THEM,
    "anywho": ANY_WHO,
    "searchpeoplefree": SEARCH_PEOPLE_FREE,
    "zabasearch": ZABA_SEARCH
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

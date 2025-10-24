#!/usr/bin/env python3
"""
Crexi API to Supabase Sync Script
Fetches industrial/warehouse listings from Crexi API and stores in Supabase
"""

import os
import sys
import requests
import json
from datetime import datetime
from supabase import create_client, Client
from typing import List, Dict, Any

# Configuration
CREXI_API_KEY = os.getenv('CREXI_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Crexi API Configuration
CREXI_BASE_URL = 'https://api.crexi.com'
CREXI_STAGE_URL = 'https://stage-api.crexi.com'  # Fallback for staging

# Target market configuration
TARGET_MARKET = 'Los Angeles'
PROPERTY_TYPES = ['Industrial', 'Warehouse', 'Flex', 'Distribution']


def validate_environment():
    """Validate required environment variables are set"""
    missing = []
    if not CREXI_API_KEY:
        missing.append('CREXI_API_KEY')
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_KEY:
        missing.append('SUPABASE_KEY')
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set them in your environment or .env file:")
        print("  export CREXI_API_KEY='your-api-key'")
        print("  export SUPABASE_URL='your-supabase-url'")
        print("  export SUPABASE_KEY='your-supabase-key'")
        sys.exit(1)


def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_crexi_listings() -> Dict[str, Any]:
    """
    Fetch listings from Crexi API
    
    Returns market snapshot and suite-level data
    """
    print(f"\n🔍 Fetching Crexi listings for {TARGET_MARKET}...")
    
    # Try different authentication methods and endpoints
    headers_options = [
        {'Authorization': f'Bearer {CREXI_API_KEY}'},
        {'x-api-key': CREXI_API_KEY},
        {'api-key': CREXI_API_KEY},
    ]
    
    # Common endpoint patterns for real estate APIs
    endpoint_options = [
        '/v1/listings',
        '/v1/properties',
        '/api/v1/listings',
        '/api/v1/properties',
        '/listings',
        '/properties',
    ]
    
    base_urls = [CREXI_BASE_URL, CREXI_STAGE_URL]
    
    # Search parameters
    params = {
        'market': TARGET_MARKET,
        'propertyType': 'Industrial',
        'transactionType': 'Lease',
        'status': 'Active',
    }
    
    print(f"\n🔑 Testing Crexi API authentication...")
    
    # Try different combinations
    for base_url in base_urls:
        print(f"\n  Trying base URL: {base_url}")
        for endpoint in endpoint_options:
            for headers in headers_options:
                url = f"{base_url}{endpoint}"
                try:
                    print(f"    Testing: {url}")
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        print(f"    ✅ Success! Found working endpoint")
                        data = response.json()
                        print(f"    📊 Received {len(data.get('results', data.get('data', [])))} listings")
                        return {
                            'success': True,
                            'endpoint': url,
                            'headers': headers,
                            'data': data
                        }
                    elif response.status_code == 401:
                        print(f"    ❌ 401 Unauthorized")
                    elif response.status_code == 403:
                        print(f"    ❌ 403 Forbidden")
                    elif response.status_code == 404:
                        print(f"    ❌ 404 Not Found")
                    else:
                        print(f"    ❌ {response.status_code}: {response.text[:100]}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ Request failed: {str(e)[:50]}")
                    continue
    
    print("\n❌ Could not find working Crexi API endpoint")
    print("\n💡 Next steps:")
    print("  1. Check Crexi API documentation for correct endpoint")
    print("  2. Verify API key is activated for staging/production")
    print("  3. Contact Crexi support for endpoint and authentication details")
    
    return {
        'success': False,
        'error': 'No working endpoint found'
    }


def process_market_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw API data into market snapshot format
    """
    # Extract listings from various possible response formats
    listings = data.get('results', data.get('data', data.get('listings', [])))
    
    return {
        'snapshot_date': datetime.now().isoformat(),
        'market_area': TARGET_MARKET,
        'property_type': 'Industrial',
        'total_properties': len(listings),
        'total_suites': sum(len(listing.get('suites', [listing])) for listing in listings),
        'notes': f"Synced from Crexi API",
        'raw_data': data
    }


def process_suite_snapshots(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process raw API data into suite-level snapshots
    """
    listings = data.get('results', data.get('data', data.get('listings', [])))
    suites = []
    
    for listing in listings:
        # Handle both property-level and suite-level data
        suite_list = listing.get('suites', [listing])
        
        for suite in suite_list:
            suite_snapshot = {
                'snapshot_date': datetime.now().isoformat(),
                'crexi_asset_id': str(listing.get('id', listing.get('assetId', ''))),
                'crexi_suite_id': str(suite.get('id', suite.get('suiteId', ''))),
                'market_area': TARGET_MARKET,
                'property_type': listing.get('propertyType', 'Industrial'),
                'suite_size': suite.get('size', suite.get('squareFeet')),
                'lease_rate': suite.get('rate', suite.get('leaseRate')),
                'rate_type': suite.get('rateType', 'Monthly'),
                'status': suite.get('status', 'Active'),
                'address': listing.get('address', suite.get('address')),
                'city': listing.get('city', suite.get('city')),
                'state': listing.get('state', suite.get('state')),
                'zip': listing.get('zip', suite.get('zipCode')),
                'raw_data': suite
            }
            suites.append(suite_snapshot)
    
    return suites


def save_to_supabase(supabase: Client, market_snapshot: Dict[str, Any], suite_snapshots: List[Dict[str, Any]]):
    """
    Save data to Supabase tables
    """
    print("\n💾 Saving data to Supabase...")
    
    try:
        # Insert market snapshot
        print(f"  Inserting market snapshot...")
        result = supabase.table('crexi_market_snapshots').insert(market_snapshot).execute()
        print(f"  ✅ Market snapshot saved")
        
        # Insert suite snapshots in batches
        if suite_snapshots:
            print(f"  Inserting {len(suite_snapshots)} suite snapshots...")
            batch_size = 100
            for i in range(0, len(suite_snapshots), batch_size):
                batch = suite_snapshots[i:i + batch_size]
                result = supabase.table('crexi_suite_snapshots').insert(batch).execute()
                print(f"  ✅ Inserted batch {i//batch_size + 1} ({len(batch)} suites)")
        
        print("\n✅ All data saved successfully!")
        
    except Exception as e:
        print(f"\n❌ Error saving to Supabase: {str(e)}")
        raise


def main():
    """
    Main execution function
    """
    print("="*60)
    print("🏭 Crexi to Supabase Sync - Los Angeles Industrial Listings")
    print("="*60)
    
    # Validate environment
    validate_environment()
    
    # Initialize Supabase client
    print("\n📊 Connecting to Supabase...")
    supabase = get_supabase_client()
    print("✅ Connected to Supabase")
    
    # Fetch data from Crexi
    result = fetch_crexi_listings()
    
    if not result['success']:
        print("\n⚠️  Sync completed with errors. Check output above.")
        sys.exit(1)
    
    # Process data
    print("\n🔄 Processing API response...")
    market_snapshot = process_market_snapshot(result['data'])
    suite_snapshots = process_suite_snapshots(result['data'])
    
    print(f"  Processed {market_snapshot['total_properties']} properties")
    print(f"  Processed {len(suite_snapshots)} suites")
    
    # Save to Supabase
    save_to_supabase(supabase, market_snapshot, suite_snapshots)
    
    print("\n" + "="*60)
    print("✅ Sync completed successfully!")
    print("="*60)
    print(f"\n📈 Summary:")
    print(f"  Market: {TARGET_MARKET}")
    print(f"  Properties: {market_snapshot['total_properties']}")
    print(f"  Suites: {len(suite_snapshots)}")
    print(f"  Timestamp: {market_snapshot['snapshot_date']}")
    print()


if __name__ == '__main__':
    main()
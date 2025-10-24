# Crexi Listings Sync

Automated sync of industrial/warehouse listings from Crexi API to Supabase for Los Angeles market analysis.

## Overview

This tool fetches industrial and warehouse listings from the Crexi API and stores them in Supabase for tracking and analysis. It captures both high-level market snapshots and detailed suite-level data.

## Features

- 🏭 **Industrial Focus**: Targets warehouse, industrial, flex, and distribution properties
- 📍 **Los Angeles Market**: Currently configured for LA market (easily extensible)
- 📊 **Dual-Layer Data**: Captures both market-level and suite-level metrics
- 🔄 **Automated Sync**: Can run weekly via GitHub Actions
- 🛡️ **Error Handling**: Robust error handling and logging

## Supabase Schema

### Market Snapshots Table
```sql
crexi_market_snapshots
- id (uuid)
- snapshot_date (timestamp)
- market_area (text) -- e.g., "Los Angeles"
- property_type (text) -- e.g., "Industrial"
- total_properties (integer)
- total_suites (integer)
- notes (text)
- raw_data (jsonb)
- created_at (timestamp)
```

### Suite Snapshots Table
```sql
crexi_suite_snapshots
- id (uuid)
- snapshot_date (timestamp)
- crexi_asset_id (text)
- crexi_suite_id (text)
- market_area (text)
- property_type (text)
- suite_size (integer)
- lease_rate (numeric)
- rate_type (text)
- status (text)
- address (text)
- city (text)
- state (text)
- zip (text)
- raw_data (jsonb)
- created_at (timestamp)
```

## Setup

### 1. Clone Repository
```bash
git clone https://github.com/RS-Nick/listings.git
cd listings
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
CREXI_API_KEY=03ac8bc3-acc4-4817-943a-5a76cd45e452
SUPABASE_URL=https://ypnusgohwpxqscexzmsr.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### 4. Run Sync

```bash
python sync_crexi.py
```

## GitHub Actions (Automated Weekly Sync)

To enable automated weekly syncs:

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   - `CREXI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

The workflow is set up to run weekly (see `.github/workflows/sync-crexi.yml`).

## Usage Examples

### Query Market Trends
```sql
-- Get latest market snapshot
SELECT 
  snapshot_date,
  total_properties,
  total_suites
FROM crexi_market_snapshots
WHERE market_area = 'Los Angeles'
ORDER BY snapshot_date DESC
LIMIT 1;
```

### Analyze Suite Inventory
```sql
-- Get average lease rates by size
SELECT 
  CASE 
    WHEN suite_size < 5000 THEN 'Small (<5K SF)'
    WHEN suite_size < 20000 THEN 'Medium (5-20K SF)'
    ELSE 'Large (>20K SF)'
  END as size_category,
  COUNT(*) as count,
  AVG(lease_rate) as avg_rate,
  MIN(lease_rate) as min_rate,
  MAX(lease_rate) as max_rate
FROM crexi_suite_snapshots
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM crexi_suite_snapshots)
  AND lease_rate IS NOT NULL
GROUP BY size_category
ORDER BY AVG(suite_size);
```

### Track Historical Changes
```sql
-- Compare week-over-week inventory changes
SELECT 
  snapshot_date::date as date,
  total_properties,
  total_suites,
  total_properties - LAG(total_properties) OVER (ORDER BY snapshot_date) as properties_change,
  total_suites - LAG(total_suites) OVER (ORDER BY snapshot_date) as suites_change
FROM crexi_market_snapshots
WHERE market_area = 'Los Angeles'
ORDER BY snapshot_date DESC
LIMIT 10;
```

## Troubleshooting

### API Connection Issues

The script will automatically test multiple endpoint patterns and authentication methods. If all fail, you'll see:

```
❌ Could not find working Crexi API endpoint

💡 Next steps:
  1. Check Crexi API documentation for correct endpoint
  2. Verify API key is activated for staging/production
  3. Contact Crexi support for endpoint and authentication details
```

### Common Issues

**401 Unauthorized**: API key may not be activated or incorrect format
**403 Forbidden**: API key may not have access to the requested endpoint
**404 Not Found**: Endpoint URL may be incorrect

### Getting Help

1. Check Crexi API documentation
2. Verify your API key status with Crexi support
3. Review the script's diagnostic output for specific error messages

## Extending to Other Markets

To add more markets, edit `sync_crexi.py`:

```python
TARGET_MARKET = 'San Francisco'  # Change this
```

Or run multiple syncs:

```bash
for market in "Los Angeles" "San Francisco" "Chicago"; do
  MARKET="$market" python sync_crexi.py
done
```

## License

MIT
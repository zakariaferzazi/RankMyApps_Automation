# RankMyApps Automation - Setup Guide

## Overview

This project contains three web scraping scripts that collect app data from Google Play Store and Apple App Store. The workflow:

1. **Scrape** apps from multiple sources (all 3 scripts)
2. **Upload** scraped files to WordPress via FTP

## Scripts

### 1. `scrape_google_play_apps.py`
- Scrapes Google Play Store by category
- Filters apps released in last 3 months (configurable)
- Outputs: `google_play_apps.csv`

### 2. `appstore_search_by_category.py`
- Scrapes Apple App Store by category across multiple countries
- Filters apps released in last 90 days (configurable)
- Outputs: `app_store_apps.csv`

### 3. `scrape_apps_by_similar.py`
- Scrapes Google Play Store using "similar apps" method
- Crawls related apps from a seed URL
- Outputs: `google_play_similar_apps.csv` (can be configured)

## GitHub Actions Workflow Setup

The workflow file `.github/workflows/scrape-and-upload.yml` automates everything, but requires FTP credentials.

### Step 1: Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

```
FTP_SERVER        = your-ftp-server.com
FTP_USERNAME      = your-ftp-username
FTP_PASSWORD      = your-ftp-password
```

**Where to find these values:**
- Contact your hosting provider or check your hosting control panel (cPanel, Plesk, etc.)
- For WordPress hosting, usually found in FTP/SFTP credentials section

### Step 2: Verify FTP Path

The workflow uploads to: `/wp-content/themes/astra-child/`

If your path is different, edit the workflow:
```yaml
server-dir: /your/custom/path/
```

### Step 3: Adjust Schedule

The workflow runs every Sunday at 2 AM UTC by default. To change:

Edit `.github/workflows/scrape-and-upload.yml`:
```yaml
on:
  schedule:
    - cron: '0 2 * * 0'  # Change these numbers
```

Cron format: `minute hour day month weekday`
- Example: `0 12 * * 1` = Every Monday at noon UTC

### Step 4: Test the Workflow

1. Go to GitHub → Actions tab
2. Select "Scrape Apps & Merge Data"
3. Click "Run workflow"

## Local Testing

To test locally before setting up GitHub Actions:

```bash
# Install dependencies
pip install -r requirements.txt

# Run scraping scripts
python scrape_google_play_apps.py
python scrape_apps_by_similar.py
python appstore_search_by_category.py
```

This will create all 3 CSV files with scraped data.

## Configuration Options

All scripts have **optional date filters** that you can enable/disable:

### 1. `scrape_google_play_apps.py`

Edit the CONFIG section at the top:

```python
CONFIG = {
    # Filter apps by release date (True = filter, False = include all apps)
    'FILTER_BY_RELEASE_DATE': True,
    
    # How many months back to include (only used if FILTER_BY_RELEASE_DATE = True)
    'MONTHS_THRESHOLD': 3,
}
```

**Examples:**
- `FILTER_BY_RELEASE_DATE = True, MONTHS_THRESHOLD = 3`: Only apps from last 3 months
- `FILTER_BY_RELEASE_DATE = False`: All apps regardless of date
- `FILTER_BY_RELEASE_DATE = True, MONTHS_THRESHOLD = 6`: Only apps from last 6 months

### 2. `appstore_search_by_category.py`

Edit the CONFIG section at the top:

```python
CONFIG = {
    # Filter apps by release date (True = filter, False = include all apps)
    'FILTER_BY_RELEASE_DATE': True,
    
    # How many days back to include (only used if FILTER_BY_RELEASE_DATE = True)
    'DAYS_THRESHOLD': 90,
}
```

**Examples:**
- `FILTER_BY_RELEASE_DATE = True, DAYS_THRESHOLD = 90`: Only apps from last 90 days
- `FILTER_BY_RELEASE_DATE = False`: All apps regardless of date
- `FILTER_BY_RELEASE_DATE = True, DAYS_THRESHOLD = 180`: Only apps from last 6 months

### 3. `scrape_apps_by_similar.py`

Edit the CONFIG section at the top:

```python
CONFIG = {
    'ONLY_RECENT_APPS': True,           # True = filter, False = include all apps
    'MONTHS_THRESHOLD': 3,              # How many months back to include
    # ... other settings
}
```

**Examples:**
- `ONLY_RECENT_APPS = True, MONTHS_THRESHOLD = 3`: Only apps from last 3 months
- `ONLY_RECENT_APPS = False`: All apps regardless of date
- `ONLY_RECENT_APPS = True, MONTHS_THRESHOLD = 12`: Only apps from last year

## Important Notes

⚠️ **File Uploads**
- All 3 files are uploaded to WordPress on each run
- New files replace old files (no merging)
- Configure date filters to control what apps are scraped

⚠️ **Workflow Settings**
- Check existing GitHub workflows for schedules and FTP settings
- Current workflows: `scrape_categories.yml`, `scrape_app_store.yml`, `scrape_similar.yml`

## Troubleshooting

### FTP Upload Fails
- Verify FTP credentials in GitHub Secrets
- Check that FTP server/port is correct
- Ensure disk space available on server

### Workflow Doesn't Run
- Check GitHub Actions is enabled for the repo
- Verify cron schedule syntax
- Check for syntax errors in YAML file

## Column Structure

CSV files should include these columns:
```
Niche, App Name, Logo URL, Install Count, Release Date, Rating, Review Count, App Link, Developer
```

The merge script automatically detects and uses these fields.

## Key Features

✅ FTP Upload - Direct to WordPress (all 3 files)  
✅ Error Resilient - Continues if one scraper fails  
✅ Scheduled or Manual - Run on schedule or anytime  
✅ **Optional Date Filtering** - Disable filters to get all apps  

## Need Help?

1. Check GitHub Actions logs for error details
2. Run scripts locally to test
3. Verify FTP credentials and path
4. Review workflow YAML syntax
5. Check the optional date filter configuration

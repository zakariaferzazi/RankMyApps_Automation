# RankMyApps Automation - Setup Guide

## Overview

This project contains three web scraping scripts that collect app data from Google Play Store and Apple App Store. The workflow:

1. **Scrape** apps from multiple sources
2. **Merge** new data with existing data (no duplicates)
3. **Upload** merged file to WordPress

## Scripts

### 1. `scrape_google_play_apps.py`
- Scrapes Google Play Store by category
- Filters apps released in last 3 months
- Outputs: `google_play_apps.csv`

### 2. `appstore_search_by_category.py`
- Scrapes Apple App Store by category across multiple countries
- Filters apps released in last 90 days
- Outputs: `app_store_apps.csv`

### 3. `scrape_apps_by_similar.py`
- Scrapes Google Play Store using "similar apps" method
- Crawls related apps from a seed URL
- Outputs: `google_play_similar_apps.csv` (can be configured)

### 4. `merge_csv_data.py` ✨ NEW
- Downloads existing CSV from WordPress
- Merges new scraped data
- **Deduplicates by App Link** (most reliable method)
- Creates merged file ready for upload

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
pip install -r requirements.txt requests

# Run scraping scripts
python scrape_google_play_apps.py
python scrape_apps_by_similar.py
python appstore_search_by_category.py

# Merge with existing data
python merge_csv_data.py
```

This will create `google_play_apps.csv` with merged data.

## Data Merge Logic

The `merge_csv_data.py` script:

1. ✓ Downloads existing CSV from your WordPress site
2. ✓ Loads new scraped data
3. ✓ **Deduplicates by "App Link" field** (most reliable)
4. ✓ Keeps all existing records
5. ✓ Adds/updates with new data
6. ✓ Saves merged result for upload

**Example:**
```
Existing data:  1000 apps
New data:        500 apps
Duplicates:      250 apps (same App Link)
After merge:   1250 apps (1000 + 250 new)
```

## Important Notes

⚠️ **No Git Commits**
- This workflow does NOT use git commits to avoid merge conflicts
- Uses FTP upload directly instead

⚠️ **Workflow Continues on Errors**
- If one scraper fails, others still run
- Merge only happens if data files exist
- Upload still proceeds even if some scrapers failed

⚠️ **Update Frequency**
- Only merge runs after scraping completes
- Check logs in GitHub Actions to verify success

⚠️ **File Naming**
- Google Play: `google_play_apps.csv`
- App Store: `app_store_apps.csv`
- Similar Apps: `google_play_similar_apps.csv`
- Merged output: `google_play_apps.csv`

## Troubleshooting

### FTP Upload Fails
- Verify FTP credentials in GitHub Secrets
- Check that FTP server/port is correct
- Ensure disk space available on server

### Merge Shows 0 Apps
- Verify download URL is correct and accessible
- Check CSV format matches expected headers
- Ensure `App Link` column exists

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

## Need Help?

1. Check GitHub Actions logs for error details
2. Run scripts locally to test
3. Verify FTP credentials and path
4. Review workflow YAML syntax

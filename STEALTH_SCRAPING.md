# Stealth Scraping Integration

## Overview

**UPDATE (Oct 2025)**: Switched from Botright to Botasaurus for stealth scraping due to compilation issues. Botasaurus has been integrated to attempt to bypass advanced bot protection on sites like LoopNet and Land.com.

**Status**: ⚠️ Botasaurus successfully installs and launches browser sessions, but LoopNet/Land.com still detect and terminate connections after ~8 seconds. Additional measures needed (proxies, non-headless mode, or alternative solutions).

## What Changed

### New Files

1. **src/scrapers/botasaurus_scraper.py** (Replaced botright_scraper.py)
   - Stealth browser automation using Botasaurus (Selenium-based)
   - Anti-detection features via BotasaurusDriver
   - Retry logic with exponential backoff
   - Random wait times (5-8s) for JavaScript execution
   - Enhanced error logging with HTML preview

### Modified Files

1. **src/main_with_db.py**
   - Added BotasaurusScraper import with fallback if not installed
   - Added botasaurus URL routing in `scrape_async_with_db()`
   - Falls back to PlaywrightScraper if botasaurus not available
   - Routes URLs to BotasaurusScraper based on `use_botasaurus` config flag

2. **src/config.py**
   - Changed `loopnet.com` to use `use_botasaurus: True` instead of `use_playwright`
   - Changed `land.com` to use `use_botasaurus: True` instead of `use_playwright`
   - Both sites limited to `max_concurrent: 1` for stealth

3. **src/scrapers/__init__.py**
   - Commented out broken stealth_browser imports (Botright-related)
   - Updated to reflect Botasaurus as the stealth solution

## Installation

```bash
pip install botasaurus
```

**Note**: Much simpler than Botright - only ~50MB of dependencies:
- botasaurus (core stealth framework)
- botasaurus-driver (Selenium-based driver)
- selenium (browser automation)
- No C++ compiler required
- No heavy AI models

**Why Botasaurus instead of Botright?**
- Botright requires Microsoft Visual C++ 14.0+ for greenlet compilation
- Botasaurus has no compilation requirements
- Simpler installation process
- Lighter weight (~50MB vs ~1.5GB)

## Configuration

Sites that require stealth scraping are configured in `src/config.py`:

```python
'loopnet.com': {
    'delay_between_requests': (8, 15),
    'requests_per_minute': 4,
    'max_retries': 3,
    'max_concurrent': 1,
    'timeout': 60,
    'use_botasaurus': True,  # Use Botasaurus stealth browser
    'wait_for_selector': 'h1'
},
'land.com': {
    'delay_between_requests': (2, 4),
    'requests_per_minute': 20,
    'max_retries': 3,
    'max_concurrent': 1,
    'timeout': 30,
    'use_botasaurus': True,  # Use Botasaurus stealth browser
    'wait_for_selector': 'h1'
},
```

## How It Works

1. **URL Routing**: Main scraper detects which sites need Botasaurus via `use_botasaurus: True` config flag
2. **Stealth Browser**: BotasaurusScraper launches Selenium-based stealth browser with:
   - Randomized user agents
   - Image blocking for faster loading
   - Random wait times (5-8s) for JavaScript execution
   - Retry logic with exponential backoff (2 attempts)
   - Enhanced error logging with HTML preview
3. **Fallback**: If Botasaurus not installed, falls back to standard PlaywrightScraper

**Current Limitations**:
- LoopNet and Land.com still detect and terminate connections after ~8 seconds
- Websocket disconnection indicates active bot detection
- May require additional measures: proxies, non-headless mode, or alternative solutions

## Usage

Same as before - the scraper automatically selects the right tool:

```bash
# LoopNet URLs will use BotasaurusScraper automatically
python -m src.main_with_db \
  --input loopnet_urls.csv \
  --output loopnet_data.csv \
  --concurrent 1

# Land.com URLs will use BotasaurusScraper automatically
python -m src.main_with_db \
  --input landcom_urls.csv \
  --output landcom_data.csv \
  --concurrent 1
```

## Testing (After Installation)

Once Botasaurus is installed, test with a few URLs:

```bash
# Test LoopNet (5 URLs)
python -m src.main_with_db \
  --input ../Scraping.Sites_Selectors_URLs/loopnet_georgia_properties.csv \
  --output data/loopnet_botasaurus_test.csv \
  --limit 5 \
  --concurrent 1

# Test Land.com (5 URLs)
python -m src.main_with_db \
  --input ../Scraping.Sites_Selectors_URLs/north_ga_landcom_urls_oct2025.csv \
  --output data/landcom_botasaurus_test.csv \
  --limit 5 \
  --concurrent 1
```

## Expected Results

### Before Botasaurus (with AsyncScraper/PlaywrightScraper)
- LoopNet: ERR_HTTP2_PROTOCOL_ERROR or TimeoutError - 0% success
- Land.com: ERR_HTTP2_PROTOCOL_ERROR or TimeoutError - 0% success

### After Botasaurus (Current Status)
- LoopNet: Browser connects but websocket disconnects after ~8s - 0% success (quality score 0)
- Land.com: Browser connects but websocket disconnects after ~8s - 0% success (quality score 0)

**Progress**: Botasaurus bypasses initial ERR_HTTP2_PROTOCOL_ERROR, but sites detect automation and terminate sessions.

**Next Steps Needed**:
1. Try non-headless mode (headless=False) for better stealth
2. Implement proxy rotation to avoid IP-based blocking
3. Consider alternative stealth solutions or manual data collection methods

## Troubleshooting

### Import Error
If you see:
```
ImportError: Botasaurus is not installed
```

Install Botasaurus:
```bash
pip install botasaurus
```

### Fallback Warning
If you see:
```
WARNING - Botasaurus not available - falling back to PlaywrightScraper
```

This means Botasaurus isn't installed - the scraper will try standard Playwright but will fail on protected sites with ERR_HTTP2_PROTOCOL_ERROR.

### Still Getting Blocked (Current Status)
Botasaurus is installed but LoopNet/Land.com still detect and block after ~8 seconds:

**Symptoms**:
- Websocket connects successfully
- Connection terminates after ~8 seconds with "Connection to remote host was lost - goodbye"
- Quality score 0 (no HTML content extracted)
- No ERR_HTTP2_PROTOCOL_ERROR (progress from standard scrapers!)

**Potential Solutions**:
1. **Try non-headless mode**: Edit `botasaurus_scraper.py` and set `headless=False` (slower but more realistic)
2. **Proxy rotation**: Implement proxy services to avoid IP-based detection
3. **Longer delays**: Increase `delay_between_requests` in config (8-15s → 15-30s)
4. **Alternative stealth frameworks**: May need commercial solutions or manual data collection

## Performance Notes

- BotasaurusScraper is ~2-3x slower than AsyncScraper (launches full browser)
- Each page load takes 10-15 seconds including 5-8s random wait for JS execution
- Resource blocking (images blocked via block_images=True) helps speed up loading
- Recommended max_concurrent: 1 (prevents detection)
- Retry logic: 2 attempts with exponential backoff (1s, 2s delays)

## Future Enhancements

1. **Proxy Rotation**: Integrate rotating proxies for IP diversity
2. **User Behavior Simulation**: Random mouse movements, scroll patterns
3. **CAPTCHA Solving**: Leverage built-in hcaptcha-challenger
4. **Session Persistence**: Reuse browser contexts for faster scraping
5. **Cookie Management**: Save/restore cookies to appear as returning user

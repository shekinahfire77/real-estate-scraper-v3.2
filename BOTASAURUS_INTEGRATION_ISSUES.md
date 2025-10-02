# Botasaurus Integration - Issues and Outcomes

**Date**: October 2, 2025
**Status**: ⚠️ Partial Success - Browser launches but sites still detect and block

## Background

Attempted to integrate Botright stealth browser for LoopNet and Land.com scraping, but encountered C++ compiler dependency issues. Switched to Botasaurus as a simpler alternative.

## Issues Encountered

### 1. Botright Installation Failure

**Problem**:
```
Failed building wheel for greenlet
error: Microsoft Visual C++ 14.0 or greater is required
```

**Root Cause**: Botright requires greenlet==3.0.1 which must be compiled from C++ source

**Resolution**: Abandoned Botright, switched to Botasaurus

### 2. Botasaurus Integration Errors

#### Error 1: BaseScraper Parameter Issue
```python
TypeError: BaseScraper.__init__() got an unexpected keyword argument 'max_concurrent'
```

**Fix**: Changed from `super().__init__(max_concurrent=max_concurrent)` to:
```python
super().__init__()
self.max_concurrent = max_concurrent
self.semaphore = asyncio.Semaphore(max_concurrent)
```

#### Error 2: Decorator Pattern Issue
```python
TypeError: 'module' object is not callable
```

**Fix**: Switched from @browser decorator to direct Driver instantiation:
```python
from botasaurus_driver import Driver as BotasaurusDriver
driver = BotasaurusDriver(headless=self.headless, ...)
```

#### Error 3: wait() Method Not Found
```python
AttributeError: 'Driver' object has no attribute 'wait'
```

**Fix**: Changed from `driver.wait(2)` to `time.sleep(2)`

#### Error 4: Import Path Issue
```python
ModuleNotFoundError: No module named 'src.scrapers.base_scraper'
```

**Fix**: Changed `from .base_scraper import BaseScraper` to `from .base import BaseScraper`

### 3. Bot Detection Still Active

**Symptoms**:
- Websocket connects successfully
- Connection terminates after ~8 seconds with "Connection to remote host was lost - goodbye"
- Quality score 0 (no HTML content extracted)
- No data saved to CSV

**Progress Made**:
- ✅ No longer getting ERR_HTTP2_PROTOCOL_ERROR (improvement!)
- ✅ Browser launches and connects
- ❌ Sites detect automation and terminate session before data can be extracted

## Implementation Details

### Files Created
1. **src/scrapers/botasaurus_scraper.py**
   - Selenium-based stealth browser automation
   - Random wait times (5-8s) for JavaScript execution
   - Retry logic with exponential backoff (2 attempts)
   - Enhanced error logging with HTML preview
   - Image blocking for faster loading

### Files Modified
1. **src/main_with_db.py**
   - Added BotasaurusScraper import with fallback
   - URL routing based on `use_botasaurus` config flag
   - Graceful fallback to PlaywrightScraper if not available

2. **src/config.py**
   - Changed LoopNet: `use_botasaurus: True` (was `use_playwright: True`)
   - Changed Land.com: `use_botasaurus: True` (was `use_playwright: True`)

3. **src/scrapers/__init__.py**
   - Commented out broken stealth_browser imports

4. **STEALTH_SCRAPING.md**
   - Fully updated with Botasaurus documentation
   - Current status and limitations documented
   - Next steps outlined

## Test Results

### Before Botasaurus
- AsyncScraper: ERR_HTTP2_PROTOCOL_ERROR or TimeoutError - 0% success
- PlaywrightScraper: ERR_HTTP2_PROTOCOL_ERROR - 0% success

### After Botasaurus
- Browser connects, websocket established
- Connection terminates after ~8 seconds
- Quality score 0, no data extracted
- 0% success rate (but different failure mode)

## Enhancements Attempted

1. ✅ Increased wait time from 2s to random 5-8s
2. ✅ Added retry logic with exponential backoff
3. ✅ Enhanced logging with HTML preview
4. ✅ Image blocking for faster loading
5. ✅ Random user agent selection

## Current Limitations

1. **Active Bot Detection**: LoopNet and Land.com actively terminate automated browser sessions
2. **Websocket Disconnection**: Consistent pattern of disconnection at ~8 seconds
3. **No HTML Extracted**: Quality score 0 indicates no content retrieved
4. **Headless Detection**: May need non-headless mode (headless=False) for better stealth

## Recommended Next Steps

### Short-term Solutions
1. **Try non-headless mode**
   - Edit `botasaurus_scraper.py` line 102: `headless=False`
   - Slower but may appear more realistic

2. **Increase delays between requests**
   - Change config `delay_between_requests`: (8, 15) → (15, 30)
   - Further reduce requests_per_minute

3. **Implement proxy rotation**
   - Integrate proxy services to avoid IP-based detection
   - Distribute requests across multiple IPs

### Long-term Solutions
1. **Commercial stealth solutions**
   - Consider paid services like ScrapingBee, Bright Data
   - May have better success rates but higher cost

2. **Alternative data sources**
   - Look for official APIs (if available)
   - Manual data collection for small datasets
   - Partnerships with data providers

3. **Botright with C++ compiler**
   - Install Microsoft Visual C++ 14.0+
   - Retry Botright installation
   - May offer better stealth capabilities than Botasaurus

## Conclusion

Botasaurus was successfully installed and integrated, representing progress from the ERR_HTTP2_PROTOCOL_ERROR failures. However, LoopNet and Land.com still detect and terminate automated sessions before data extraction. Additional measures (proxies, non-headless mode, or commercial solutions) are required for successful scraping of these protected sites.

**Success Rate**: 0% (but failure mode changed from immediate protocol error to session termination)

**Recommendation**: Consider commercial scraping services or alternative data sources for LoopNet and Land.com, as these sites employ sophisticated bot detection that may be difficult to bypass with open-source tools alone.

# Simple Improvements (Quick Wins)

Based on ChatGPT-5 audit - these can be implemented quickly without major refactoring.

## ✅ Completed

1. **Database files in .gitignore**
   - Added `*.db`, `*.sqlite`, `*.sqlite3` patterns
   - Removed tracked database files
   - Status: DONE

## 🔄 Ready to Implement

### 2. Failed URLs Error Report
**Complexity:** Low
**Impact:** High usability improvement
**Location:** `src/main_with_db.py`, `src/main.py`

**Implementation:**
```python
def save_failed_urls_report(self, output_path: str):
    """Save failed URLs with error reasons to CSV"""
    errors_file = output_path.replace('.csv', '_errors.csv')
    with open(errors_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'error_type', 'error_message', 'timestamp'])
        writer.writeheader()
        for url, error_info in self.failed_urls.items():
            writer.writerow(error_info)
```

**Benefits:**
- Users can easily review failed URLs
- Identify patterns in failures
- Reattempt failed scrapes

### 3. Convert Print to Logging
**Complexity:** Low
**Impact:** Better logging consistency
**Location:** `src/main_with_db.py` lines 306-420

**Implementation:**
- Replace `print()` with `logger.info()`
- Preserve formatting with proper string formatting
- Ensure summary appears in both console and log file

**Benefits:**
- All output captured in log files
- Consistent logging approach
- Better debugging in production

### 4. Configurable Batch Size
**Complexity:** Low
**Impact:** Performance tuning flexibility
**Location:** `config.yaml`, `src/config_manager.py`, `src/main_with_db.py`

**Implementation:**
```yaml
# config.yaml
scraping:
  concurrent_limit: 5
  batch_size: 10  # New parameter (default: 2 * concurrent_limit)
```

**Benefits:**
- Users can optimize for their use case
- Adaptive to different server capacities
- Better memory management control

### 5. Expand Type Hints
**Complexity:** Low
**Impact:** Better IDE support and code clarity
**Location:** Throughout codebase

**Files to update:**
- `src/main.py` - add return types
- `src/extractors_enhanced.py` - complete function signatures
- `src/scrapers/*.py` - add missing hints

**Benefits:**
- Better IDE autocomplete
- Catch type errors early
- Improved code documentation

### 6. Document Quality Scoring
**Complexity:** Very Low
**Impact:** User understanding
**Location:** `README.md`

**Add section:**
```markdown
## Quality Scoring System

The scraper assigns a quality score (0-100) to each property:

- **Required Fields (40 points):** price, address, bedrooms, bathrooms
- **Enhanced Fields (20 points):** sqft, listing_id, description, photos
- **Additional Data (20 points):** property_type, schools, amenities
- **Completeness Bonus (20 points):** All fields present

Threshold: Default is 50 (configurable with --threshold flag)
```

**Benefits:**
- Users understand quality filtering
- Know what to expect in output
- Can adjust threshold appropriately

---

## 📋 Complex Features (For Claude Opus 4.1)

These require significant refactoring and are beyond quick wins:

### Performance Optimization
- ⏭️ Async pipeline with `asyncio.as_completed()`
- ⏭️ Streaming CSV output
- ⏭️ HTML parsing optimization
- ⏭️ Extractor instance reuse

### Error Handling
- ⏭️ Async retry with exponential backoff
- ⏭️ Unified retry logic sync/async
- ⏭️ More specific exception handling

### Feature Completeness
- ⏭️ Multi-site extractor registry
- ⏭️ Pagination and crawling
- ⏭️ Proxy rotation support
- ⏭️ CAPTCHA handling
- ⏭️ Additional output formats

### Architecture
- ⏭️ BaseExtractor class hierarchy
- ⏭️ Consolidate config.py and config.yaml
- ⏭️ Unify main.py and main_with_db.py
- ⏭️ Switch to httpx for unified sync/async

### Testing
- ⏭️ End-to-end integration tests
- ⏭️ Edge case coverage
- ⏭️ Site-specific HTML tests
- ⏭️ Circuit breaker tests

---

## Implementation Priority

**Today (Simple):**
1. Document quality scoring in README ✍️
2. Convert print to logging 🔧
3. Add failed URLs error report 📝

**Next Session (Still Simple):**
4. Configurable batch size ⚙️
5. Expand type hints 📝

**Future (Complex - Opus 4.1):**
6. All architectural and performance improvements 🏗️

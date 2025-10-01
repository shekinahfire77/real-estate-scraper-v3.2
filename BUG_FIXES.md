# Bug Fixes for Real Estate Scraper V3

## Summary
This document details the bugs identified and fixed during code review of the pull request.

---

## Bug #1: Bare except clauses catching all exceptions

### Location
- `src/extractors_enhanced.py` lines 204, 230, 241, 299, 388
- `src/exporters/excel_exporter.py` line 210

### Issue
Using bare `except:` clauses catches **all** exceptions, including:
- `KeyboardInterrupt` - prevents users from stopping the program with Ctrl+C
- `SystemExit` - prevents proper program termination
- Other critical exceptions that should propagate

This makes debugging extremely difficult as errors are silently swallowed.

### Example of problematic code
```python
try:
    year = int(match.group())
    if 1800 < year <= 2030:
        return year
except:  # ❌ CATCHES EVERYTHING
    pass
```

### Fix
Replace bare `except:` with specific exception types:

```python
try:
    year = int(match.group())
    if 1800 < year <= 2030:
        return year
except (ValueError, AttributeError):  # ✅ SPECIFIC EXCEPTIONS
    pass
```

### Fixed exceptions by location
- Line 204 (`_extract_year_built`): `except (ValueError, AttributeError)`
- Line 230 (`_extract_days_on_market`): `except (ValueError, IndexError)`
- Line 241 (`_extract_hoa`): `except (ValueError, IndexError)`
- Line 299 (`_calculate_price_per_sqft`): `except (ValueError, ZeroDivisionError)`
- Line 388 (`_extract_security_deposit`): `except (ValueError, IndexError, AttributeError)`
- `excel_exporter.py` Line 210: `except (TypeError, AttributeError)`

---

## Bug #2: Missing dest parameter for --async argument

### Location
`src/main_with_db.py` line 490

### Issue
The `--async` argument didn't have a `dest` parameter, but the code tries to access `args.use_async`. Since `async` is a reserved keyword in Python, this would cause:
```python
AttributeError: 'Namespace' object has no attribute 'use_async'
```

The `--sync` flag correctly set `dest='use_async'`, but `--async` did not, causing an inconsistency.

### Example of problematic code
```python
parser.add_argument('--async', action='store_true', default=True,  # ❌ Missing dest
                   help='Use async scraping (default: True)')
parser.add_argument('--sync', dest='use_async', action='store_false',  # ✅ Has dest
                   help='Use synchronous scraping')

# Later in code:
use_async = args.use_async  # Would fail!
```

### Fix
Add `dest='use_async'` to the `--async` argument to match the pattern in `src/main.py`:

```python
parser.add_argument('--async', dest='use_async', action='store_true', default=True,  # ✅ Fixed
                   help='Use async scraping (default: True)')
```

---

## Bug #3: Page type detection checking HTML content for URL patterns

### Location
`src/extractors_enhanced.py` lines 374-377 in `_detect_page_type` method

### Issue
The method was checking for URL path patterns like `/rent/` and `/buy/` inside the HTML content instead of in the actual URL. This is problematic because:
1. HTML content might contain these strings in unrelated contexts
2. The actual URL structure is more reliable for classification
3. The URL parameter was available but not being used for this check

### Example of problematic code
```python
def _detect_page_type(self, html: str) -> str:  # ❌ URL not passed
    """Detect if page is for rental or for sale"""
    html_lower = html.lower()
    
    # Check URL for rent vs buy
    if '/rent/' in html_lower:  # ❌ Checking HTML, not URL!
        rental_score += 2
    if '/buy/' in html_lower or '/home/' in html_lower:  # ❌ Wrong variable
        sale_score += 2
```

### Fix
1. Add `url` parameter to `_detect_page_type` method signature
2. Create separate `url_lower` variable for URL checks
3. Update the method call in `extract_property_data` to pass the URL

```python
def _detect_page_type(self, html: str, url: str) -> str:  # ✅ URL parameter added
    """Detect if page is for rental or for sale"""
    html_lower = html.lower()
    url_lower = url.lower()  # ✅ Separate URL variable
    
    # Check URL for rent vs buy
    if '/rent/' in url_lower:  # ✅ Checking actual URL
        rental_score += 2
    if '/buy/' in url_lower or '/home/' in url_lower:  # ✅ Correct variable
        sale_score += 2
```

And update the call:
```python
page_type = self._detect_page_type(html, url)  # ✅ Pass both parameters
```

---

## Testing

All fixes were validated with the following tests:
1. ✅ Code compiles without syntax errors
2. ✅ `_detect_page_type` correctly uses URL parameter
3. ✅ Specific exceptions don't crash with invalid data
4. ✅ Zero division in `_calculate_price_per_sqft` returns None
5. ✅ `main_with_db.py` has correct `dest='use_async'` parameter

---

## Impact Assessment

### Severity: Medium-High
- **Bug #1 (Bare except)**: High - Could mask critical errors and make debugging impossible
- **Bug #2 (Missing dest)**: High - Would cause runtime error when using --async flag
- **Bug #3 (URL detection)**: Medium - Could cause incorrect property classification

### Risk of Breaking Changes: Low
All fixes are backward compatible and don't change public APIs.

---

## Best Practices Applied

1. **Always use specific exception types** instead of bare `except:`
2. **Be careful with reserved keywords** like `async` in argument names
3. **Use the right data source** for classification (URL vs HTML content)
4. **Test edge cases** like zero division, missing data, and invalid formats

---

## Files Modified
- `src/extractors_enhanced.py` - 7 changes (5 exception handlers + 2 for URL detection)
- `src/main_with_db.py` - 1 change (dest parameter)
- `src/exporters/excel_exporter.py` - 1 change (exception handler)

Total: 9 bug fixes across 3 files

# Tests

These are headless-browser checks for `index.html`, written with Python and Playwright.

```
pip install playwright && python -m playwright install chromium
python tests/test_core.py        # bug fixes, migration, features (28 checks)
python tests/test_edge_cases.py  # edge cases from code review (16 checks)
```

To run against a Chrome binary already on the machine, set `CHROME=/path/to/chrome`. Each script exits non-zero if any check fails.

`fixtures/legacy_v13.json` is a layout saved by the pre-v14 app. The tests use it to check that old saves are upgraded correctly.

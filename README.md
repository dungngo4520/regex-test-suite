# Regex Test Suite

Test Suite for regex engines.

Usage

```bash
python3 bin/validate_suite.py            # check JSON tests
python3 bin/run_tests.py                 # run all tests
python3 bin/run_tests.py -f <path>.json  # run one file
```

Customize

- Add new `.json` files under `tests/` following the existing format.
- Extend `bin/run_tests.py` for other engines or flag semantics.

License

MIT

Example

```json
[
 {
  "description": "Simple literal",
  "pattern": "hello",
  "flags": "",
  "tests": [
   {
    "description": "exact match",
    "input": "hello",
    "matches": [
     { "start": 0, "end": 5, "match": "hello", "groups": [] }
    ]
   },
   {
    "description": "no match",
    "input": "world",
    "matches": []
   }
  ]
 }
]
```

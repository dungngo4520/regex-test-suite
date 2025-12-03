# Regex Test Suite

Regex test suite.

## Usage

```bash
# Validate test files
python3 bin/validate_suite.py

# Run tests
node bin/run_tests.js tests               # JavaScript
perl bin/run_tests.pl tests               # Perl
python3 bin/run_tests.py tests            # Python
```

## Annotations

Annotations used in patterns:

| Annotation | Description |
|------------|-------------|
| `@[unicode:XXXX]` | Unicode character by hex code point |
| `@[hex:XX]` | Character by hexadecimal value |
| `@[octal:NNN]` | Character by octal value |
| `@[control:X]` | Control character |
| `@[named:name,pattern]` | Named capture group |
| `@[backref:name]` | Backreference to named group |

## Test Format

```json
[
  {
    "description": "Unicode space",
    "pattern": "@[unicode:00A0]+",
    "flags": "u",
    "tests": [
      {
        "description": "match non-breaking space",
        "input": "\u00A0",
        "matches": [
          { "start": 0, "end": 1, "match": "\u00A0", "groups": [] }
        ]
      }
    ]
  }
]
```

## License

MIT

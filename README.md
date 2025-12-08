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
| `@[unicode:XXXX]` | Unicode character by hex code point (4-6 hex digits) |
| `@[hex:XX]` | Character by hexadecimal value (2 hex digits) |
| `@[octal:NNN]` | Character by octal value (1-3 octal digits) |
| `@[control:X]` | Control character (A-Z) |
| `@[named:name,pattern]` | Named capture group |
| `@[backref:name]` | Backreference to named group |
| `@[conditional:cond,yes,no]` | Conditional pattern (if-then-else) |
| `@[recursive]` | Recursive pattern match |
| `@[subroutine:name]` | Call to named subroutine |
| `@[verb:NAME]` | Backtracking control verb (SKIP, FAIL, PRUNE, COMMIT, etc.) |
| `@[atomic:pattern]` | Atomic group (no backtracking) |

## Test Format

```json
[
  {
    "description": "Test case description",
    "pattern": "@[unicode:00A0]+",
    "flags": "u",
    "engine": "all",
    "minVersion": "",
    "skipEngines": [],
    "expectCompileError": false,
    "tests": [
      {
        "description": "Individual test description",
        "input": "\u00A0",
        "matches": [
          { 
            "start": 0, 
            "end": 1, 
            "match": "\u00A0", 
            "groups": [],
            "namedGroups": {}
          }
        ]
      }
    ]
  }
]
```

### Format Fields

**Top-level test case:**

- `description`: Test case description (required)
- `pattern`: The regex pattern (required)
- `flags`: Regex flags: `i` (case-insensitive), `m` (multiline), `s` (dotall), `g` (global), `x` (verbose), `u` (unicode) (optional, default: "")
- `engine`: Target engine: "all", "pcre", "perl", "python", "javascript", "java", etc. (optional, default: "all")
- `minVersion`: Minimum engine version required (optional)
- `skipEngines`: Array of engines to skip this test (optional)
- `expectCompileError`: Whether pattern should fail to compile (optional, default: false)
- `tests`: Array of individual test cases (required)

**Individual test:**

- `description`: Test description (required)
- `input`: Input string to match against (required)
- `matches`: Array of expected matches (required, empty array for no match)

**Match object:**

- `start`: Start position (0-indexed, required)
- `end`: End position (exclusive, required)
- `match`: Matched text (required)
- `groups`: Array of captured groups, `null` for optional unmatched groups (optional)
- `namedGroups`: Object with named group captures (optional)

## License

MIT

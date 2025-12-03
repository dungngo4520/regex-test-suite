#!/usr/bin/env python3

import json, re, sys
from pathlib import Path

# --- Minimal, focused Python runner ---


def translate_pattern(p: str) -> str:
    prev = None
    while p != prev:
        prev = p

        def uni(m):
            code = m.group(1)
            return f"\\u{code.zfill(4)}" if len(code) <= 4 else f"\\U{code.zfill(8)}"

        p = re.sub(r"@\[unicode:([0-9A-Fa-f]{4,6})\]", uni, p)
        p = re.sub(r"@\[hex:([0-9A-Fa-f]{2})\]", r"\\x\1", p)
        p = re.sub(r"@\[octal:([0-7]{1,3})\]", r"\\\1", p)
        p = re.sub(r"@\[control:([A-Z])\]", lambda m: chr(ord(m.group(1)) - 64), p)
        p = re.sub(r"@\[named:(\w+),(.+?)\]", r"(?P<\1>\2)", p)
        p = re.sub(r"@\[backref:(\w+)\]", r"(?P=\1)", p)
    return p


def translate_data(s: str) -> str:
    prev = None
    while s != prev:
        prev = s
        s = re.sub(
            r"@\[unicode:([0-9A-Fa-f]{4,6})\]", lambda m: chr(int(m.group(1), 16)), s
        )
        s = re.sub(r"@\[hex:([0-9A-Fa-f]{2})\]", lambda m: chr(int(m.group(1), 16)), s)
        s = re.sub(r"@\[octal:([0-7]{1,3})\]", lambda m: chr(int(m.group(1), 8)), s)
        s = re.sub(r"@\[control:([A-Z])\]", lambda m: chr(ord(m.group(1)) - 64), s)
    return s


def compile_re(p: str, flags: str):
    try:
        p = translate_pattern(p)
        f = 0
        f |= re.IGNORECASE if "i" in flags else 0
        f |= re.MULTILINE if "m" in flags else 0
        f |= re.DOTALL if "s" in flags else 0
        f |= re.VERBOSE if "x" in flags else 0
        f |= re.UNICODE if "u" in flags else 0
        return re.compile(p, f)
    except re.error:
        return None


def exec_all(rx, input_s: str, is_global: bool):
    return (
        list(rx.finditer(input_s))
        if is_global
        else ([m] if (m := rx.search(input_s)) else [])
    )


def compare(m, exp):
    if m.start() != exp["start"]:
        return f"Start mismatch: expected {exp['start']}, got {m.start()}"
    if m.end() != exp["end"]:
        return f"End mismatch: expected {exp['end']}, got {m.end()}"
    if m.group(0) != exp["match"]:
        return f"Text mismatch: expected '{exp['match']}', got '{m.group(0)}'"
    if "groups" in exp:
        ag = list(m.groups())
        eg = exp["groups"]
        if len(ag) != len(eg):
            return f"Group count mismatch: expected {len(eg)}, got {len(ag)}"
        for i, (e, a) in enumerate(zip(eg, ag)):
            if e != a:
                return f"Group {i + 1} mismatch: expected '{e}', got '{a}'"
    return None


def run_case(case_def, test, stats):
    stats["total"] += 1
    rx = compile_re(case_def.get("pattern", ""), case_def.get("flags", ""))
    input_s = translate_data(test["input"])
    expected = [{**m, "match": translate_data(m["match"])} for m in test["matches"]]
    if rx is None:
        if not expected:
            stats["passed"] += 1
            return
        stats["failed"] += 1
        raise RuntimeError("Failed to compile pattern")
    matches = exec_all(rx, input_s, "g" in (case_def.get("flags", "")))
    if len(matches) != len(expected):
        stats["failed"] += 1
        raise RuntimeError(
            f"Match count mismatch: expected {len(expected)}, got {len(matches)}"
        )
    for i, (m, e) in enumerate(zip(matches, expected)):
        err = compare(m, e)
        if err:
            stats["failed"] += 1
            raise RuntimeError(f"Match {i}: {err}")
    stats["passed"] += 1


def run_file(file_path: Path, stats, verbose=False) -> bool:
    cases = json.loads(Path(file_path).read_text(encoding="utf-8"))
    ok = True
    for c in cases:
        for t in c["tests"]:
            try:
                run_case(c, t, stats)
                if verbose:
                    print(f"    OK {t['description']}")
            except Exception as e:
                ok = False
                if verbose:
                    print(f"    FAILED {t['description']}\n      {e}")
    return ok


def find_json(dir_path: Path):
    return sorted(dir_path.rglob("*.json"))


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("-f", "--file", type=str)
    args = ap.parse_args()

    repo_root = Path(__file__).parent.parent
    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        print(f"Error: Tests directory not found: {tests_dir}")
        return 1

    stats = {"total": 0, "passed": 0, "failed": 0}

    if args.file:
        test_file = repo_root / args.file
        if not test_file.exists():
            print(f"Error: File not found: {test_file}")
            return 1
        print(f"Running tests from {test_file.name}")
        print("=" * 70)
        ok = run_file(test_file, stats, True)
        print("\n" + "=" * 70)
        print(f"Total: {stats['total']} tests")
        print(f"Passed: {stats['passed']}")
        print(f"Failed: {stats['failed']}")
        return 0 if ok else 1

    files = find_json(tests_dir)
    print("Running Regex Test Suite")
    print(f"Found {len(files)} test files\n")
    files_ok = 0
    for f in files:
        rel = f.relative_to(tests_dir.parent)
        print(rel)
        ok = run_file(f, stats, args.verbose)
        if ok:
            files_ok += 1
            if not args.verbose:
                print("All tests passed")
        else:
            if not args.verbose:
                print("Some tests failed")
        print()
    print(f"Total Tests: {stats['total']}")
    pct = (100 * stats["passed"] / stats["total"]) if stats["total"] else 0
    print(f"Passed: {stats['passed']} ({pct:.1f}%)")
    print(f"Failed: {stats['failed']}")
    print(f"Files: {files_ok}/{len(files)} passed")
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

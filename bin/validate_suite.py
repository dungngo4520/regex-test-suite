#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def validate_test_file(file_path: Path) -> List[str]:
    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except Exception as e:
        return [f"Error reading file: {e}"]

    if not isinstance(data, list):
        errors.append("Root element must be an array")
        return errors

    for idx, test_case in enumerate(data):
        prefix = f"Test case {idx}: "

        if not isinstance(test_case, dict):
            errors.append(f"{prefix}Must be an object")
            continue

        required_fields = ["description", "pattern", "tests"]
        for field in required_fields:
            if field not in test_case:
                errors.append(f"{prefix}Missing required field '{field}'")

        if "description" in test_case:
            if not isinstance(test_case["description"], str):
                errors.append(f"{prefix}'description' must be a string")
            elif not test_case["description"].strip():
                errors.append(f"{prefix}'description' cannot be empty")

        if "pattern" in test_case:
            if not isinstance(test_case["pattern"], str):
                errors.append(f"{prefix}'pattern' must be a string")

        if "flags" in test_case:
            if not isinstance(test_case["flags"], str):
                errors.append(f"{prefix}'flags' must be a string")

        if "tests" in test_case:
            if not isinstance(test_case["tests"], list):
                errors.append(f"{prefix}'tests' must be an array")
            elif len(test_case["tests"]) == 0:
                errors.append(f"{prefix}'tests' array cannot be empty")
            else:
                for test_idx, test in enumerate(test_case["tests"]):
                    test_prefix = f"{prefix}Test {test_idx}: "

                    if not isinstance(test, dict):
                        errors.append(f"{test_prefix}Must be an object")
                        continue

                    test_required = ["description", "input", "matches"]
                    for field in test_required:
                        if field not in test:
                            errors.append(
                                f"{test_prefix}Missing required field '{field}'"
                            )

                    if "description" in test:
                        if not isinstance(test["description"], str):
                            errors.append(
                                f"{test_prefix}'description' must be a string"
                            )

                    if "input" in test:
                        if not isinstance(test["input"], str):
                            errors.append(f"{test_prefix}'input' must be a string")

                    if "matches" in test:
                        if not isinstance(test["matches"], list):
                            errors.append(f"{test_prefix}'matches' must be an array")
                        else:
                            for match_idx, match in enumerate(test["matches"]):
                                match_prefix = f"{test_prefix}Match {match_idx}: "

                                if not isinstance(match, dict):
                                    errors.append(f"{match_prefix}Must be an object")
                                    continue

                                match_required = ["start", "end", "match"]
                                for field in match_required:
                                    if field not in match:
                                        errors.append(
                                            f"{match_prefix}Missing required field '{field}'"
                                        )

                                if "start" in match:
                                    if not isinstance(match["start"], int):
                                        errors.append(
                                            f"{match_prefix}'start' must be an integer"
                                        )
                                    elif match["start"] < 0:
                                        errors.append(
                                            f"{match_prefix}'start' must be non-negative"
                                        )

                                if "end" in match:
                                    if not isinstance(match["end"], int):
                                        errors.append(
                                            f"{match_prefix}'end' must be an integer"
                                        )
                                    elif match["end"] < 0:
                                        errors.append(
                                            f"{match_prefix}'end' must be non-negative"
                                        )

                                if "start" in match and "end" in match:
                                    if isinstance(match["start"], int) and isinstance(
                                        match["end"], int
                                    ):
                                        if match["end"] < match["start"]:
                                            errors.append(
                                                f"{match_prefix}'end' must be >= 'start'"
                                            )

                                if "match" in match:
                                    if not isinstance(match["match"], str):
                                        errors.append(
                                            f"{match_prefix}'match' must be a string"
                                        )

                                if "groups" in match:
                                    if not isinstance(match["groups"], list):
                                        errors.append(
                                            f"{match_prefix}'groups' must be an array"
                                        )

    return errors


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    tests_dir = repo_root / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found: {tests_dir}")
        return 1

    test_files = list(tests_dir.rglob("*.json"))

    if not test_files:
        print(f"Warning: No test files found in {tests_dir}")
        return 0

    print(f"Validating {len(test_files)} test files...")
    print()

    total_errors = 0
    files_with_errors = 0

    for test_file in sorted(test_files):
        relative_path = test_file.relative_to(repo_root)
        errors = validate_test_file(test_file)

        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            print(f"{relative_path}")
            for error in errors:
                print(f"  - {error}")
            print()
        else:
            print(f"{relative_path}")

    print()
    print("=" * 70)
    if total_errors == 0:
        print("All test files are valid!")
        return 0
    else:
        print(f"Found {total_errors} error(s) in {files_with_errors} file(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

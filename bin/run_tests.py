#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class TestResult:
    def __init__(self, passed: bool, message: str = ""):
        self.passed = passed
        self.message = message


class RegexTestRunner:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0

    def compile_pattern(self, pattern: str, flags: str) -> Optional[re.Pattern]:
        try:
            flag_value = 0
            if "i" in flags:
                flag_value |= re.IGNORECASE
            if "m" in flags:
                flag_value |= re.MULTILINE
            if "s" in flags:
                flag_value |= re.DOTALL
            if "x" in flags:
                flag_value |= re.VERBOSE
            if "u" in flags:
                flag_value |= re.UNICODE

            return re.compile(pattern, flag_value)
        except re.error as e:
            return None

    def find_matches(
        self, pattern: re.Pattern, input_str: str, global_flag: bool = False
    ):
        if global_flag:
            return list(pattern.finditer(input_str))
        else:
            match = pattern.search(input_str)
            return [match] if match else []

    def compare_match(self, actual: re.Match, expected: Dict[str, Any]) -> TestResult:
        if actual.start() != expected["start"]:
            return TestResult(
                False,
                f"Start position mismatch: expected {expected['start']}, got {actual.start()}",
            )

        if actual.end() != expected["end"]:
            return TestResult(
                False,
                f"End position mismatch: expected {expected['end']}, got {actual.end()}",
            )

        if actual.group(0) != expected["match"]:
            return TestResult(
                False,
                f"Match text mismatch: expected '{expected['match']}', got '{actual.group(0)}'",
            )

        if "groups" in expected:
            expected_groups = expected["groups"]
            actual_groups = list(actual.groups())

            if len(actual_groups) != len(expected_groups):
                return TestResult(
                    False,
                    f"Group count mismatch: expected {len(expected_groups)}, got {len(actual_groups)}",
                )

            for i, (exp_group, act_group) in enumerate(
                zip(expected_groups, actual_groups)
            ):
                if exp_group != act_group:
                    return TestResult(
                        False,
                        f"Group {i + 1} mismatch: expected '{exp_group}', got '{act_group}'",
                    )

        return TestResult(True)

    def run_test(self, test_case: Dict[str, Any], test: Dict[str, Any]) -> TestResult:
        self.total_tests += 1

        pattern_str = test_case["pattern"]
        flags = test_case.get("flags", "")
        input_str = test["input"]
        expected_matches = test["matches"]

        pattern = self.compile_pattern(pattern_str, flags)
        if pattern is None:
            if len(expected_matches) == 0:
                self.passed_tests += 1
                return TestResult(True, "Invalid pattern correctly rejected")
            else:
                self.failed_tests += 1
                return TestResult(False, "Failed to compile pattern")

        global_flag = "g" in flags
        actual_matches = self.find_matches(pattern, input_str, global_flag)

        if len(actual_matches) != len(expected_matches):
            self.failed_tests += 1
            return TestResult(
                False,
                f"Match count mismatch: expected {len(expected_matches)}, got {len(actual_matches)}",
            )

        for i, (actual, expected) in enumerate(zip(actual_matches, expected_matches)):
            result = self.compare_match(actual, expected)
            if not result.passed:
                self.failed_tests += 1
                return TestResult(False, f"Match {i}: {result.message}")

        self.passed_tests += 1
        return TestResult(True)

    def run_test_file(self, file_path: Path, verbose: bool = False) -> bool:
        with open(file_path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        file_passed = True

        for test_case in test_cases:
            if verbose:
                print(f"  {test_case['description']}")

            for test in test_case["tests"]:
                result = self.run_test(test_case, test)

                if verbose:
                    status = "OK" if result.passed else "FAILED"
                    print(f"    {status} {test['description']}")
                    if not result.passed:
                        print(f"      {result.message}")

                if not result.passed:
                    file_passed = False

        return file_passed

    def run_suite(self, tests_dir: Path, verbose: bool = False):
        test_files = sorted(tests_dir.rglob("*.json"))

        print("Running Regex Test Suite")
        print(f"Found {len(test_files)} test files")
        print()

        passed_files = 0
        failed_files = 0

        for test_file in test_files:
            relative_path = test_file.relative_to(tests_dir.parent)
            print(f"{relative_path}")

            file_passed = self.run_test_file(test_file, verbose)

            if file_passed:
                passed_files += 1
                if not verbose:
                    print("All tests passed")
            else:
                failed_files += 1
                if not verbose:
                    print("Some tests failed")

            print()

        print(f"Total Tests: {self.total_tests}")
        print(
            f"Passed: {self.passed_tests} ({100 * self.passed_tests / self.total_tests:.1f}%)"
        )
        print(f"Failed: {self.failed_tests}")
        print(f"Files: {passed_files}/{len(test_files)} passed")

        return self.failed_tests == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the Regex Test Suite")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output for each test",
    )
    parser.add_argument("-f", "--file", type=str, help="Run tests from a specific file")

    args = parser.parse_args()

    # Get paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    tests_dir = repo_root / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found: {tests_dir}")
        return 1

    runner = RegexTestRunner()

    if args.file:
        # Run single file
        test_file = repo_root / args.file
        if not test_file.exists():
            print(f"Error: File not found: {test_file}")
            return 1

        print(f"Running tests from {test_file.name}")
        print("=" * 70)
        print()

        success = runner.run_test_file(test_file, verbose=True)

        print()
        print("=" * 70)
        print(f"Total: {runner.total_tests} tests")
        print(f"Passed: {runner.passed_tests}")
        print(f"Failed: {runner.failed_tests}")

        return 0 if success else 1
    else:
        # Run full suite
        success = runner.run_suite(tests_dir, verbose=args.verbose)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

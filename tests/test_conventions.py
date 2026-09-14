"""Tests for scripts/validate-conventions.sh.

The Git hooks and the repository-standards workflow both delegate to that
script, so these cases pin down exactly which branch names and commit subjects
the project accepts. They shell out to the script itself rather than
re-implementing the patterns, which would only test a copy of the rules.
"""

import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate-conventions.sh"

# A POSIX shell ships with Git for Windows, but it is not always on PATH.
SH = shutil.which("sh")


@unittest.skipUnless(SH, "requires a POSIX shell on PATH")
class ValidateConventionsTestCase(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [SH, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_accepted(self, *args):
        result = self.run_script(*args)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"expected {args} to be accepted\n{result.stderr}",
        )

    def assert_rejected(self, *args):
        result = self.run_script(*args)
        self.assertEqual(
            result.returncode,
            1,
            msg=f"expected {args} to be rejected, output was:\n{result.stdout}",
        )
        return result


class BranchNameTests(ValidateConventionsTestCase):
    VALID = [
        "feat/crf-3-cv-template-export",
        "fix/crf-42-token-expiry",
        "chore/crf-7-bump-django",
        "docs/crf-1-readme",
        "hotfix/crf-9-a",
        "release/crf-100-v1-0-0",
        "refactor/crf-15-split-user-service-2",
    ]

    INVALID = {
        "feat/cv-template-export": "no ticket reference",
        "feat/crf-3": "no description",
        "feat/crf3-export": "no hyphen after the ticket key",
        "feat/crf-x-export": "ticket number is not a number",
        "feat/crf-3-CV-Export": "uppercase",
        "feat/crf-3-cv_export": "underscore",
        "feature/crf-3-export": "type is not allowed",
        "crf-3-export": "no type",
        "feat/crf-3-": "trailing hyphen",
        "feat//crf-3-export": "empty segment",
        "": "empty branch name",
    }

    def test_valid_branch_names_are_accepted(self):
        for branch in self.VALID:
            with self.subTest(branch=branch):
                self.assert_accepted("branch", branch)

    def test_invalid_branch_names_are_rejected(self):
        for branch, reason in self.INVALID.items():
            with self.subTest(branch=branch, reason=reason):
                self.assert_rejected("branch", branch)

    def test_protected_branches_skip_the_pattern(self):
        for branch in ("main", "develop"):
            with self.subTest(branch=branch):
                self.assert_accepted("branch", branch)

    def test_rejection_explains_the_format_with_examples(self):
        stderr = self.assert_rejected("branch", "feat/cv-export").stderr

        self.assertIn("<type>/crf-<ticket-number>-<short-kebab-case-description>", stderr)
        self.assertIn("feat/crf-3-cv-template-export", stderr)
        self.assertIn("git branch -m", stderr)
        self.assertIn("CONTRIBUTING.md", stderr)


class CommitSubjectTests(ValidateConventionsTestCase):
    VALID = [
        "feat(auth): add refresh token rotation",
        "fix: reject expired reset links",
        "docs: document local setup",
        "feat(api)!: drop v1 endpoints",
        "chore(deps/django): bump to 6.1.1",
        "revert: feat(auth): add refresh token rotation",
    ]

    INVALID = {
        "added login": "no type",
        "Feat: add login": "type is not lowercase",
        "feat add login": "no colon",
        "feat:add login": "no space after the colon",
        "feature: add login": "type is not allowed",
        "feat: ": "no description",
        "feat(): add login": "empty scope",
        "": "empty subject",
    }

    def test_valid_subjects_are_accepted(self):
        for subject in self.VALID:
            with self.subTest(subject=subject):
                self.assert_accepted("commit", subject)

    def test_invalid_subjects_are_rejected(self):
        for subject, reason in self.INVALID.items():
            with self.subTest(subject=subject, reason=reason):
                self.assert_rejected("commit", subject)

    def test_git_generated_subjects_are_exempt(self):
        self.assert_accepted("commit", "Merge pull request #4 from org/branch")
        self.assert_accepted("commit", 'Revert "feat: add login"')

    def test_subject_length_limit_is_72_characters(self):
        prefix = "feat: "
        at_limit = prefix + "x" * (72 - len(prefix))
        over_limit = at_limit + "x"

        self.assert_accepted("commit", at_limit)
        stderr = self.assert_rejected("commit", over_limit).stderr

        self.assertIn("73 characters", stderr)
        self.assertIn("limit is 72", stderr)

    def test_rejection_explains_the_format_with_examples(self):
        stderr = self.assert_rejected("commit", "added login").stderr

        self.assertIn("<type>(optional-scope): <description>", stderr)
        self.assertIn("feat(auth): add refresh token rotation", stderr)
        self.assertIn("git commit --amend", stderr)
        self.assertIn("CONTRIBUTING.md", stderr)


class IsProtectedTests(ValidateConventionsTestCase):
    def test_protected_branches_exit_zero(self):
        for branch in ("main", "develop"):
            with self.subTest(branch=branch):
                self.assert_accepted("is-protected", branch)

    def test_other_branches_exit_non_zero(self):
        for branch in ("feat/crf-1-thing", "mainline", "develop-2", ""):
            with self.subTest(branch=branch):
                self.assert_rejected("is-protected", branch)


class UsageTests(ValidateConventionsTestCase):
    def test_missing_arguments_report_usage(self):
        result = self.run_script()

        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)

    def test_unknown_check_is_rejected(self):
        result = self.run_script("branchname", "feat/crf-1-thing")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown validation type", result.stderr)

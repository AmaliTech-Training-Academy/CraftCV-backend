"""Tests for the tests-required gate in scripts/check.sh.

The pre-commit hook calls it to reject a behaviour change that arrives without
a test, so the rule about which paths count as source and which count as tests
is worth pinning down.
"""

import os
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check.sh"

SH = shutil.which("sh")


@unittest.skipUnless(SH, "requires a POSIX shell on PATH")
class TestsRequiredTestCase(unittest.TestCase):
    def run_check(self, *paths, env=None):
        environment = {**os.environ, "SKIP_TEST_CHECK": "0"}
        if env:
            environment.update(env)

        return subprocess.run(
            [SH, str(SCRIPT), "tests-required", *paths],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

    def assert_allowed(self, *paths, env=None):
        result = self.run_check(*paths, env=env)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"expected {paths} to be allowed\n{result.stderr}",
        )
        return result

    def assert_blocked(self, *paths):
        result = self.run_check(*paths)
        self.assertEqual(
            result.returncode,
            1,
            msg=f"expected {paths} to be blocked, output was:\n{result.stdout}",
        )
        return result


class SourceWithoutTestTests(TestsRequiredTestCase):
    def test_source_change_alone_is_blocked(self):
        for path in (
            "apps/users/models.py",
            "apps/users/views.py",
            "apps/cv_builder/serializers.py",
            "craftcv/urls.py",
        ):
            with self.subTest(path=path):
                self.assert_blocked(path)

    def test_source_change_with_a_test_is_allowed(self):
        self.assert_allowed("apps/users/models.py", "apps/users/tests.py")
        self.assert_allowed("apps/users/views.py", "tests/test_views.py")
        self.assert_allowed("craftcv/urls.py", "craftcv/tests.py")

    def test_one_test_covers_several_source_files(self):
        self.assert_allowed(
            "apps/users/models.py",
            "apps/users/views.py",
            "apps/users/tests.py",
        )

    def test_every_test_naming_convention_counts(self):
        for path in (
            "apps/users/tests.py",
            "tests/test_conventions.py",
            "apps/users/tests/test_models.py",
            "apps/users/models_test.py",
        ):
            with self.subTest(path=path):
                self.assert_allowed("apps/users/models.py", path)


class ExemptPathTests(TestsRequiredTestCase):
    def test_generated_and_configuration_paths_need_no_test(self):
        for path in (
            "apps/users/migrations/0001_initial.py",
            "apps/users/__init__.py",
            "apps/users/apps.py",
            "craftcv/settings.py",
            "craftcv/asgi.py",
            "craftcv/wsgi.py",
            "manage.py",
        ):
            with self.subTest(path=path):
                self.assert_allowed(path)

    def test_non_python_changes_need_no_test(self):
        self.assert_allowed("README.md", "requirements.txt", ".githooks/pre-commit")

    def test_nothing_staged_is_allowed(self):
        self.assert_allowed()


class EscapeHatchTests(TestsRequiredTestCase):
    def test_skip_variable_allows_an_untested_change(self):
        result = self.assert_allowed("apps/users/models.py", env={"SKIP_TEST_CHECK": "1"})

        self.assertIn("SKIP_TEST_CHECK=1", result.stdout)


class MessageTests(TestsRequiredTestCase):
    def test_rejection_names_the_files_and_the_way_out(self):
        stderr = self.assert_blocked("apps/users/models.py", "craftcv/urls.py").stderr

        self.assertIn("apps/users/models.py", stderr)
        self.assertIn("craftcv/urls.py", stderr)
        self.assertIn("apps/<app>/tests.py", stderr)
        self.assertIn("SKIP_TEST_CHECK=1", stderr)
        self.assertIn("CONTRIBUTING.md", stderr)

#!/bin/sh

# Canonical quality gate. The Git hooks and GitHub Actions both call this file,
# so local and CI results cannot drift.
#
#   sh scripts/check.sh lint            ruff lint + format check, whole project
#   sh scripts/check.sh lint --staged   the same, on staged Python files only
#   sh scripts/check.sh build           Django system checks + missing migrations
#   sh scripts/check.sh test            Django unit tests
#   sh scripts/check.sh all             everything above
#
# Set PYTHON to choose an interpreter; otherwise a project venv is used when one
# exists, falling back to python3/python on PATH.

set -eu

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

resolve_python() {
  if [ -n "${PYTHON:-}" ]; then
    printf '%s' "$PYTHON"
    return 0
  fi

  for candidate in \
    "$repo_root/venv/Scripts/python.exe" \
    "$repo_root/venv/bin/python" \
    "$repo_root/.venv/Scripts/python.exe" \
    "$repo_root/.venv/bin/python"; do
    if [ -x "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done

  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return 0
    fi
  done

  fail "No Python interpreter found. Create one with 'python -m venv venv' or set PYTHON."
}

python_bin=$(resolve_python)

require_module() {
  "$python_bin" -c "import $1" >/dev/null 2>&1 && return 0

  cat >&2 <<EOF
Missing dependency: $1 is not installed for $python_bin

Install the project dependencies first:

    python -m venv venv
    . venv/Scripts/activate          # Windows: .\\venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt -r requirements-dev.txt

Or point the hooks at another interpreter with PYTHON=/path/to/python.
EOF
  exit 1
}

step() {
  printf '\n[check] %s\n' "$1"
}

run_lint() {
  require_module ruff

  if [ "${1:-}" = "--staged" ]; then
    staged=$(mktemp)
    # ACMR: added, copied, modified, renamed. Deleted files have nothing to lint.
    git diff --cached --name-only --diff-filter=ACMR -z -- '*.py' >"$staged"

    if [ ! -s "$staged" ]; then
      rm -f "$staged"
      step 'lint: no staged Python files, skipping'
      return 0
    fi

    step 'lint: ruff check (staged files)'
    xargs -0 "$python_bin" -m ruff check --force-exclude <"$staged" || {
      rm -f "$staged"
      lint_help
      exit 1
    }

    step 'lint: ruff format --check (staged files)'
    xargs -0 "$python_bin" -m ruff format --check --force-exclude <"$staged" || {
      rm -f "$staged"
      lint_help
      exit 1
    }

    rm -f "$staged"
    return 0
  fi

  step 'lint: ruff check'
  "$python_bin" -m ruff check . || { lint_help; exit 1; }

  step 'lint: ruff format --check'
  "$python_bin" -m ruff format --check . || { lint_help; exit 1; }
}

lint_help() {
  cat >&2 <<EOF

Lint failed. Most of this is fixable automatically:

    python -m ruff check --fix .     apply safe lint fixes
    python -m ruff format .          reformat

Then stage the result and commit again. Rules live in pyproject.toml.
EOF
}

run_build() {
  require_module django

  step 'build: django system checks'
  "$python_bin" manage.py check

  step 'build: no model changes missing a migration'
  "$python_bin" manage.py makemigrations --check --dry-run || {
    cat >&2 <<EOF

A model changed without a matching migration. Generate and commit it:

    python manage.py makemigrations
EOF
    exit 1
  }
}

run_test() {
  require_module django

  step 'test: django unit tests'
  "$python_bin" manage.py test
}

# A change to these needs no test of its own: generated code, packaging stubs,
# and configuration with no behaviour to assert.
test_exempt() {
  case "$1" in
    */migrations/*) return 0 ;;
    manage.py | */__init__.py | */apps.py | */asgi.py | */wsgi.py) return 0 ;;
    craftcv/settings.py) return 0 ;;
  esac
  return 1
}

is_test_file() {
  case "$1" in
    tests/* | */tests/* | tests.py | */tests.py) return 0 ;;
    test_*.py | */test_*.py | *_test.py | */*_test.py) return 0 ;;
  esac
  return 1
}

# Fails when application code is staged without a test alongside it. Pass paths
# to check an explicit list; with no arguments the staged files are used.
run_tests_required() {
  if [ "${SKIP_TEST_CHECK:-0}" = "1" ]; then
    step 'tests-required: skipped by SKIP_TEST_CHECK=1'
    return 0
  fi

  if [ "$#" -eq 0 ]; then
    set -- $(git diff --cached --name-only --diff-filter=ACMR -- '*.py')
  fi

  untested=''
  saw_test=0

  for path in "$@"; do
    case "$path" in *.py) ;; *) continue ;; esac

    if is_test_file "$path"; then
      saw_test=1
      continue
    fi

    test_exempt "$path" && continue

    untested="$untested  $path
"
  done

  if [ -z "$untested" ] || [ "$saw_test" -eq 1 ]; then
    step 'tests-required: ok'
    return 0
  fi

  cat >&2 <<EOF

Application code is staged with no test in the same commit:

$untested
Every behaviour change needs a unit test. Add or update one of:

  apps/<app>/tests.py     tests for that app
  tests/test_*.py         repository-level tests

Then stage it and commit again. Run the suite with:

    sh scripts/check.sh test

If this change genuinely has nothing to assert, say so explicitly:

    SKIP_TEST_CHECK=1 git commit ...

See CONTRIBUTING.md.
EOF
  exit 1
}

[ "$#" -ge 1 ] ||
  fail "Usage: $0 lint [--staged] | tests-required [path...] | build | test | all"

case "$1" in
  lint) shift; run_lint "$@" ;;
  tests-required) shift; run_tests_required "$@" ;;
  build) run_build ;;
  test) run_test ;;
  all) run_lint; run_build; run_test ;;
  *) fail "Unknown check '$1'. Use lint, tests-required, build, test, or all." ;;
esac

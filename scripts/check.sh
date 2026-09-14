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

[ "$#" -ge 1 ] || fail "Usage: $0 lint [--staged] | build | test | all"

case "$1" in
  lint) shift; run_lint "$@" ;;
  build) run_build ;;
  test) run_test ;;
  all) run_lint; run_build; run_test ;;
  *) fail "Unknown check '$1'. Use lint, build, test, or all." ;;
esac

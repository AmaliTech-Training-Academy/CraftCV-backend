#!/bin/sh

set -eu

branch_pattern='^(feat|fix|docs|refactor|test|chore|build|ci|perf|hotfix|release)/[a-z0-9]+(-[a-z0-9]+)*$'
commit_pattern='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9][a-z0-9._/-]*\))?!?: .+$'

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

validate_branch() {
  branch=$1

  case "$branch" in
    main) return 0 ;;
  esac

  printf '%s\n' "$branch" | grep -Eq "$branch_pattern" ||
    fail "Invalid branch '$branch'. Expected <type>/<short-kebab-case-description>. See CONTRIBUTING.md."
}

validate_commit() {
  subject=$1

  # Git-generated subjects are allowed. Pull requests should normally be squash merged.
  case "$subject" in
    "Merge "*|"Revert \""*) return 0 ;;
  esac

  [ "${#subject}" -le 72 ] ||
    fail "Commit subject is longer than 72 characters: $subject"

  printf '%s\n' "$subject" | grep -Eq "$commit_pattern" ||
    fail "Invalid commit subject '$subject'. Use 'type(optional-scope): description'. See CONTRIBUTING.md."
}

[ "$#" -eq 2 ] || fail "Usage: $0 branch <name> | commit <subject>"

case "$1" in
  branch) validate_branch "$2" ;;
  commit) validate_commit "$2" ;;
  *) fail "Unknown validation type '$1'." ;;
esac

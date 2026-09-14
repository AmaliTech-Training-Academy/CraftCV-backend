#!/bin/sh

set -eu

# Issue tracker key that every branch must reference, lowercase as it appears in
# branch names. Change this single value if the project key changes.
ticket_key='crf'

branch_types='feat|fix|docs|refactor|test|chore|build|ci|perf|hotfix|release'
commit_types='feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert'

# Branches that are integrated into rather than created from.
protected_branches='main develop'

branch_pattern="^(${branch_types})/${ticket_key}-[0-9]+(-[a-z0-9]+)+\$"
commit_pattern="^(${commit_types})(\([a-z0-9][a-z0-9._/-]*\))?!?: .+\$"

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

is_protected() {
  for protected in $protected_branches; do
    [ "$1" = "$protected" ] && return 0
  done
  return 1
}

branch_help() {
  cat >&2 <<EOF

Branch names must be:

    <type>/${ticket_key}-<ticket-number>-<short-kebab-case-description>

  ok   feat/${ticket_key}-3-cv-template-export
  ok   fix/${ticket_key}-42-token-expiry
  ok   chore/${ticket_key}-7-bump-django

  bad  feat/cv-template-export        missing ${ticket_key}-<number> ticket reference
  bad  feat/${ticket_key}-3                     missing description
  bad  feat/${ticket_key}3-export               ticket number must follow '${ticket_key}-'
  bad  feat/${ticket_key}-3-CV-Export           uppercase is not allowed
  bad  feature/${ticket_key}-3-export           'feature' is not an allowed type

Allowed types: $(printf '%s' "$branch_types" | tr '|' ' ')

Rename the branch you are on with:

    git branch -m <type>/${ticket_key}-<ticket-number>-<short-description>

See CONTRIBUTING.md.
EOF
}

commit_help() {
  subject_kind=${1:-commit}

  if [ "$subject_kind" = "pr-title" ]; then
    remedy='Rename the pull request on GitHub. GitHub titles a pull request from
the branch name by default, which is never a valid subject.'
  else
    remedy='Amend the last commit with:

    git commit --amend'
  fi

  cat >&2 <<EOF

Subjects must be:

    <type>(optional-scope): <description>          (72 characters max)

  ok   feat(auth): add refresh token rotation
  ok   fix: reject expired reset links
  ok   docs: document local setup
  ok   feat(api)!: drop v1 endpoints                (! marks a breaking change)

  bad  added login                                  missing type
  bad  Feat: add login                              type must be lowercase
  bad  feat add login                               missing colon
  bad  feat:add login                               missing space after colon
  bad  feature: add login                           'feature' is not an allowed type

Allowed types: $(printf '%s' "$commit_types" | tr '|' ' ')

$remedy

See CONTRIBUTING.md.
EOF
}

validate_branch() {
  branch=$1

  is_protected "$branch" && return 0

  printf '%s\n' "$branch" | grep -Eq "$branch_pattern" && return 0

  printf 'Invalid branch name: %s\n' "'$branch'" >&2
  branch_help
  exit 1
}

validate_commit() {
  subject=$1
  kind=${2:-commit}

  if [ "$kind" = "pr-title" ]; then
    label='pull request title'
  else
    label='commit subject'
  fi

  # Git-generated subjects are allowed. Pull requests should normally be squash merged.
  case "$subject" in
    "Merge "*|"Revert \""*) return 0 ;;
  esac

  if [ "${#subject}" -gt 72 ]; then
    printf 'The %s is %s characters, the limit is 72:\n  %s\n' \
      "$label" "${#subject}" "$subject" >&2
    commit_help "$kind"
    exit 1
  fi

  printf '%s\n' "$subject" | grep -Eq "$commit_pattern" && return 0

  printf 'Invalid %s: %s\n' "$label" "'$subject'" >&2
  commit_help "$kind"
  exit 1
}

[ "$#" -ge 2 ] ||
  fail "Usage: $0 branch <name> | commit <subject> [pr-title] | is-protected <name>"

case "$1" in
  branch) validate_branch "$2" ;;
  # The optional third argument tailors the advice: a pull request title is
  # renamed on GitHub, not amended with git.
  commit) validate_commit "$2" "${3:-commit}" ;;
  # Exits 0 when the branch is protected, 1 otherwise. Prints nothing.
  is-protected) is_protected "$2" ;;
  *) fail "Unknown validation type '$1'." ;;
esac

#!/bin/sh

set -eu

repo_root=$(git rev-parse --show-toplevel)
chmod +x "$repo_root/.githooks/pre-commit" "$repo_root/.githooks/commit-msg"
git -C "$repo_root" config core.hooksPath .githooks
printf '%s\n' "Git hooks enabled for $repo_root"

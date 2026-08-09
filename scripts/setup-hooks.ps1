$ErrorActionPreference = 'Stop'

$repoRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) {
    throw 'Run this script from inside the Git repository.'
}

git -C $repoRoot config core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to configure Git hooks.'
}

Write-Host "Git hooks enabled for $repoRoot"

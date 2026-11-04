# Install dula-craft for Claude Code, Codex, Kimi Code and Qoder on Windows. Safe to rerun; rerunning updates.
#   irm https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.ps1 | iex
#   $env:DULA_CRAFT_UNINSTALL='1'; irm .../install.ps1 | iex
# This script runs through iex, so it must never call exit: that would close the person's window.
& {
    $ErrorActionPreference = 'Stop'
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    $userHome = if ($env:DULA_CRAFT_TEST_USERPROFILE) { $env:DULA_CRAFT_TEST_USERPROFILE } else { $env:USERPROFILE }
    $homeDir = if ($env:DULA_CRAFT_HOME) { $env:DULA_CRAFT_HOME } else { Join-Path $userHome '.dula-craft' }
    $repoUrl = if ($env:DULA_CRAFT_REPO) { $env:DULA_CRAFT_REPO } else { 'https://github.com/orange9angel/dula-craft.git' }
    $repoDir = Join-Path $homeDir 'repo'
    # Claude Code reads the first; Codex, Kimi Code and Qoder read the second.
    $targets = @((Join-Path $userHome '.claude\skills'), (Join-Path $userHome '.agents\skills'))

    function Get-LinkTarget($path) {
        $item = Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        if ($item -and $item.LinkType) { return [string]($item.Target | Select-Object -First 1) }
        return $null
    }

    if ($env:DULA_CRAFT_UNINSTALL -eq '1') {
        if (Test-Path (Join-Path $repoDir 'skills')) {
            foreach ($skill in Get-ChildItem (Join-Path $repoDir 'skills') -Directory) {
                foreach ($target in $targets) {
                    $link = Join-Path $target $skill.Name
                    if ((Get-LinkTarget $link) -eq $skill.FullName) { [System.IO.Directory]::Delete($link) }
                }
            }
        }
        foreach ($dir in @($repoDir, (Join-Path $homeDir 'venv'), (Join-Path $homeDir 'config.env'))) {
            if (Test-Path $dir) { Remove-Item -LiteralPath $dir -Recurse -Force -Confirm:$false }
        }
        if ((Test-Path $homeDir) -and -not (Get-ChildItem $homeDir -Force)) { Remove-Item -LiteralPath $homeDir -Force -Confirm:$false }
        Write-Host 'dula-craft is uninstalled.'
        return
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host 'Please install git first: winget install Git.Git'; return }

    # The python3 shim from the Microsoft Store exists even when Python is not installed, so run each.
    $python = $null
    foreach ($candidate in @('python', 'python3', 'py')) {
        if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $candidate -c 'import sys; sys.exit(sys.version_info < (3, 9))' *> $null
        $ok = $LASTEXITCODE -eq 0
        $ErrorActionPreference = $previous
        if ($ok) { $python = $candidate; break }
    }
    if (-not $python) { Write-Host 'Python 3.9 or newer is required: winget install Python.Python.3.12'; return }

    New-Item -ItemType Directory -Force -Path $homeDir | Out-Null
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if (Test-Path (Join-Path $repoDir '.git')) {
        & git -C $repoDir pull --quiet --ff-only
    } else {
        & git clone --quiet --depth 1 $repoUrl $repoDir
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) { Write-Host 'Download failed. Check your connection and try again.'; return }

    foreach ($target in $targets) {
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        foreach ($skill in Get-ChildItem (Join-Path $repoDir 'skills') -Directory) {
            $link = Join-Path $target $skill.Name
            if ((Get-LinkTarget $link) -eq $skill.FullName) { continue }
            if (Get-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue) {
                Write-Host "Skipped ${link}: something else is already there, and it was not overwritten."
                continue
            }
            # A junction needs no administrator rights.
            New-Item -ItemType Junction -Path $link -Target $skill.FullName | Out-Null
        }
    }

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $python (Join-Path $repoDir 'skills\dula-start\scripts\doctor.py') --fix
    $ErrorActionPreference = $previous
    Write-Host ''
    Write-Host 'All set. Restart Claude Code, Codex, Kimi Code or Qoder and say: make me an animated short'
}

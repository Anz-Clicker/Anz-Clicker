param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VersionPath = Join-Path $RepoRoot "src\anz_clicker_qt\version.py"
$ChangelogPath = Join-Path $RepoRoot "docs\CHANGELOG.md"
$BuildScript = Join-Path $PSScriptRoot "build_release.ps1"
$VersionPattern = "^\d+\.\d+\.\d+$"

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Read-CurrentVersion {
    $value = (& python -B -c "import sys; sys.path.insert(0, 'src'); from anz_clicker_qt.version import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $value) {
        throw "Unable to read the current application version."
    }
    return $value
}

function Assert-ReleaseWorkspace {
    $branch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the current Git branch."
    }
    if ($branch -ne "main") {
        throw "Release builds must be created from the main branch. Current branch: $branch"
    }

    $changes = @(& git status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect the Git working tree."
    }
    if ($changes.Count -gt 0) {
        throw "The main branch has uncommitted changes. Commit or discard them before creating a release."
    }
}

function Set-ReleaseVersion {
    param(
        [string]$NewVersion,
        [string]$ReleaseDate
    )

    $versionSource = Get-Content -LiteralPath $VersionPath -Raw
    $updatedVersionSource = [regex]::Replace(
        $versionSource,
        'APP_VERSION\s*=\s*"[^"]+"',
        "APP_VERSION = `"$NewVersion`"",
        1
    )
    if ($updatedVersionSource -eq $versionSource) {
        throw "Unable to update APP_VERSION in '$VersionPath'."
    }

    $changelog = Get-Content -LiteralPath $ChangelogPath -Raw
    $unreleasedPattern = '(?ms)^## Unreleased\s*\r?\n(?<body>.*?)(?=^## |\z)'
    $unreleased = [regex]::Match($changelog, $unreleasedPattern)
    if (-not $unreleased.Success) {
        throw "The changelog does not contain an '## Unreleased' section."
    }
    $releaseNotes = $unreleased.Groups["body"].Value.Trim()
    if (-not $releaseNotes) {
        throw "The changelog's Unreleased section is empty. Add release notes before building."
    }

    $releaseBlock = "## Unreleased`r`n`r`n## $NewVersion - $ReleaseDate`r`n`r`n$releaseNotes`r`n`r`n"
    $updatedChangelog = [regex]::Replace($changelog, $unreleasedPattern, $releaseBlock, 1)

    Write-Utf8NoBom -Path $VersionPath -Content $updatedVersionSource
    Write-Utf8NoBom -Path $ChangelogPath -Content $updatedChangelog
}

Push-Location $RepoRoot
try {
    Assert-ReleaseWorkspace

    $CurrentVersion = Read-CurrentVersion
    if (-not $Version) {
        $Version = (Read-Host "Enter the new release version (current: $CurrentVersion)").Trim()
    } else {
        $Version = $Version.Trim()
    }
    $Version = $Version -replace '^[vV]', ''

    if ($Version -notmatch $VersionPattern) {
        throw "Version must use semantic version format, for example 1.4.0."
    }
    if ([version]$Version -le [version]$CurrentVersion) {
        throw "Version $Version must be newer than the current version $CurrentVersion."
    }

    Write-Output ""
    Write-Output "Preparing Anz Clicker $Version from main..."
    Write-Output "This will update version.py, roll the changelog, run tests, and build the installer."
    $confirmation = (Read-Host "Continue? (Y/N)").Trim()
    if ($confirmation -notin @("Y", "y", "Yes", "yes")) {
        Write-Output "Release creation cancelled."
        exit 0
    }

    $OriginalVersionSource = Get-Content -LiteralPath $VersionPath -Raw
    $OriginalChangelog = Get-Content -LiteralPath $ChangelogPath -Raw
    try {
        Set-ReleaseVersion -NewVersion $Version -ReleaseDate (Get-Date -Format "yyyy-MM-dd")

        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BuildScript
        if ($LASTEXITCODE -ne 0) {
            throw "The release build failed with exit code $LASTEXITCODE."
        }
    }
    catch {
        Write-Utf8NoBom -Path $VersionPath -Content $OriginalVersionSource
        Write-Utf8NoBom -Path $ChangelogPath -Content $OriginalChangelog
        Write-Warning "The version and changelog were restored because release preparation or building failed."
        throw
    }

    $InstallerPath = Join-Path $RepoRoot "release\Anz Clicker Setup v$Version.exe"
    Write-Output ""
    Write-Output "Release build completed successfully."
    Write-Output "Installer: $InstallerPath"
    Write-Output ""
    Write-Output "Next steps:"
    Write-Output "1. Test the installer."
    Write-Output "2. Commit version.py and CHANGELOG.md to main."
    Write-Output "3. Push main to GitHub."
    Write-Output "4. Create a GitHub Release tagged v$Version."
    Write-Output "5. Attach 'Anz Clicker Setup v$Version.exe' to that release."
}
finally {
    Pop-Location
}

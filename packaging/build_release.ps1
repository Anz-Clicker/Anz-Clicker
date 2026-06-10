param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $RepoRoot "build"
$DistRoot = Join-Path $RepoRoot "dist"
$ReleaseRoot = Join-Path $RepoRoot "release"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller-work"
$PyInstallerDist = Join-Path $BuildRoot "pyinstaller-dist"
$SpecPath = Join-Path $PSScriptRoot "Anz Clicker Portable.spec"

Push-Location $RepoRoot
try {
    $Version = (& python -B -c "import sys; sys.path.insert(0, 'src'); from anz_clicker_qt.version import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $Version) {
        throw "Unable to read the application version."
    }

    if (-not $SkipTests) {
        & python "tests\smoke_test.py"
        if ($LASTEXITCODE -ne 0) {
            throw "Smoke tests failed."
        }
    }

    foreach ($path in @($PyInstallerWork, $PyInstallerDist)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }

    & pyinstaller --noconfirm --clean --distpath $PyInstallerDist --workpath $PyInstallerWork $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $BuiltApp = Join-Path $PyInstallerDist "Anz Clicker Portable"
    $ReleaseName = "Anz Clicker v$Version"
    $ReleaseDir = Join-Path $DistRoot $ReleaseName
    $ZipPath = Join-Path $ReleaseRoot "Anz Clicker Portable v$Version.zip"

    if (Test-Path -LiteralPath $ReleaseDir) {
        Remove-Item -LiteralPath $ReleaseDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }

    New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "scripts") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "user-data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "docs") -Force | Out-Null
    New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null

    Copy-Item -LiteralPath (Join-Path $BuiltApp "Anz Clicker.exe") -Destination $ReleaseDir
    Copy-Item -LiteralPath (Join-Path $BuiltApp "_internal") -Destination (Join-Path $ReleaseDir "_internal") -Recurse
    Copy-Item -LiteralPath (Join-Path $RepoRoot "scripts\README.md") -Destination (Join-Path $ReleaseDir "scripts\README.md")
    Copy-Item -LiteralPath (Join-Path $RepoRoot "config\USER_DATA_README.md") -Destination (Join-Path $ReleaseDir "user-data\README.md")
    Copy-Item -LiteralPath (Join-Path $RepoRoot "docs\CHANGELOG.md") -Destination (Join-Path $ReleaseDir "docs\CHANGELOG.md")
    Copy-Item -LiteralPath (Join-Path $RepoRoot "docs\PORTABLE_README.txt") -Destination (Join-Path $ReleaseDir "README.txt")

    $Manifest = [ordered]@{
        product = "Anz Clicker"
        version = $Version
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        executable = "Anz Clicker.exe"
        preserve_on_update = @("scripts", "user-data")
    }
    $Manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $ReleaseDir "release-manifest.json") -Encoding UTF8

    Compress-Archive -LiteralPath $ReleaseDir -DestinationPath $ZipPath -CompressionLevel Optimal
    $Hash = Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256
    $Zip = Get-Item -LiteralPath $ZipPath

    Write-Output ""
    Write-Output "Release folder: $ReleaseDir"
    Write-Output "Release ZIP:    $ZipPath"
    Write-Output "ZIP size:       $([math]::Round($Zip.Length / 1MB, 2)) MB"
    Write-Output "SHA-256:        $($Hash.Hash)"
}
finally {
    Pop-Location
}

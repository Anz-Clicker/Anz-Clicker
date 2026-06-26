param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $RepoRoot "build"
$DistRoot = Join-Path $RepoRoot "dist"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller-work"
$PyInstallerDist = Join-Path $BuildRoot "pyinstaller-dist"
$SpecPath = Join-Path $PSScriptRoot "Anz Clicker.spec"
$InstallerScript = Join-Path $PSScriptRoot "Anz Clicker.iss"

function Assert-AnzClickerIsClosed {
    $running = @(Get-Process -Name "Anz Clicker" -ErrorAction SilentlyContinue)
    if ($running.Count -eq 0) {
        return
    }

    $processIds = ($running | ForEach-Object { $_.Id }) -join ", "
    throw "Anz Clicker is currently running (process ID(s): $processIds). Close every Anz Clicker window, wait a few seconds, and run Create Update.cmd again. Windows cannot replace compiled application files while they are loaded."
}

function Remove-BuildDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $lastError = $null
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return
        }
        catch {
            $lastError = $_
            if ($attempt -lt 5) {
                Write-Warning "Could not clean '$Path' (attempt $attempt of 5). Waiting for file locks to clear..."
                Start-Sleep -Seconds 2
            }
        }
    }

    throw "Could not clean the previous build directory '$Path'. Close Anz Clicker and any File Explorer, antivirus, terminal, or editor process using that folder, then try again. Locked file error: $($lastError.Exception.Message)"
}

Push-Location $RepoRoot
try {
    Assert-AnzClickerIsClosed

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
        Remove-BuildDirectory -Path $path
    }

    & pyinstaller --noconfirm --clean --distpath $PyInstallerDist --workpath $PyInstallerWork $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $BuiltApp = Join-Path $PyInstallerDist "Anz Clicker"
    $StagedApp = Join-Path $DistRoot "Anz Clicker"

    Remove-BuildDirectory -Path $StagedApp
    New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null
    Copy-Item -LiteralPath $BuiltApp -Destination $StagedApp -Recurse
    Write-Output "Staged application: $StagedApp"

    if ($SkipInstaller) {
        Write-Output "Installer compilation skipped."
        return
    }

    $CompilerCandidates = @(
        (Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    $Compiler = $CompilerCandidates | Select-Object -First 1
    if (-not $Compiler) {
        throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php, then rerun this command. The tested application remains staged at '$StagedApp'."
    }

    & $Compiler "/DAppVersion=$Version" "/DSourceDir=$StagedApp" "/DRepoRoot=$RepoRoot" $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed."
    }

    $SetupPath = Join-Path $RepoRoot "release\Anz Clicker Setup v$Version.exe"
    $Hash = Get-FileHash -LiteralPath $SetupPath -Algorithm SHA256
    $Setup = Get-Item -LiteralPath $SetupPath
    Write-Output ""
    Write-Output "Installer: $SetupPath"
    Write-Output "Size:      $([math]::Round($Setup.Length / 1MB, 2)) MB"
    Write-Output "SHA-256:   $($Hash.Hash)"
}
finally {
    Pop-Location
}

# Local experimental build only. Review third-party licenses before distribution.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py)) { throw 'Install the project environment first.' }
# A unique directory avoids deleting or overwriting previous builds/results.
$tag = 'source-build-' + [guid]::NewGuid().ToString('N')
$out = Join-Path $root ('dist\' + $tag)
$work = Join-Path $root ('build\' + $tag)
Push-Location $root
try {
    & $py -m PyInstaller --noconfirm --distpath $out --workpath $work (Join-Path $root 'GSRIM.spec')
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    $package = Join-Path $out 'GSRIM'
    foreach ($name in @('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md')) {
        Copy-Item -LiteralPath (Join-Path $root $name) -Destination $package
    }
    Write-Host "Experimental local build: $package"
    Write-Host 'No external stopping datasets included. Binary redistribution has not been audited.'
} finally {
    Pop-Location
}

# Compatibility entry point; preserves existing portable packages.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'make_deliverable.ps1')

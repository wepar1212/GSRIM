$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'GSRIM Python environment missing.' }
# Do not attach the new GUI to a resident old engine or interrupt its run.
$candidatePorts = @(8765,8766,8767,8768)
foreach ($candidatePort in $candidatePorts) {
    try {
        $reply = Invoke-RestMethod "http://127.0.0.1:$candidatePort/api/info" -TimeoutSec 1
        if ($reply.app -eq 'GSRIM' -and $reply.engine_revision -eq 2 -and $reply.project_root -eq $projectRoot) {
            Start-Process "http://127.0.0.1:$candidatePort"
            exit
        }
    } catch { }
}
$usedPorts = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | ForEach-Object { $_.Port })
$newPort = $candidatePorts | Where-Object { $_ -notin $usedPorts } | Select-Object -First 1
if (-not $newPort) { throw 'GSRIM ports 8765-8768 are occupied; no running service was stopped.' }
Start-Process -FilePath $pythonPath -ArgumentList '-m','gsrim.server','--port',"$newPort" -WorkingDirectory $projectRoot -WindowStyle Hidden

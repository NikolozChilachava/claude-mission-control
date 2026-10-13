# Start Claude Mission Control with Python 3, no extra dependencies.
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 server.py
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python server.py
} else {
    Write-Host 'Python 3 required. Install from python.org and rerun.' -ForegroundColor Red
}

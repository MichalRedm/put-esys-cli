param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$VenvPath = Join-Path $PSScriptRoot "..\..\..\..\.venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not found at $VenvPath. Please run 'python -m venv .venv' in the project root."
    exit 1
}

$MainPath = Join-Path $PSScriptRoot "..\..\..\..\put_esys\main.py"
& $PythonExe $MainPath @Args

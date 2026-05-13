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

& $PythonExe -m put_esys.main @Args

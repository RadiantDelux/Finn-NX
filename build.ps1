param(
    [Parameter(Mandatory = $true)][string]$ApkPath,
    [string]$DevkitPro = 'C:\devkitPro',
    [string]$PythonExe = 'python',
    [string]$DepsDir = (Join-Path $PSScriptRoot '.deps')
)

$ErrorActionPreference = 'Stop'
$bashExe = Join-Path $DevkitPro 'msys2\usr\bin\bash.exe'
if (!(Test-Path -LiteralPath $bashExe)) { throw "MSYS2 bash not found: $bashExe" }
$apk = (Resolve-Path -LiteralPath $ApkPath).Path
$cache = [System.IO.Path]::GetFullPath($DepsDir)

Push-Location $PSScriptRoot
try {
    & $PythonExe -c 'import os,sys; assert os.name == "nt" and sys.version_info >= (3,10), "Use native Windows Python 3.10+ via -PythonExe"'
    if ($LASTEXITCODE) { throw 'Select native Windows Python 3.10+ with -PythonExe.' }
    & $PythonExe tools/build_controls.py --apk $apk
    if ($LASTEXITCODE) { throw 'Managed control helper compilation failed.' }
    & $PythonExe tools/fetch_deps.py --dest $cache
    if ($LASTEXITCODE) { throw 'Dependency preparation failed.' }
    # MSYS2 translates the Windows paths inside the shared shell build.
    $script = Join-Path $PSScriptRoot 'tools\build_switch.sh'
    & $bashExe $script $PSScriptRoot $DevkitPro $cache
    if ($LASTEXITCODE) { throw 'Build or artifact verification failed. See build/*.log.' }
    Write-Host 'Built launcher/finn_nx.nro; artifact verification passed.'
} finally {
    Pop-Location
}

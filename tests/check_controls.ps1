param([switch]$CompileHelper)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $root 'build/control-check'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
& $csc /nologo /target:library /optimize+ "/out:$out\UnityEngine.dll" (Join-Path $PSScriptRoot 'managed\UnityStubs.cs')
if ($LASTEXITCODE) {throw 'Unity boundary compile failed'}
& $csc /nologo /target:library /optimize+ "/out:$out\Assembly-CSharp.dll" "/reference:$out\UnityEngine.dll" (Join-Path $PSScriptRoot 'managed\GameStubs.cs')
if ($LASTEXITCODE) {throw 'Game boundary compile failed'}
if (!$CompileHelper -and (Test-Path -LiteralPath "$root/build/FinnControls.dll")) {
    Copy-Item -LiteralPath "$root/build/FinnControls.dll" -Destination "$out/FinnControls.dll"
} else {
    & $csc /nologo /target:library /optimize+ /langversion:3 "/out:$out\FinnControls.dll" "/reference:$out\UnityEngine.dll" "/reference:$out\Assembly-CSharp.dll" (Join-Path $root 'managed\FinnControls.cs')
    if ($LASTEXITCODE) {throw 'Modeled control helper compile failed'}
}
& $csc /nologo /target:exe "/out:$out\check.exe" "/reference:$out\UnityEngine.dll" "/reference:$out\Assembly-CSharp.dll" "/reference:$out\FinnControls.dll" (Join-Path $PSScriptRoot 'managed\ControlsChecks.cs')
if ($LASTEXITCODE) {throw 'Control scenario compile failed'}
'<configuration><startup useLegacyV2RuntimeActivationPolicy="true"><supportedRuntime version="v4.0"/></startup></configuration>' | Set-Content -LiteralPath "$out/check.exe.config"
& "$out/check.exe"
if ($LASTEXITCODE) {throw 'Control scenarios failed'}

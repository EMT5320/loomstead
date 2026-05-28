param(
    [switch]$DryRun,
    [string]$Input = "",
    [string]$OutputDir = "",
    [string[]]$Formats = @("svg", "png", "pdf")
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mmdc = Join-Path $projectRoot "node_modules\.bin\mmdc.cmd"
if (-not (Test-Path -LiteralPath $mmdc)) {
    throw "Mermaid CLI was not found. Run npm.cmd install first."
}

$diagramDir = Join-Path $projectRoot "paper\diagrams"
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $projectRoot "paper\generated\figures"
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $projectRoot $OutputDir
}

$files = @()
if ([string]::IsNullOrWhiteSpace($Input)) {
    $files = Get-ChildItem -LiteralPath $diagramDir -Filter "*.mmd" | Sort-Object Name
} else {
    $inputPath = $Input
    if (-not [System.IO.Path]::IsPathRooted($inputPath)) {
        $inputPath = Join-Path $projectRoot $inputPath
    }
    $files = @(Get-Item -LiteralPath $inputPath)
}

if ($files.Count -eq 0) {
    throw "No Mermaid diagrams found under $diagramDir."
}

$allowedFormats = @("svg", "pdf", "png")
foreach ($format in $Formats) {
    if ($allowedFormats -notcontains $format) {
        throw "Unsupported Mermaid output format: $format. Allowed values: $($allowedFormats -join ', ')."
    }
}

$browserCandidates = @()
if (-not [string]::IsNullOrWhiteSpace($env:PUPPETEER_EXECUTABLE_PATH)) {
    $browserCandidates += $env:PUPPETEER_EXECUTABLE_PATH
}
if (-not [string]::IsNullOrWhiteSpace($env:CHROME_BIN)) {
    $browserCandidates += $env:CHROME_BIN
}
$browserCandidates += "C:\Program Files\Google\Chrome\Application\chrome.exe"
$browserCandidates += "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
$browserCandidates += "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$browserCandidates += "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
foreach ($commandName in @("chrome", "msedge")) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
        $browserCandidates += $command.Source
    }
}

$browserPath = $null
foreach ($candidate in $browserCandidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        $browserPath = $candidate
        break
    }
}

$puppeteerConfig = $null
if ($browserPath) {
    $runDir = Join-Path $projectRoot ".run\mermaid"
    $puppeteerConfig = Join-Path $runDir "puppeteer-config.json"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $runDir -Force | Out-Null
        $config = [ordered]@{
            executablePath = $browserPath
            args = @("--no-sandbox", "--disable-setuid-sandbox")
        }
        $json = $config | ConvertTo-Json -Depth 4
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($puppeteerConfig, $json, $utf8NoBom)
    }
}

if ($DryRun) {
    Write-Output "MMDC=$mmdc"
    Write-Output "BROWSER=$browserPath"
    Write-Output "OUTPUT_DIR=$OutputDir"
    Write-Output "FORMATS=$($Formats -join ',')"
    foreach ($file in $files) {
        foreach ($format in $Formats) {
            $target = Join-Path $OutputDir "$($file.BaseName).$format"
            Write-Output "RENDER=$($file.FullName) -> $target"
        }
    }
    exit 0
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
foreach ($file in $files) {
    foreach ($format in $Formats) {
        $target = Join-Path $OutputDir "$($file.BaseName).$format"
        $args = @("-i", $file.FullName, "-o", $target, "-b", "transparent")
        if ($format -eq "pdf") {
            $args += "--pdfFit"
        }
        if ($puppeteerConfig) {
            $args = @("-p", $puppeteerConfig) + $args
        }
        & $mmdc @args
        if ($LASTEXITCODE -ne 0) {
            throw "Mermaid render failed for $($file.FullName) with exit code $LASTEXITCODE."
        }
        Write-Output "Rendered $target"
    }
}

param(
    [ValidateRange(1, 10000)][int]$Count = 1000,
    [string]$OutputDirectory = (Join-Path (Split-Path $PSScriptRoot -Parent) '.local/downloads'),
    [ValidateRange(200, 60000)][int]$DelayMs = 200
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
Add-Type -AssemblyName System.Drawing
$datasetPath = [System.IO.Path]::GetFullPath($OutputDirectory)
if ((Test-Path -LiteralPath $datasetPath) -and (Get-ChildItem -LiteralPath $datasetPath -Force | Select-Object -First 1)) {
    throw "Output directory must be empty; existing dataset and labels must not be overwritten: $datasetPath"
}
New-Item -ItemType Directory -Path $datasetPath -Force | Out-Null
$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(30)
$records = [System.Collections.Generic.List[object]]::new()
$hashes = [System.Collections.Generic.HashSet[string]]::new()
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    for ($index = 1; $index -le $Count; $index++) {
        $saved = $false
        for ($attempt = 1; $attempt -le 8; $attempt++) {
            $response = $null
            $stream = $null
            $picture = $null
            try {
                $response = $client.GetAsync('https://ezpost.post.gov.tw/Captcha.ashx').GetAwaiter().GetResult()
                $response.EnsureSuccessStatusCode() | Out-Null
                $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
                $stream = [System.IO.MemoryStream]::new($bytes, $false)
                $picture = [System.Drawing.Image]::FromStream($stream)
                $extension = switch ($picture.RawFormat.Guid.ToString()) {
                    'b96b3caf-0728-11d3-9d7b-0000f81ef32e' { 'png' }
                    'b96b3cae-0728-11d3-9d7b-0000f81ef32e' { 'jpg' }
                    'b96b3cb0-0728-11d3-9d7b-0000f81ef32e' { 'gif' }
                    'b96b3cab-0728-11d3-9d7b-0000f81ef32e' { 'bmp' }
                    default { throw 'Unsupported image format' }
                }
                $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
                if ($hashes.Contains($hash)) { throw 'Duplicate image received' }
                $filename = 'captcha_{0:D4}.{1}' -f $index, $extension
                [System.IO.File]::WriteAllBytes((Join-Path $datasetPath $filename), $bytes)
                $hashes.Add($hash) | Out-Null
                $records.Add([pscustomobject]@{
                    filename = $filename; bytes = $bytes.Length; width = $picture.Width
                    height = $picture.Height; sha256 = $hash; downloaded_at_utc = [DateTime]::UtcNow.ToString('o')
                    source = 'https://ezpost.post.gov.tw/Captcha.ashx'
                })
                $saved = $true
                break
            } catch {
                Write-Output ('Retry image {0}, attempt {1}: {2}' -f $index, $attempt, $_.Exception.Message)
                Start-Sleep -Seconds ([Math]::Min(30, $attempt * 2))
            } finally {
                if ($picture) { $picture.Dispose() }
                if ($stream) { $stream.Dispose() }
                if ($response) { $response.Dispose() }
            }
        }
        if (-not $saved) { throw "Failed to download image $index after 8 attempts" }
        if ($index % 25 -eq 0) {
            $records | Export-Csv -LiteralPath (Join-Path $datasetPath 'manifest.csv') -NoTypeInformation -Encoding UTF8
            Write-Output "Downloaded $index / $Count"
        }
        Start-Sleep -Milliseconds $DelayMs
    }
} finally {
    if ($records.Count -gt 0) { $records | Export-Csv -LiteralPath (Join-Path $datasetPath 'manifest.csv') -NoTypeInformation -Encoding UTF8 }
    $sha.Dispose()
    $client.Dispose()
}
Write-Output "Complete: $($records.Count) unique validated images in $datasetPath"

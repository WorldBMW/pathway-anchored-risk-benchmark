$ErrorActionPreference = 'Stop'
$packageRoot = (Get-ChildItem -LiteralPath 'papers' -Directory | Where-Object { $_.Name -match '_20261016$' -and $_.Name -notmatch '^\d' }).FullName
$renderRoot = Join-Path (Get-Location) '.qa/submission_reaudit_20261016/render'
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$renderer = New-Object -ComObject kwps.Application
$renderer.Visible = $false
$renderer.DisplayAlerts = 0
$renderResults = @()
try {
    foreach ($paperFile in Get-ChildItem -LiteralPath $packageRoot -Recurse -Filter '*.docx') {
        $targetFolder = Join-Path $renderRoot $paperFile.Directory.Name
        New-Item -ItemType Directory -Path $targetFolder -Force | Out-Null
        $pdfPath = Join-Path $targetFolder ($paperFile.BaseName + '.pdf')
        if ((Test-Path -LiteralPath $pdfPath) -and ((Get-Item -LiteralPath $pdfPath).LastWriteTime -gt $paperFile.LastWriteTime)) { continue }
        $paperDoc = $null
        try {
            $paperDoc = $renderer.Documents.Open($paperFile.FullName, $false, $true)
            $paperDoc.ExportAsFixedFormat($pdfPath, 17)
            Write-Output ($paperFile.Directory.Name + ' / ' + $paperFile.BaseName)
            $renderResults += [PSCustomObject]@{file=$paperFile.FullName;pdf=$pdfPath;status='ok'}
        } catch {
            $renderResults += [PSCustomObject]@{file=$paperFile.FullName;status='error';error=$_.Exception.Message}
            Write-Output ('ERROR ' + $paperFile.FullName + ' ' + $_.Exception.Message)
        } finally { if ($paperDoc) { $paperDoc.Close(0) } }
    }
} finally { $renderer.Quit() }
$renderResults | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $renderRoot 'render_log.json')

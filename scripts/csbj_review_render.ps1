$ErrorActionPreference = 'Stop'
$paperFolder = 'G:\project4_cervix_multimodal\papers\13_CSBJ_v2_20261014\CSBJ_submission_checked_20261014'
$renderFolder = 'G:\project4_cervix_multimodal\papers\13_CSBJ_v2_20261014\submission_review\word_render'
New-Item -ItemType Directory -Path $renderFolder -Force | Out-Null
foreach ($paperFile in Get-ChildItem -LiteralPath $paperFolder -Filter '*.docx') {
    $wordRenderer = New-Object -ComObject Word.Application
    $wordRenderer.Visible = $false
    $wordRenderer.DisplayAlerts = 0
    try {
        $renderDoc = $wordRenderer.Documents.Open($paperFile.FullName, $false, $true)
        try {
            $renderDoc.Repaginate()
            $pdfFile = Join-Path $renderFolder ($paperFile.BaseName + '.pdf')
            $renderDoc.ExportAsFixedFormat($pdfFile, 17)
            Write-Output ($paperFile.BaseName + ': ' + $renderDoc.ComputeStatistics(2) + ' pages')
        } finally { try { $renderDoc.Close(0) } catch {} }
    } catch { Write-Output ($paperFile.BaseName + ': render error ' + $_.Exception.Message) }
    finally {
        try { $wordRenderer.Quit() } catch {}
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($wordRenderer) | Out-Null
    }
}

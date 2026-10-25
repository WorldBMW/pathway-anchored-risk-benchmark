$ErrorActionPreference='Stop'
$qaRoot=Join-Path (Get-Location) 'papers/08_JBI/_qa_20260924/render'
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$qaWps=New-Object -ComObject kwps.Application
$qaWps.Visible=$false
$qaWps.DisplayAlerts=0
try {
 foreach($qaFile in Get-ChildItem -LiteralPath 'papers/08_JBI' -Filter '*.docx') {
  $qaDoc=$qaWps.Documents.Open($qaFile.FullName,$false,$true)
  $qaPdf=Join-Path $qaRoot ($qaFile.BaseName+'.pdf')
  $qaDoc.ExportAsFixedFormat($qaPdf,17)
  $qaDoc.Close(0)
  Write-Output $qaPdf
 }
} finally { $qaWps.Quit() }

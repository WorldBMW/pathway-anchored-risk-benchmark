$ErrorActionPreference = 'Stop'
$taskRoot='G:\project4_cervix_multimodal'
$taskFiles=@('Manuscript_Patterns','TitlePage_Patterns','CoverLetter_Patterns','Supplemental_Information_Patterns')
foreach($taskFile in $taskFiles) {
  $taskWord=$null
  try {
    $taskWord=New-Object -ComObject Word.Application
    $taskWord.Visible=$false
    $taskWord.DisplayAlerts=0
    $taskDoc=$taskWord.Documents.Open(($taskRoot+'\papers\20_MRP-ST-Repair_Patterns\'+$taskFile+'.docx'),$false,$true)
    $taskDoc.ExportAsFixedFormat(($taskRoot+'\.qa\patterns_v27_render\'+$taskFile+'.pdf'),17)
    Write-Output ('RENDERED '+$taskFile)
  } catch {Write-Output ('ERROR '+$taskFile+' '+$_.Exception.Message)}
  finally {if($taskWord){try {$taskWord.Quit(0)} catch {}}}
}

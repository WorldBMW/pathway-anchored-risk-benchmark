$ErrorActionPreference='Stop'
$taskRoot='G:\project4_cervix_multimodal'
$taskOut=$taskRoot+'\.qa\patterns_v29\render'
New-Item -ItemType Directory -Path $taskOut -Force | Out-Null
foreach($taskName in @('Manuscript','Supplemental_Information','CoverLetter','TitlePage')) {
 $taskApp=$null;$taskOwned=$false;$taskDoc=$null
 try {
  $taskApp=New-Object -ComObject Word.Application
  $taskOwned=($taskApp.Documents.Count -eq 0)
  if($taskOwned){$taskApp.Visible=$false;$taskApp.DisplayAlerts=0}
  $taskFile=$taskName+'_Patterns_v29'
  $taskDoc=$taskApp.Documents.Open(($taskRoot+'\papers\20_MRP-ST-Repair_Patterns\'+$taskFile+'.docx'),$false,$true)
  $taskDoc.ExportAsFixedFormat(($taskOut+'\'+$taskFile+'.pdf'),17)
  Write-Output ('RENDERED '+$taskFile)
 } catch {Write-Output ('ERROR '+$taskName+' '+$_.Exception.Message)}
 finally {if($taskDoc){try{$taskDoc.Close(0)}catch{}};if($taskOwned -and $taskApp){try{$taskApp.Quit(0)}catch{}}}
}

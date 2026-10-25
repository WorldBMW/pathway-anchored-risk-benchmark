$ErrorActionPreference = 'Stop'
$packageRoot = 'G:\project4_cervix_multimodal\papers\12_CSBJ_audit_20261010'
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Fix-ReferenceText([string]$value) {
    $value = $value.Replace('[16] . Integrated genomic', '[16] The Cancer Genome Atlas Research Network. Integrated genomic')
    $value = $value.Replace('2010;9:.', '2010;9:Article39.')
    return $value
}
foreach ($name in @('Manuscript_CSBJ.md','Manuscript_CSBJ_resolved.md','References_verified.txt')) {
    $path = Join-Path $packageRoot $name
    $content = [System.IO.File]::ReadAllText($path)
    [System.IO.File]::WriteAllText($path, (Fix-ReferenceText $content), $utf8)
}
$bibPath = Join-Path $packageRoot 'References.bib'
$bib = [System.IO.File]::ReadAllText($bibPath)
$bib = $bib.Replace('author = {}', 'author = {{The Cancer Genome Atlas Research Network}}')
[System.IO.File]::WriteAllText($bibPath,$bib,$utf8)
$metaPath = Join-Path $packageRoot 'evidence\references_verified.json'
$meta = Get-Content -LiteralPath $metaPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $meta.PSObject.Properties) {
    if ($property.Value.doi -eq '10.1038/nature21386') { $property.Value.authors = @('The Cancer Genome Atlas Research Network') }
    if ($property.Value.doi -eq '10.2202/1544-6115.1585') { $property.Value.page = 'Article39' }
}
[System.IO.File]::WriteAllText($metaPath,($meta | ConvertTo-Json -Depth 30),$utf8)
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$docPath = Join-Path $packageRoot 'Manuscript_CSBJ.docx'
$archive = [System.IO.Compression.ZipFile]::Open($docPath,[System.IO.Compression.ZipArchiveMode]::Update)
try {
    $entry = $archive.GetEntry('word/document.xml')
    $reader = New-Object System.IO.StreamReader($entry.Open())
    $xml = $reader.ReadToEnd(); $reader.Dispose()
    $xml = Fix-ReferenceText $xml
    $entry.Delete()
    $entry = $archive.CreateEntry('word/document.xml')
    $writer = New-Object System.IO.StreamWriter($entry.Open(),$utf8)
    $writer.Write($xml); $writer.Dispose()
} finally { $archive.Dispose() }
$readmePath = Join-Path $packageRoot 'README_投稿说明.md'
$addition = "`n## 本次最终核对补充`n请先阅读 CSBJ_方向与投稿要求_20261010.md，填写 Submission_Metadata_to_Complete.tsv。补正参考文献 TCGA 团体作者及 Phipson Article39。投稿信仍需全体作者邮箱、ORCID及作者确认后的正式独家投稿/出版伦理声明；推荐审稿人联系方式待填写。官方签字表单从现行官网获取，不以本地作者确认文件替代。`n"
[System.IO.File]::AppendAllText($readmePath,$addition,$utf8)
Write-Output 'Reference omissions corrected; submission requirements and missing metadata recorded.'

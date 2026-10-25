$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$contactRoot = 'G:\project4_cervix_multimodal\papers\12_CSBJ_audit_20261010'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$contacts = 'Author e-mail addresses: Mingwei Bai: baimingwei@jm360.cn; Zhengmin Gu: guzm@cmu1h.com; Ye Zhang: 13332457636@163.com; Lang Guo (corresponding author): guolang1016@symc.edu.cn.'
$correspondence = 'Corresponding author: Lang Guo, School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China. Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn.'
foreach ($name in @('Manuscript_CSBJ.docx','Title_Page_CSBJ.docx','Cover_Letter_CSBJ.docx')) {
    $path = Join-Path $contactRoot $name
    $zip = [System.IO.Compression.ZipFile]::Open($path,[System.IO.Compression.ZipArchiveMode]::Update)
    try {
        $entry = $zip.GetEntry('word/document.xml')
        $reader = New-Object System.IO.StreamReader($entry.Open())
        [xml]$xml = $reader.ReadToEnd(); $reader.Dispose()
        $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
        $ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
        $paragraphs = $xml.SelectNodes('//w:body/w:p',$ns)
        $existing = ($xml.SelectNodes('//w:t',$ns) | ForEach-Object {$_.InnerText}) -join ' '
        if ($existing -notmatch 'baimingwei@jm360.cn') {
            $anchor = $null
            foreach ($p in $paragraphs) {
                $text = ($p.SelectNodes('.//w:t',$ns) | ForEach-Object {$_.InnerText}) -join ''
                if (($name -eq 'Manuscript_CSBJ.docx' -and $text -match 'Correspondence:') -or ($name -eq 'Title_Page_CSBJ.docx' -and $text -match 'Corresponding author:') -or ($name -eq 'Cover_Letter_CSBJ.docx' -and $text -match '^Sincerely,')) { $anchor = $p; break }
            }
            if ($null -eq $anchor) { throw "Contact insertion anchor missing: $name" }
            $new = $xml.CreateElement('w','p',$ns.LookupNamespace('w'))
            $props = $anchor.SelectSingleNode('./w:pPr',$ns)
            if ($props) { [void]$new.AppendChild($props.CloneNode($true)) }
            $run = $xml.CreateElement('w','r',$ns.LookupNamespace('w'))
            $runProps = $anchor.SelectSingleNode('./w:r/w:rPr',$ns)
            if ($runProps) { [void]$run.AppendChild($runProps.CloneNode($true)) }
            $t = $xml.CreateElement('w','t',$ns.LookupNamespace('w')); $t.InnerText = $contacts
            [void]$run.AppendChild($t); [void]$new.AppendChild($run)
            if ($name -eq 'Cover_Letter_CSBJ.docx') { [void]$anchor.ParentNode.InsertBefore($new,$anchor) }
            else { [void]$anchor.ParentNode.InsertAfter($new,$anchor) }
        }
        if ($name -eq 'Manuscript_CSBJ.docx') {
            foreach ($p in $xml.SelectNodes('//w:body/w:p',$ns)) {
                $texts = $p.SelectNodes('.//w:t',$ns)
                $text = ($texts | ForEach-Object {$_.InnerText}) -join ''
                if ($text -match 'Correspondence:') { $texts[0].InnerText = '* '+$correspondence; for ($i=1;$i -lt $texts.Count;$i++) {$texts[$i].InnerText=''} }
            }
        }
        $entry.Delete(); $entry = $zip.CreateEntry('word/document.xml')
        $writer = New-Object System.IO.StreamWriter($entry.Open(),$utf8); $writer.Write($xml.OuterXml); $writer.Dispose()
    } finally { $zip.Dispose() }
}
foreach ($name in @('Manuscript_CSBJ.md','Manuscript_CSBJ_resolved.md')) {
    $path = Join-Path $contactRoot $name; $text = [System.IO.File]::ReadAllText($path)
    if ($text -notmatch 'baimingwei@jm360.cn') { $text = $text.Replace('* Correspondence: guolang1016@symc.edu.cn',('* '+$correspondence+"`n`n"+$contacts)) }
    [System.IO.File]::WriteAllText($path,$text,$utf8)
}
$metadataPath = Join-Path $contactRoot 'Submission_Metadata_to_Complete.tsv'
$rows = Import-Csv -LiteralPath $metadataPath -Delimiter "`t" -Encoding UTF8
foreach ($row in $rows) {
    switch ($row.name) {
        'Mingwei Bai' { $row.email = 'baimingwei@jm360.cn' }
        'Zhengmin Gu' { $row.email = 'guzm@cmu1h.com' }
        'Ye Zhang' { $row.email = '13332457636@163.com' }
    }
}
$rows | Export-Csv -LiteralPath $metadataPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8
$strategyPath = Join-Path $contactRoot 'CSBJ_方向与投稿要求_20261010.md'
$text = [System.IO.File]::ReadAllText($strategyPath)
$text = $text.Replace('需补所有作者邮箱、ORCID和正式独家投稿声明','全体作者邮箱已补；ORCID和正式独家投稿声明待补')
$text = $text.Replace('现有投稿信保留“待确认”说明','全体作者邮箱已从历史稿件补入。现有投稿信保留“待确认”说明')
$text = $text.Replace('填写全体作者邮箱与 ORCID','作者邮箱已补入；填写全体作者 ORCID')
[System.IO.File]::WriteAllText($strategyPath,$text,$utf8)
$readmePath = Join-Path $contactRoot 'README_投稿说明.md'
$text = [System.IO.File]::ReadAllText($readmePath).Replace('投稿信仍需全体作者邮箱、ORCID及作者确认后的正式独家投稿/出版伦理声明','投稿信已补全体作者邮箱，仍需 ORCID 及作者确认后的正式独家投稿/出版伦理声明')
[System.IO.File]::WriteAllText($readmePath,$text,$utf8)
$provenance = @'
# 作者联系资料核对记录

2026-10-10：核对 papers/10_PLOSCB/Manuscript_PLOSCB.docx、papers/11_CBM/Title_Page_CBM.docx 和 papers/11_CiBM/Title_Page_CiBM.docx，作者联系方式一致。

|作者|邮箱|
|---|---|
|Mingwei Bai|baimingwei@jm360.cn|
|Zhengmin Gu|guzm@cmu1h.com|
|Ye Zhang|13332457636@163.com|
|Lang Guo，通讯作者|guolang1016@symc.edu.cn|

通讯地址：School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China。电话：+86 13555707001。

已同步主稿 DOCX/Markdown、标题页、投稿信、作者元数据表及全套 ZIP。未在历史稿件中检出实际 ORCID；早期文件只有占位符。ORCID 仍需作者补充。此次补入联系方式不代替作者对独家投稿、贡献和出版伦理的确认。

当前机器缺少 LibreOffice；新增联系段落保留原有正文样式，但修改后 Word 逐页视觉 QA 尚未完成。
'@
[System.IO.File]::WriteAllText((Join-Path $contactRoot 'Author_Contact_Provenance.md'),$provenance,$utf8)
$deliveryPath = Join-Path $contactRoot 'CSBJ_Submission_Package_20261010.zip'
$delivery = [System.IO.Compression.ZipFile]::Open($deliveryPath,[System.IO.Compression.ZipArchiveMode]::Update)
try {
    foreach ($file in (Get-ChildItem -LiteralPath $contactRoot -File | Where-Object {$_.Extension -in @('.docx','.md','.bib','.txt','.tsv')})) {
        $old = $delivery.GetEntry($file.Name); if ($old) {$old.Delete()}
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($delivery,$file.FullName,$file.Name,[System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally {$delivery.Dispose()}
Write-Output 'Restored all four author emails and corresponding-author details; updated submission ZIP. ORCID not found in historical manuscripts.'

import zipfile, re
path = r"F:/project4_cervix_multimodal/papers/07_CSBJ_v10/Manuscript_v10_中文.docx"
z = zipfile.ZipFile(path)
xml = z.read("word/document.xml").decode("utf-8")
paras = re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", xml, re.S)
out = []
for p in paras:
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
    line = "".join(texts)
    line = line.replace("&lt;","<").replace("&gt;",">").replace("&amp;","&")
    out.append(line)
text = "\n".join(out)
with open(r"F:/project4_cervix_multimodal/papers/07_CSBJ_v10/_v10_zh_extracted.txt","w",encoding="utf-8") as f:
    f.write(text)
print("paras:", len(out))
print("chars:", len(text))

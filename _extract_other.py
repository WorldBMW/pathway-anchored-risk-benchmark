import zipfile, re
for name in ["Manuscript_v10_English.docx","CoverLetter_v10.docx","Highlights_v10.docx"]:
    path = rf"F:/project4_cervix_multimodal/papers/07_CSBJ_v10/{name}"
    z = zipfile.ZipFile(path)
    xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", xml, re.S)
    out=[]
    for p in paras:
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
        out.append("".join(texts).replace("&lt;","<").replace("&gt;",">").replace("&amp;","&"))
    text="\n".join(out)
    with open(rf"F:/project4_cervix_multimodal/papers/07_CSBJ_v10/_{name}.txt","w",encoding="utf-8") as f:
        f.write(text)
    print(name, len(out), "paras,", len(text), "chars")

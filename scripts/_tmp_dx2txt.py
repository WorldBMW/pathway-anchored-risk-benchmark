import zipfile, re, sys


def dx2txt(p):
    z = zipfile.ZipFile(p)
    xml = z.read('word/document.xml').decode('utf-8')
    parts = []
    # split by paragraph
    for para in re.findall(r'<w:p\b.*?</w:p>', xml, re.S):
        buf = []
        for m in re.finditer(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', para, re.S):
            buf.append(m.group(1))
        line = ''.join(buf)
        parts.append(line)
    return '\n'.join(parts)


for p in sys.argv[1:]:
    print('===== FILE:', p)
    print(dx2txt(p))

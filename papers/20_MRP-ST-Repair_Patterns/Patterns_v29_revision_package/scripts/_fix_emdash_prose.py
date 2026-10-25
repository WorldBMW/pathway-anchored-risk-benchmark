"""Replace prose em-dashes with commas, colons or parentheses (AI-tell cleanup)."""
import io, re, difflib

P = 'MRP-ST-Repair_manuscript_Patterns_v5.md'
lines = io.open(P, encoding='utf-8').read().split('\n')


def process(line):
    if line.lstrip().startswith('|') or '—' not in line:
        return line
    idxs = [m.start() for m in re.finditer('—', line)]
    n = len(idxs)
    dec = [None] * n
    i = 0
    while i < n:
        paired = False
        if i + 1 < n:
            between = line[idxs[i] + 1:idxs[i + 1]]
            before_char = line[idxs[i] - 1] if idxs[i] > 0 else ''
            after_char = line[idxs[i + 1] + 1] if idxs[i + 1] + 1 < len(line) else ''
            if ('.' not in between and ';' not in between and len(between) < 240
                    and before_char != '(' and after_char != ')'):
                dec[i] = ' ('
                dec[i + 1] = ') '
                i += 2
                paired = True
        if not paired:
            nxt = line[idxs[i] + 1:].lstrip().lower()
            if nxt.startswith(('and ', 'or ', 'but ', 'nor ', 'yet ', 'so ')):
                dec[i] = ', '
            elif ':' in nxt[:25]:
                dec[i] = '; '
            else:
                dec[i] = ': '
            i += 1
    out, prev = [], 0
    for k, pos in enumerate(idxs):
        out.append(line[prev:pos])
        out.append(dec[k])
        prev = pos + 1
    out.append(line[prev:])
    s = ''.join(out)
    s = re.sub(r'\s+([,;:)])', r'\1', s)
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'  +', ' ', s)
    return s


new = [process(l) for l in lines]
changed = [(i + 1, lines[i], new[i]) for i in range(len(lines)) if lines[i] != new[i]]
io.open(P, 'w', encoding='utf-8').write('\n'.join(new))
print('lines changed:', len(changed))
for ln, a, b in changed:
    if len(a) < 300:
        print('--- L%d' % ln)
        print('OLD:', a)
        print('NEW:', b)
remaining = sum(l.count('—') for l in new if not l.lstrip().startswith('|'))
print('em-dashes remaining outside tables:', remaining)

#!/usr/bin/env python3
"""Render the generated v5_results.md as a self-contained HTML page next to it.

The markdown stays the source of truth; this page only restyles it. Tables gain in-cell bars
(accuracy, conformability, ΔAcc, task progress), status chips and collapsible reference sections.
"""
from pathlib import Path
from urllib.parse import quote
import argparse, html, os, re

COLLAPSED_SECTIONS = {'Dataset-specific metric definitions', 'Sources and refresh'}
SHOWN_PREAMBLE = ('Run states', 'Conformability judge')
NUMBER = re.compile(r'^([+-]?\d+(?:\.\d+)?)(?:\s*±\s*(\d+(?:\.\d+)?))?$')
FRACTION = re.compile(r'^([\d,]+)\s*/\s*([\d,]+)$')
INLINE = re.compile(r'\[([^\]]+)\]\(<([^>]+)>\)|\[([^\]]+)\]\(([^)\s]+)\)|`([^`]+)`|\*\*(.+?)\*\*')


def href(target, base):
    if target.startswith('/'):
        try: target = os.path.relpath(target, base)
        except ValueError: return 'file://' + quote(target)
    return quote(target, safe='/#:?=&.-_~')


def inline(text, base):
    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(html.escape(text[pos:m.start()])); pos = m.end()
        if m.group(1) or m.group(3):
            label, target = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            out.append(f'<a href="{href(target, base)}">{inline(label, base)}</a>')
        elif m.group(5) is not None: out.append(f'<code>{html.escape(m.group(5))}</code>')
        else: out.append(f'<strong>{inline(m.group(6), base)}</strong>')
    out.append(html.escape(text[pos:]))
    return ''.join(out)


def blocks(lines):
    """Split markdown into (kind, payload) blocks: h1/h2/h3, table, list, para."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line: i += 1; continue
        heading = re.match(r'^(#{1,3}) (.*)$', line)
        if heading: out.append((f'h{len(heading.group(1))}', heading.group(2))); i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')]); i += 1
            out.append(('table', rows)); continue
        if line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '): items.append(lines[i][2:].strip()); i += 1
            out.append(('list', items)); continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,3} |\||- )', lines[i]):
            para.append(lines[i].strip()); i += 1
        out.append(('para', ' '.join(para)))
    return out


def plain(cell): return re.sub(r'\*\*|`', '', cell).strip()


def status_chip(value):
    low = value.lower()
    if 'invalid' in low: kind, icon = 'warn', '!'
    elif 'running' in low: kind, icon = 'run', '●'
    elif 'pending' in low or 'held' in low: kind, icon = 'wait', '○'
    elif 'fail' in low: kind, icon = 'bad', '×'
    elif 'complete' in low: kind, icon = 'ok', '✓'
    else: return None
    return f'<span class="chip {kind}"><span class="ico" aria-hidden="true">{icon}</span>{html.escape(value)}</span>'


def table(rows, base, context):
    head, body = rows[0], rows[2:] if len(rows) > 1 and set(''.join(rows[1])) <= set('-: ') else rows[1:]
    aligns = []
    if len(rows) > 1 and set(''.join(rows[1])) <= set('-: '):
        aligns = ['right' if c.endswith(':') and not c.startswith(':') else 'center' if c.startswith(':') and c.endswith(':') else 'left' for c in rows[1]]
    names = [plain(h) for h in head]
    bar_cols = {j for j, n in enumerate(names) if n in ('Acc %', 'Conformability %', 'Conf %')}
    delta_cols = {j for j, n in enumerate(names) if n.startswith('ΔAcc')}
    frac_cols = {j for j, n in enumerate(names) if n in ('Tasks started', 'Pred', 'Judged')}
    status_cols = {j for j, n in enumerate(names) if n == 'Status'}
    method_col = next((j for j, n in enumerate(names) if n in ('Method', 'Phase / method', 'Job')), None)
    scale = {}
    for j in bar_cols:
        vals = [float(m.group(1)) for r in body if j < len(r) and (m := NUMBER.match(plain(r[j])))]
        scale[j] = max(vals) * 1.08 if vals and max(vals) < 60 else 100
    dmax = max([abs(float(m.group(1))) for j in delta_cols for r in body if j < len(r) and (m := NUMBER.match(plain(r[j])))] or [1]) or 1
    best = {}
    for j in bar_cols:
        vals = [float(m.group(1)) for r in body if j < len(r) and (m := NUMBER.match(plain(r[j])))]
        if len(vals) > 1: best[j] = max(vals)
    out = [f'<div class="tablewrap"><table class="{context}"><thead><tr>']
    for j, h in enumerate(head):
        out.append(f'<th class="{aligns[j] if j < len(aligns) else "left"}">{inline(plain(h), base)}</th>')
    out.append('</tr></thead><tbody>')
    for r in body:
        is_ace = method_col is not None and method_col < len(r) and 'ACE' in plain(r[method_col]) and context != 'paper'
        out.append(f'<tr class="{"ace" if is_ace else ""}">')
        for j, cell in enumerate(r):
            align = aligns[j] if j < len(aligns) else 'left'; value = plain(cell)
            m, f = NUMBER.match(value), FRACTION.match(value)
            if j in bar_cols and m:
                mean = float(m.group(1)); sd = float(m.group(2)) if m.group(2) else None; s = scale[j]
                whisker = (f'<span class="whisker" style="left:{max(mean-sd,0)/s*100:.2f}%;width:{(min(mean+sd,s)-max(mean-sd,0))/s*100:.2f}%"></span>'
                           if sd is not None else '')
                top = ' best' if j in best and mean == best[j] else ''
                out.append(f'<td class="bar{top}"><div class="val">{html.escape(value)}</div>'
                           f'<div class="track"><span class="fill" style="width:{mean/s*100:.2f}%"></span>{whisker}</div></td>')
            elif j in delta_cols and m:
                d = float(m.group(1)); w = abs(d)/dmax*50
                side = f'left:50%;width:{w:.2f}%' if d >= 0 else f'left:{50-w:.2f}%;width:{w:.2f}%'
                out.append(f'<td class="delta"><div class="val">{html.escape(value)}</div>'
                           f'<div class="track dtrack"><span class="mid"></span><span class="dfill {"pos" if d > 0 else "neg" if d < 0 else ""}" style="{side}"></span></div></td>')
            elif j in frac_cols and f:
                a, b = (int(x.replace(',', '')) for x in f.groups())
                out.append(f'<td class="frac"><div class="val">{html.escape(value)}</div>'
                           f'<div class="track thin"><span class="fill neutral" style="width:{min(a/b, 1)*100 if b else 0:.2f}%"></span></div></td>')
            elif j in status_cols and (chip := status_chip(value)):
                out.append(f'<td class="left">{chip}</td>')
            else:
                out.append(f'<td class="{align}">{inline(cell, base)}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def tiles(rows, base):
    out = ['<div class="tiles">']
    for r in rows[2:]:
        label, value = plain(r[0]), plain(r[1]); f = FRACTION.match(value)
        if f:
            a, b = (int(x.replace(',', '')) for x in f.groups()); pct = a/b*100 if b else 0
            done = ' done' if a == b else ''
            out.append(f'<div class="tile{done}"><div class="tlabel">{html.escape(label)}</div>'
                       f'<div class="tvalue">{a:,}<span class="tof"> / {b:,}</span></div>'
                       f'<div class="track"><span class="fill neutral" style="width:{pct:.2f}%"></span></div>'
                       f'<div class="tpct">{pct:.1f}%</div></div>')
        else:
            out.append(f'<div class="tile"><div class="tlabel">{html.escape(label)}</div><div class="tvalue">{html.escape(value)}</div></div>')
    out.append('</div>')
    return ''.join(out)


def slug(text): return re.sub(r'[^a-z0-9]+', '-', plain(text).lower()).strip('-')


def render(md, base):
    bl = blocks(md.splitlines())
    title = next((p for k, p in bl if k == 'h1'), 'Results')
    generated = next((re.search(r'\*\*(.+?)\*\*', p).group(1) for k, p in bl if k == 'para' and p.startswith('Report generated')), '')
    sections, current = [], None
    for kind, payload in bl:
        if kind == 'h1': continue
        if kind == 'h2': current = dict(title=payload, blocks=[]); sections.append(current); continue
        if current is None: current = dict(title='', blocks=[]); sections.append(current)
        current['blocks'].append((kind, payload))
    nav, body = [], []
    for sec in sections:
        name, sid = sec['title'], slug(sec['title']) or 'overview'
        if name: nav.append(f'<a href="#{sid}">{html.escape(name.split(" · ")[0])}</a>')
        parts, sub, subparts = [], None, []

        def flush():
            nonlocal sub, subparts
            if sub is None: parts.extend(subparts)
            else:
                seed = sub.endswith('seed detail')
                inner = f'<h3 id="{slug(sub)}">{inline(sub, base)}</h3>' + ''.join(subparts)
                parts.append(f'<details class="sub" id="{slug(sub)}"><summary>{inline(sub, base)}</summary>{"".join(subparts)}</details>'
                             if seed else f'<div class="subsec">{inner}</div>')
            sub, subparts = None, []

        hidden = []
        first_table = True
        for kind, payload in sec['blocks']:
            if kind == 'h3': flush(); sub = payload; continue
            if kind == 'table':
                if not name and first_table: subparts.append(tiles(payload, base)); first_table = False; continue
                context = 'paper' if 'Paper reference' in ''.join(parts[-1:] + subparts[-1:]) else 'data'
                subparts.append(table(payload, base, context)); continue
            if kind == 'list':
                subparts.append('<ul>' + ''.join(f'<li>{inline(x, base)}</li>' for x in payload) + '</ul>'); continue
            if not name:
                if payload.startswith(('Report generated', '**Qwen3')): continue
                if payload.startswith(tuple('**' + s for s in SHOWN_PREAMBLE)):
                    subparts.append(f'<p class="note">{inline(payload, base)}</p>')
                else: hidden.append(f'<p>{inline(payload, base)}</p>')
                continue
            cls = ' class="ref"' if payload.startswith('**Paper reference') else ''
            subparts.append(f'<p{cls}>{inline(payload, base)}</p>')
        flush()
        if hidden: parts.append(f'<details class="sub"><summary>Protocol and revision notes ({len(hidden)})</summary>{"".join(hidden)}</details>')
        content = ''.join(parts)
        if not name: body.append(f'<section id="overview">{content}</section>')
        elif name in COLLAPSED_SECTIONS:
            body.append(f'<section id="{sid}"><details class="top"><summary><h2>{inline(name, base)}</h2></summary>{content}</details></section>')
        else: body.append(f'<section id="{sid}"><h2>{inline(name, base)}</h2>{content}</section>')
    subtitle = next((p for k, p in bl if k == 'para' and p.startswith('**Qwen3')), '')
    return PAGE.format(title=html.escape(title), subtitle=inline(subtitle, base), generated=html.escape(generated),
                       nav=''.join(nav), body=''.join(body))


PAGE = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>{title}</title>
<style>
:root{{--bg:#f6f7f8;--surface:#fff;--ink:#1b2a33;--muted:#5c6b73;--line:#dde3e6;--tint:#f1f4f6;--ace:#fbeaed;
--accent:#d1495b;--slate:#7d8f98;--neutral:#4f7c8a;--pos:#2f6fa8;--neg:#c8702a;--ok:#2e7d4f;--warn:#b26b00;--run:#2f6fa8;--bad:#b3261e;
--code:#eef1f3;--link:#1f5f8b;--acetrack:rgba(255,255,255,.6)}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#12181c;--surface:#1a2227;--ink:#e4eaee;--muted:#9aa9b1;--line:#2c373e;
--tint:#202a30;--ace:#3a2327;--accent:#e2677a;--slate:#8fa2ab;--neutral:#6fa3b3;--pos:#6fa6db;--neg:#e0955a;--ok:#5fb884;--warn:#e0a54a;
--run:#6fa6db;--bad:#e36b62;--code:#243037;--link:#7fb8e0;--acetrack:rgba(0,0,0,.28)}}}}
:root[data-theme="dark"]{{--bg:#12181c;--surface:#1a2227;--ink:#e4eaee;--muted:#9aa9b1;--line:#2c373e;--tint:#202a30;--ace:#3a2327;
--accent:#e2677a;--slate:#8fa2ab;--neutral:#6fa3b3;--pos:#6fa6db;--neg:#e0955a;--ok:#5fb884;--warn:#e0a54a;--run:#6fa6db;--bad:#e36b62;
--code:#243037;--link:#7fb8e0;--acetrack:rgba(0,0,0,.28)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo",sans-serif}}
header{{background:var(--surface);border-bottom:1px solid var(--line);padding:28px 32px 18px}}
h1{{margin:0 0 4px;font:700 28px/1.2 Cambria,Georgia,serif;letter-spacing:-.01em}}
.subtitle{{color:var(--muted);margin:0}}
.stamp{{color:var(--muted);font-size:12.5px;margin-top:8px}}
nav{{position:sticky;top:0;z-index:5;background:var(--surface);border-bottom:1px solid var(--line);padding:8px 32px;display:flex;gap:6px;flex-wrap:wrap}}
nav a{{color:var(--ink);text-decoration:none;padding:4px 10px;border-radius:999px;background:var(--tint);font-size:13px}}
nav a:hover{{background:var(--line)}}
main{{max-width:1320px;margin:0 auto;padding:8px 32px 60px}}
section{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px 24px;margin:20px 0;scroll-margin-top:56px}}
h2{{font:700 21px/1.3 Cambria,Georgia,serif;margin:0 0 12px;display:inline}}
section>h2{{display:block}}
h3{{font-size:16px;margin:22px 0 8px}}
p{{margin:8px 0;max-width:110ch}}
p.note{{background:var(--tint);border-radius:8px;padding:10px 14px;max-width:none}}
p.ref{{margin-top:22px;color:var(--muted)}}
ul{{margin:6px 0;padding-left:20px}} li{{margin:4px 0;max-width:110ch}}
a{{color:var(--link)}}
code{{background:var(--code);border-radius:4px;padding:1px 5px;font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:4px 0 14px}}
.tile{{background:var(--tint);border-radius:10px;padding:12px 14px}}
.tlabel{{color:var(--muted);font-size:12.5px;min-height:2.6em}}
.tvalue{{font:700 24px/1.2 Cambria,Georgia,serif;margin:4px 0 8px}}
.tof{{font:400 14px -apple-system,sans-serif;color:var(--muted)}}
.tpct{{font-size:12px;color:var(--muted);margin-top:4px}}
.tile.done .tpct::before{{content:"✓ ";color:var(--ok)}}
.tablewrap{{overflow-x:auto;margin:8px 0 4px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{text-align:left;font-weight:600;color:var(--muted);font-size:12px;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:middle}}
tbody tr:hover td{{background:var(--tint)}}
tr.ace td{{background:var(--ace)}}
tr.ace:hover td{{filter:brightness(.97)}}
.right{{text-align:right}} .center{{text-align:center}} .left{{text-align:left}}
td.bar,td.delta{{min-width:130px}} td.frac{{min-width:90px}}
.val{{font-variant-numeric:tabular-nums;white-space:nowrap}}
td.bar.best .val{{font-weight:700}}
.track{{position:relative;height:6px;background:var(--tint);border-radius:3px;margin-top:4px;overflow:hidden}}
tr.ace .track{{background:var(--acetrack)}}
.track.thin{{height:4px}}
.fill{{position:absolute;left:0;top:0;bottom:0;background:var(--slate);border-radius:0 3px 3px 0}}
tr.ace .fill{{background:var(--accent)}}
.fill.neutral,tr.ace .fill.neutral{{background:var(--neutral)}}
.whisker{{position:absolute;top:2.5px;height:1px;background:var(--ink);opacity:.55}}
.dtrack .mid{{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--muted)}}
.dfill{{position:absolute;top:0;bottom:0}}
.dfill.pos{{background:var(--pos)}} .dfill.neg{{background:var(--neg)}}
.chip{{display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:2px 8px;border-radius:999px;background:var(--tint);white-space:nowrap}}
.chip .ico{{font-weight:700}}
.chip.ok .ico{{color:var(--ok)}} .chip.warn .ico{{color:var(--warn)}} .chip.run .ico{{color:var(--run)}} .chip.bad .ico{{color:var(--bad)}} .chip.wait .ico{{color:var(--muted)}}
details.sub{{border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:0 14px}}
details.sub[open]{{padding-bottom:10px}}
details summary{{cursor:pointer;padding:10px 0;font-weight:600}}
details.top summary{{list-style:none;padding:0}}
details.top summary::-webkit-details-marker{{display:none}}
details.top summary h2::after{{content:"  ▸";color:var(--muted);font-size:15px}}
details.top[open] summary h2::after{{content:"  ▾"}}
.subsec{{margin-top:6px}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:12.5px;margin:6px 0 0}}
.sw{{display:inline-block;width:12px;height:8px;border-radius:2px;margin-right:6px;vertical-align:middle}}
footer{{color:var(--muted);font-size:12px;text-align:center;padding:10px}}
@media (max-width:700px){{header,nav,main{{padding-left:14px;padding-right:14px}} section{{padding:14px}}}}
</style></head>
<body>
<header><h1>{title}</h1><p class="subtitle">{subtitle}</p>
<div class="stamp">Report generated <strong>{generated}</strong> · <span id="age"></span> · this page reloads every 10 minutes</div>
<div class="legend"><span><span class="sw" style="background:var(--accent)"></span>ACE rows</span>
<span><span class="sw" style="background:var(--slate)"></span>other methods (bar = mean, line = ±1 SD; GoEmotions bars scaled to its own maximum)</span>
<span><span class="sw" style="background:var(--pos)"></span>ΔAcc above Base</span><span><span class="sw" style="background:var(--neg)"></span>ΔAcc below Base</span></div>
</header>
<nav>{nav}</nav>
<main>{body}</main>
<footer>Rendered from v5_results.md by experiments/server_v5_monitor/export_html.py · internal working results, not manuscript evidence</footer>
<script>
(function(){{var s="{generated}".replace(" UTC","Z").replace(" ","T");var t=Date.parse(s);var el=document.getElementById("age");
if(!el||isNaN(t))return;function tick(){{var m=Math.round((Date.now()-t)/60000);el.textContent=m<1?"just now":m<60?m+" min ago":Math.floor(m/60)+" h "+(m%60)+" min ago";}}
tick();setInterval(tick,30000);}})();
</script>
</body></html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.markdown.with_suffix('.html')
    page = render(args.markdown.read_text(), str(output.parent.resolve()))
    temp = output.with_suffix('.html.tmp'); temp.write_text(page); temp.replace(output)
    print(output)


if __name__ == '__main__': main()

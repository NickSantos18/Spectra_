"""Transfere a configuração existente para o build, sem alterar os efeitos."""
from pathlib import Path
import re
raiz=Path(__file__).resolve().parents[1]
p=raiz/'frontend/static/inicio.html'
s=p.read_text(encoding='utf-8')
trecho=re.search(r'<script>\s*(?://[^\n]*\n\s*)*const token =.*?</script>',s,re.S)
if trecho and 'tailwind.config' in trecho.group():
    js=trecho.group().removeprefix('<script>').removesuffix('</script>')
    js=js.replace('tailwind.config =', 'module.exports =')
    js=js.replace('theme: {', "content: ['./frontend/static/*.{html,js}', './frontend/parciais/*.html'],\n    plugins: [require('@tailwindcss/forms')],\n    theme: {",1)
    (raiz/'tailwind.config.cjs').write_text(js.strip()+'\n',encoding='utf-8')
    s=s[:trecho.start()]+s[trecho.end():]
    s=s.replace('<script src="https://cdn.tailwindcss.com?plugins=forms"></script>','<link rel="stylesheet" href="/static/utilitarios.css">')
    p.write_text(s,encoding='utf-8')

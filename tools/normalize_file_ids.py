# tools/normalize_file_ids.py
import json, unicodedata, re
from pathlib import Path

SRC = Path("assets/file_ids.json")  # ajuste se usar outro caminho
BKP = Path("assets/file_ids.backup.json")

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)   # troca qualquer coisa não [a-z0-9_] por _
    s = re.sub(r"_+", "_", s).strip("_") # compacta e tira underscores das pontas
    # limita entre 3 e 32 chars (ajuste se quiser mais)
    if len(s) < 3: s = (s + "_xxx")[:3]
    if len(s) > 32: s = s[:32]
    return s

def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    # backup
    BKP.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    new = {}
    collisions = {}
    for k, v in data.items():
        nk = slugify(k)
        if nk in new and new[nk] != v:
            collisions.setdefault(nk, []).append(k)
        new[nk] = v

    SRC.write_text(json.dumps(new, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    if collisions:
        print("Atenção: colisões de chave após normalizar:")
        for nk, old_keys in collisions.items():
            print(" -", nk, " <- ", old_keys)

if __name__ == "__main__":
    main()

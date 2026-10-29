"""Checks run in CI on sample/, docs/palavra-fazer.json and data/stats.json. Run: python scripts/validate.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "sample"
FIELDS = ["significado", "definicoes", "exemplos_de_uso", "sinonimos", "antonimos", "ortografia_pronuncia",
          "historia_da_palavra", "significado_idiomatico_regional", "significado_em_contexto", "classe_gramatical",
          "separacao_silabica", "silaba_tonica", "singular", "plural", "feminino", "masculino", "infinitivo",
          "gerundio", "participio"]
SELF = r"(?i)como (uma|um) (ia|modelo)|modelo de linguagem|sou uma ia|assistente de ia"
BRANDS = r"(?i)\b(getech|herval|incoterm|bel fix|umbro|thunderx3|aerocool|fortrek|highmed|[eé]dez)\b"
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        errors.append(msg)


def one(sql: str):
    return duckdb.sql(sql).fetchone()[0]


pw, tx = (S / "palavras_sample.csv").as_posix(), (S / "textos_ia_sample.csv").as_posix()
ri, mf = (S / "rimas_sample.csv").as_posix(), (S / "mesmo_fingerprint_sample.csv").as_posix()
st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))

cols = [r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM '{pw}'").fetchall()]
check(all(f in cols for f in FIELDS), "words: the 19 AI text fields are there")
check(one(f"SELECT count(*) - count(DISTINCT id) FROM '{pw}'") == 0, "words: one row per id")
check(one(f"SELECT count(*) FROM '{pw}' WHERE palavra_sem_acento <> strip_accents(palavra)") == 0, "words: palavra_sem_acento = palavra without accents")
check(one(f"SELECT count(*) FROM '{pw}' WHERE ao_contrario <> reverse(lower(palavra))") == 0, "words: ao_contrario = palavra reversed")
check(set(r[0] for r in duckdb.sql(f"SELECT DISTINCT modelo FROM '{tx}'").fetchall()) <= {"text-davinci-002", "gpt-3.5-turbo"}, "AI texts: known models")
check(set(r[0] for r in duckdb.sql(f"SELECT DISTINCT campo FROM '{tx}'").fetchall()) <= set(FIELDS), "AI texts: known fields")
check(one(f"SELECT count(*) - count(DISTINCT (id_palavra, campo, modelo)) FROM '{tx}'") == 0, "AI texts: one text per word, field and model")
check(one(f"SELECT count(*) FROM '{tx}' WHERE regexp_matches(texto, '^\\s|\\s$')") == 0, "AI texts: trimmed (no leading or trailing spaces and line breaks)")
check(one(f"SELECT count(*) FROM '{tx}' WHERE regexp_matches(texto, '{SELF}')") == 0, "AI texts: no model talking about itself")
check(one(f"SELECT count(*) FROM '{tx}' WHERE regexp_matches(texto, '/[^/\\n]*\\?[^/\\n]*/')") == 0, "AI texts: no broken IPA")
check(one(f"SELECT count(*) FROM '{tx}' WHERE regexp_matches(texto, '[[:alpha:]]\\?[[:alpha:]]')") == 0, "AI texts: no characters lost mid-word")
check(one(f"SELECT count(*) FROM '{tx}' WHERE regexp_matches(texto, '(?i)^com (pelo menos|até) ')") == 0, "AI texts: no prompt echo at the start")
for name, f, col in (("words", pw, "palavra"), ("rhymes", ri, "palavra || ' ' || rima"), ("fingerprint pairs", mf, "palavra || ' ' || outra")):
    check(one(f"SELECT count(*) FROM '{f}' WHERE regexp_matches({col}, '{BRANDS}')") == 0, f"{name} sample: no brands that asked removal")
check(one(f"SELECT count(*) FROM '{ri}' WHERE palavra = rima") == 0, "rhymes: no word rhymes with itself")
check(one(f"SELECT count(*) FROM '{mf}' WHERE palavra = outra") == 0, "fingerprint pairs: no word paired with itself")

word = json.loads((ROOT / "docs" / "palavra-fazer.json").read_text(encoding="utf-8"))
check(word["palavra"] == "Fazer" and word["rimas"], "docs/palavra-fazer.json: the example word with rhymes")
check(sum(v["davinci"] + v["chatgpt"] for v in st["textos_por_campo"].values()) == st["textos_publicados_dicionario"],
      "stats: texts per field add up")
check(st["palavras"] == st["palavras_brutas"] - 37, "stats: only the 37 ignored words left out")

print(f"\n{len(errors)} failure(s)")
sys.exit(1 if errors else 0)

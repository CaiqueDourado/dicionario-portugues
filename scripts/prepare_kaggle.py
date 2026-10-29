"""Get the Kaggle folder ready to upload: stats.json and dataset-metadata.json with the description and every
file's columns. The build already writes flat file names (palavras-0000.parquet…), which is what Kaggle needs.

    python scripts/prepare_kaggle.py --kaggle D:\\dicionario_out\\dicionario-portugues\\data
    kaggle datasets create -p D:\\dicionario_out\\dicionario-portugues\\data          # first time
    kaggle datasets version -p D:\\dicionario_out\\dicionario-portugues\\data -m "…"   # later versions
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S, I, B = "string", "integer", "boolean"
AI = [("significado", "Meaning"), ("definicoes", "Definitions"), ("exemplos_de_uso", "Usage examples"),
      ("sinonimos", "Synonyms"), ("antonimos", "Antonyms"), ("ortografia_pronuncia", "Spelling and pronunciation"),
      ("historia_da_palavra", "History of the word"), ("significado_idiomatico_regional", "Idiomatic and regional meaning"),
      ("significado_em_contexto", "Meaning in context"), ("classe_gramatical", "Part of speech"),
      ("separacao_silabica", "Syllable split"), ("silaba_tonica", "Stressed syllable"), ("singular", "Singular"),
      ("plural", "Plural"), ("feminino", "Feminine"), ("masculino", "Masculine"), ("infinitivo", "Infinitive"),
      ("gerundio", "Gerund"), ("participio", "Past participle")]
COLS = {
    "palavras": ("One word per row: rule-based fields, occurrences and the 19 AI text fields (not reviewed).", [
        ("id", I, "Word id (textos_ia.id_palavra)"), ("palavra", S, "The word, capitalized"),
        ("palavra_sem_acento", S, "The word without accents"), ("numero_letras", I, "Number of letters"),
        ("ocorrencias", I, "Occurrences in the Bible, a quotes collection and Google searches"),
        ("radical", S, "Stem (simple stemmer)"), ("ao_contrario", S, "The word reversed, lower case"),
        ("vogais", S, "Vowels, hyphen separated"), ("consoantes", S, "Consonants, hyphen separated"),
        ("ultimos_caracteres", S, "Last characters, the rhyme key"), ("metaphone", S, "Metaphone key (Portuguese)"),
        ("fingerprint", S, "Fingerprint key"), ("tokenizada", S, "Stemmed token"), ("ngram", S, "N-gram key"),
        ("soft", S, "Soft normalized key"), ("tem_textos_ia", B, "Word has at least one AI text")]
        + [(c, S, f"{d}, AI-generated (gpt-3.5-turbo when there is one, else text-davinci-002), not reviewed") for c, d in AI]),
    "textos_ia": ("Every AI text with its model, long format.", [
        ("id_palavra", I, "Word id (palavras.id)"), ("campo", S, "Field: significado, sinonimos, plural…"),
        ("modelo", S, "text-davinci-002 or gpt-3.5-turbo"), ("texto", S, "The text, cleaned, not reviewed")]),
    "rimas": ("Up to 10 rhymes per word (same last characters).", [
        ("palavra", S, "Word"), ("rima", S, "A word that rhymes with it")]),
    "mesmo_fingerprint": ("Pairs of words with the same normalized key, mostly inflections.", [
        ("palavra", S, "Word"), ("outra", S, "Another word with the same key")]),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, required=True)
    a = ap.parse_args()
    k = a.kaggle
    shutil.copy(ROOT / "data" / "stats.json", k / "stats.json")  # the dictionary totals (no activities)
    resources = []
    for f in sorted(k.glob("*.parquet")):
        key, part = f.stem.rsplit("-", 1)
        desc, fields = COLS[key]
        resources.append({"path": f.name, "description": f"{desc} Part {int(part) + 1}.",
                          "schema": {"fields": [{"name": n, "type": t, "description": d} for n, t, d in fields]}})
    resources.append({"path": "stats.json", "description": "Totals and cleaning counts used in the README."})
    meta = {
        "title": "Dicionário do Português: 272 mil palavras",
        "subtitle": "Portuguese words with phonetic keys, rhymes and 2.9M AI-generated texts",
        "id": "caiquedourado/dicionario-portugues",
        "licenses": [{"name": "Attribution 4.0 International (CC BY 4.0)"}],
        "keywords": ["languages", "nlp", "text", "linguistics"],
        "description": (ROOT / "docs" / "kaggle-description.md").read_text(encoding="utf-8"),
        "isPrivate": False,
        "resources": resources,
    }
    (k / "dataset-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    copy = ROOT / "kaggle" / "dataset-metadata.json"
    copy.parent.mkdir(exist_ok=True)
    copy.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")  # the repo keeps a copy
    print(f"{len(resources)} files described -> {k / 'dataset-metadata.json'}")
    print(f"title {len(meta['title'])} chars · subtitle {len(meta['subtitle'])} chars")


if __name__ == "__main__":
    main()

"""Build the two public datasets from the raw export (exportar_dicionario.py), with DuckDB on your machine:

    python build_dicionario.py --raw D:\\dicionario_raw --out D:\\dicionario_out

dicionario-portugues/
  data/palavras-0000.parquet …   one row per word: rule-based fields + the 19 AI text fields (the ChatGPT text when
                                 there is one, otherwise the davinci text), cleaned
  data/textos_ia-*.parquet        every AI text with its model: id_palavra, campo, modelo, texto (both versions)
  data/rimas-*.parquet            palavra, rima (same last characters)
  data/mesmo_fingerprint-* palavra, outra (same fingerprint: spelling variants)
  samples/                       CSV samples + palavra-fazer.json
atividades-com-palavras/
  data/atividades.parquet        one row per activity: id_palavra, palavra, modelo, ordem, atividade
  samples/
stats.json                       counts before and after every cleaning step (send it to Claude)

Every table is written as flat parts under ~40 MB (Kaggle and GitHub friendly).
Cleaning: trims the leading spaces and line breaks, removes prompt echoes ("com pelo menos 10 exemplos."), removes IPA lost in the
old varchar conversion ("/?n'la?n/"), drops texts where the model talks about itself ("como uma IA",
"modelo de linguagem") and texts with characters lost mid-word ("pron?ncia"). Words marked ignorado are left out.
Needs duckdb. Nothing here touches SQL Server.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = {  # source column -> public column
    "significado": "significado", "definicoes": "definicoes", "exemplosDeUso": "exemplos_de_uso",
    "sinonimos": "sinonimos", "antonimos": "antonimos", "ortografiaPronuncia": "ortografia_pronuncia",
    "historiaDaPalavra": "historia_da_palavra", "significadoIdiomaticoRegional": "significado_idiomatico_regional",
    "significadoEmContexto": "significado_em_contexto", "classeGramatical": "classe_gramatical",
    "separacaoSilabica": "separacao_silabica", "silabaTonica": "silaba_tonica", "singular": "singular",
    "plural": "plural", "feminino": "feminino", "masculino": "masculino", "infinitivo": "infinitivo",
    "gerundio": "gerundio", "participio": "participio",
}
ACTIVITIES = "exerciciosJogos"
DAVINCI, CHATGPT = "text-davinci-002", "gpt-3.5-turbo"

ECHO = r"^\s*com (pelo menos|até|ate|no máximo|no maximo) [^.\n]*?(\.|caracteres|exemplos|palavras)[:.]?\s*"
IPA = r"\s*/[^/\n]*\?[^/\n]*/"
SELF = r"(?i)como (uma|um) (ia|modelo)|modelo de linguagem|sou uma ia|assistente de ia"
BROKEN = r"[[:alpha:]]\?[[:alpha:]]"


def copy_parts(con, sql: str, folder: Path, prefix: str) -> int:
    """Write the query as flat Parquet parts under ~40 MB: prefix-0000.parquet, prefix-0001.parquet…"""
    tmp = folder / f"_{prefix}"
    con.execute(f"COPY ({sql}) TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd, FILE_SIZE_BYTES '40MB', "
                f"PER_THREAD_OUTPUT false, OVERWRITE_OR_IGNORE true)")
    files = sorted(tmp.glob("*.parquet"), key=lambda f: int("".join(ch for ch in f.stem if ch.isdigit()) or 0))
    for old in folder.glob(f"{prefix}-*.parquet"):
        old.unlink()
    for i, f in enumerate(files):
        f.replace(folder / f"{prefix}-{i:04d}.parquet")
    tmp.rmdir()
    return len(files)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import duckdb

    dic, atv = a.out / "dicionario-portugues", a.out / "atividades-com-palavras"
    for d in (dic / "data", dic / "samples", atv / "data", atv / "samples"):
        d.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{(a.out / 'tmp').as_posix()}'")
    raw = lambda n: (a.raw / f"{n}.parquet").as_posix()  # noqa: E731
    stats: dict = {}

    con.execute(f"CREATE TABLE p AS SELECT * FROM read_parquet('{raw('palavras')}') WHERE coalesce(ignorado, false) = false")
    stats["palavras_brutas"] = con.execute(f"SELECT count(*) FROM read_parquet('{raw('palavras')}')").fetchone()[0]
    stats["palavras"] = con.execute("SELECT count(*) FROM p").fetchone()[0]

    # every AI text, long format, both models; the base column counts as davinci unless it is a copy of the ChatGPT text
    parts = []
    for src, dst in list(FIELDS.items()) + [(ACTIVITIES, "atividades")]:
        parts.append(f"SELECT id AS id_palavra, '{dst}' AS campo, '{DAVINCI}' AS modelo, CAST({src} AS VARCHAR) AS bruto, "
                     f"CAST({src}_chatGPT AS VARCHAR) AS outro FROM p")
        parts.append(f"SELECT id, '{dst}', '{CHATGPT}', CAST({src}_chatGPT AS VARCHAR), NULL FROM p")
    con.execute("CREATE TABLE t0 AS " + " UNION ALL ".join(parts))
    con.execute("DELETE FROM t0 WHERE bruto IS NULL OR trim(bruto) = ''")
    stats["textos_brutos"] = con.execute("SELECT count(*) FROM t0").fetchone()[0]
    stats["davinci_copia_do_chatgpt"] = con.execute(
        "SELECT count(*) FROM t0 WHERE modelo = ? AND trim(bruto) = trim(outro)", [DAVINCI]).fetchone()[0]
    con.execute("DELETE FROM t0 WHERE modelo = ? AND trim(bruto) = trim(outro)", [DAVINCI])

    con.execute(f"""CREATE TABLE t1 AS SELECT id_palavra, campo, modelo, bruto,
        regexp_replace(regexp_replace(regexp_replace(bruto, '{ECHO}', '', 'i'), '{IPA}', '', 'g'), '^\\s+|\\s+$', '', 'g') AS texto FROM t0""")
    stats["eco_do_prompt_removido"] = con.execute(f"SELECT count(*) FROM t1 WHERE regexp_matches(bruto, '{ECHO}', 'i')").fetchone()[0]
    stats["ipa_quebrado_removido"] = con.execute(f"SELECT count(*) FROM t1 WHERE regexp_matches(bruto, '{IPA}')").fetchone()[0]
    stats["descartado_ia_fala_de_si"] = con.execute(f"SELECT count(*) FROM t1 WHERE regexp_matches(texto, '{SELF}')").fetchone()[0]
    stats["descartado_caractere_perdido"] = con.execute(
        f"SELECT count(*) FROM t1 WHERE NOT regexp_matches(texto, '{SELF}') AND regexp_matches(texto, '{BROKEN}')").fetchone()[0]
    con.execute(f"""CREATE TABLE t AS SELECT id_palavra, campo, modelo, texto FROM t1
        WHERE texto <> '' AND NOT regexp_matches(texto, '{SELF}') AND NOT regexp_matches(texto, '{BROKEN}')""")
    stats["textos_publicados"] = con.execute("SELECT count(*) FROM t").fetchone()[0]
    stats["textos_por_campo"] = {c: {"davinci": d, "chatgpt": g} for c, d, g in con.execute(
        f"""SELECT campo, count(*) FILTER (modelo = '{DAVINCI}'), count(*) FILTER (modelo = '{CHATGPT}')
            FROM t GROUP BY campo ORDER BY campo""").fetchall()}

    # dicionario-portugues
    stats["arquivos_textos_ia"] = copy_parts(
        con, "SELECT * FROM t WHERE campo <> 'atividades' ORDER BY id_palavra, campo, modelo", dic / "data", "textos_ia")
    pick = ",\n".join(
        f"max(texto) FILTER (campo = '{c}' AND modelo = '{CHATGPT}') AS {c}_g, max(texto) FILTER (campo = '{c}' AND modelo = '{DAVINCI}') AS {c}_d"
        for c in FIELDS.values())
    con.execute(f"CREATE TABLE escolha AS SELECT id_palavra, {pick} FROM t GROUP BY id_palavra")
    cols = ", ".join(f"coalesce(e.{c}_g, e.{c}_d) AS {c}" for c in FIELDS.values())
    con.execute(f"""CREATE TABLE palavras AS SELECT
        p.id, p.palavra, strip_accents(p.palavra) AS palavra_sem_acento,
        length(regexp_replace(p.palavra, '[^[:alpha:]]', '', 'g')) AS numero_letras,
        coalesce(p.ocorrencias, 0) AS ocorrencias, p.radical,
        reverse(lower(p.palavra)) AS ao_contrario, p.vogais, p.consoantes, p.ultimosCaracteres AS ultimos_caracteres,
        p.metaphone, p.fingerprint, p.tokenizada, p.ngram, p.soft,
        e.id_palavra IS NOT NULL AS tem_textos_ia, {cols}
        FROM p LEFT JOIN escolha e ON e.id_palavra = p.id ORDER BY ocorrencias DESC, p.palavra""")
    stats["arquivos_palavras"] = copy_parts(con, "SELECT * FROM palavras", dic / "data", "palavras")
    stats["palavras_com_textos_ia"] = con.execute("SELECT count(*) FROM palavras WHERE tem_textos_ia").fetchone()[0]
    stats["palavras_ocorrencias_gt0"] = con.execute("SELECT count(*) FROM palavras WHERE ocorrencias > 0").fetchone()[0]
    stats["palavra_sem_acento_mudou"] = con.execute(
        "SELECT count(*) FROM palavras w JOIN p USING (id) WHERE w.palavra_sem_acento <> p.palavra_sem_acento").fetchone()[0]

    for name, other in (("rimas", "rima"), ("mesmo_fingerprint", "outra")):
        src = raw(name)
        col = "idPalavraRima" if name == "rimas" else "idPalavraMesmoFingerprint"
        stats[f"arquivos_{name}"] = copy_parts(con, f"""SELECT a.palavra, b.palavra AS {other} FROM read_parquet('{src}') r
            JOIN palavras a ON a.id = r.idPalavra JOIN palavras b ON b.id = r.{col}
            ORDER BY a.ocorrencias DESC, a.palavra, b.ocorrencias DESC""", dic / "data", name)
        stats[name] = con.execute(f"SELECT count(*) FROM read_parquet('{(dic / 'data').as_posix()}/{name}-*.parquet')").fetchone()[0]

    # atividades-com-palavras: one row per item of the list
    con.execute(f"""CREATE TABLE atividades AS
        WITH s AS (SELECT t.id_palavra, w.palavra, t.modelo,
                          unnest(string_split_regex(t.texto, '\\s*(\\n+|;\\s+|\\s-\\s|^-\\s*|(^|\\s)\\d{{1,2}}[.)]\\s)\\s*')) AS item
                   FROM t JOIN palavras w ON w.id = t.id_palavra WHERE t.campo = 'atividades')
        SELECT id_palavra, palavra, modelo,
               row_number() OVER (PARTITION BY id_palavra, modelo) AS ordem,
               trim(regexp_replace(item, '^[\\s.;-]+|[\\s.;-]+$', '', 'g')) AS atividade
        FROM s WHERE length(trim(regexp_replace(item, '^[\\s.;-]+|[\\s.;-]+$', '', 'g'))) >= 3""")
    con.execute(f"COPY (SELECT * FROM atividades ORDER BY id_palavra, modelo, ordem) "
                f"TO '{(atv / 'data' / 'atividades.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    stats["atividades"] = con.execute("SELECT count(*) FROM atividades").fetchone()[0]
    stats["atividades_palavras"] = con.execute("SELECT count(DISTINCT id_palavra) FROM atividades").fetchone()[0]

    # samples (top words by occurrence) and one full word as JSON
    con.execute(f"COPY (SELECT * FROM palavras LIMIT 1000) TO '{(dic / 'samples' / 'palavras_sample.csv').as_posix()}' (HEADER)")
    con.execute(f"""COPY (SELECT t.* FROM t JOIN (SELECT id FROM palavras LIMIT 200) w ON w.id = t.id_palavra
        WHERE campo <> 'atividades') TO '{(dic / 'samples' / 'textos_ia_sample.csv').as_posix()}' (HEADER)""")
    for name in ("rimas", "mesmo_fingerprint"):
        con.execute(f"COPY (SELECT * FROM read_parquet('{(dic / 'data').as_posix()}/{name}-*.parquet') LIMIT 2000) "
                    f"TO '{(dic / 'samples' / f'{name}_sample.csv').as_posix()}' (HEADER)")
    con.execute(f"""COPY (SELECT a.* FROM atividades a JOIN (SELECT id FROM palavras LIMIT 300) w ON w.id = a.id_palavra)
        TO '{(atv / 'samples' / 'atividades_sample.csv').as_posix()}' (HEADER)""")
    row = con.execute("SELECT * FROM palavras WHERE lower(palavra) = 'fazer' LIMIT 1").fetchone()
    names = [d[0] for d in con.description]
    word = dict(zip(names, row))
    word["rimas"] = [r[0] for r in con.execute(
        f"SELECT rima FROM read_parquet('{(dic / 'data').as_posix()}/rimas-*.parquet') WHERE palavra = ? LIMIT 10", [word["palavra"]]).fetchall()]
    (dic / "samples" / "palavra-fazer.json").write_text(json.dumps(word, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    (a.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

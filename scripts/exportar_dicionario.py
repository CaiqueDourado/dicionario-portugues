"""Export the dictionary tables from SQL Server to Parquet (one sequential read per table), then profile them
with DuckDB on the Parquet, without touching SQL Server again.

    python exportar_dicionario.py --server localhost --out D:\\dicionario_raw
    python exportar_dicionario.py --out D:\\dicionario_raw --profile-only      # profile again, no export

Writes in --out: palavras.parquet (all 100 columns), rimas.parquet (palavras_rel_rimas, top 10 per word),
mesmo_fingerprint.parquet, and perfil_dicionario.txt (column fill rates, samples, counts). The raw copy stays
on your machine. Needs pyodbc, pyarrow and duckdb. Re-running skips tables already exported.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

TABLES = {
    "palavras": "SELECT * FROM dicionario.dbo.palavras WITH (NOLOCK)",
    "rimas": "SELECT * FROM dicionario.dbo.palavras_rel_rimas WITH (NOLOCK)",
    "mesmo_fingerprint": "SELECT * FROM dicionario.dbo.palavras_rel_mesmo_fingerprint WITH (NOLOCK)",
}
BATCH = 100_000


def export(server: str, out: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyodbc
    cnx = pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};Trusted_Connection=yes", autocommit=True)
    cur = cnx.cursor()
    types = {int: pa.int64(), float: pa.float64(), str: pa.string(), bool: pa.bool_()}
    for name, sql in TABLES.items():
        target = out / f"{name}.parquet"
        if target.exists():
            print(f"{name}: already there, skipped")
            continue
        t0 = time.time()
        cur.execute(sql)
        schema = pa.schema([(d[0], types.get(d[1], pa.string())) for d in cur.description])
        conv = [d[1] not in types for d in cur.description]          # decimals, dates… as text
        tmp, writer, total = target.with_suffix(".tmp"), None, 0
        while rows := cur.fetchmany(BATCH):
            cols = {f.name: [(None if r[i] is None else str(r[i])) if conv[i] else r[i] for r in rows]
                    for i, f in enumerate(schema)}
            table = pa.Table.from_pydict(cols, schema=schema)
            writer = writer or pq.ParquetWriter(tmp, schema, compression="zstd")
            writer.write_table(table)
            total += len(rows)
            print(f"\r{name}: {total:,} rows  {time.time() - t0:.0f}s", end="", flush=True)
        if writer:
            writer.close()
            tmp.replace(target)
        print(f"\r{name}: {total:,} rows  {time.time() - t0:.0f}s -> {target}")


def mask(v) -> str:
    s = re.sub(r"\s+", " ", str(v))
    return s[:110] + ("…" if len(s) > 110 else "")


def profile(out: Path) -> None:
    import duckdb
    con = duckdb.connect()
    p = (out / "palavras.parquet").as_posix()
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{p}')")
    cols = con.execute("DESCRIBE p").fetchall()
    n = con.execute("SELECT count(*) FROM p").fetchone()[0]
    with open(out / "perfil_dicionario.txt", "w", encoding="utf-8") as f:
        print(f"# palavras: {n:,} rows, {len(cols)} columns", file=f)
        print("\n## fill rate and one example per column (text cut at 110 chars)", file=f)
        for c, t, *_ in cols:
            q = f'"{c}"'
            filled = con.execute(f"SELECT count(*) FROM p WHERE {q} IS NOT NULL AND trim(CAST({q} AS VARCHAR)) <> ''").fetchone()[0]
            ex = con.execute(f"SELECT {q} FROM p WHERE {q} IS NOT NULL AND trim(CAST({q} AS VARCHAR)) <> '' "
                             f"ORDER BY ocorrencias DESC NULLS LAST LIMIT 1").fetchone() if filled else None
            print(f"{c:<40} {t:<10} {filled:>9,} ({filled / n:6.1%})  {mask(ex[0]) if ex else ''}", file=f)
        print("\n## the three counts in the notes (187 mil, 272.663, 181.384)", file=f)
        for label, cond in (("ocorrencias > 1000", "ocorrencias > 1000"), ("ocorrencias > 0", "ocorrencias > 0")):
            print(f"{label}: {con.execute(f'SELECT count(*) FROM p WHERE {cond}').fetchone()[0]:,}", file=f)
        for c, *_ in cols:
            if c.lower() in ("significado", "significado_chatgpt", "exerciciosjogos", "exerciciosjogos_chatgpt"):
                sql = "SELECT count(*) FROM p WHERE trim(coalesce(CAST(\"" + c + "\" AS VARCHAR), '')) <> ''"
                print(f"{c} filled: {con.execute(sql).fetchone()[0]:,}", file=f)
        print("\n## three full words (highest ocorrencias), every column", file=f)
        for row in con.execute("SELECT * FROM p ORDER BY ocorrencias DESC NULLS LAST LIMIT 3").fetchall():
            print("-" * 60, file=f)
            for (c, *_), v in zip(cols, row):
                if v not in (None, ""):
                    print(f"{c}: {mask(v)}", file=f)
        print("\n## AI text problems (counts over all text columns)", file=f)
        text_cols = [c for c, t, *_ in cols if t == "VARCHAR"]
        for label, rx in (("starts with 2 spaces", r"^  "), ("prompt echo 'com pelo menos'", r"(?i)^\s*com pelo menos"),
                          ("'?' inside (broken IPA/encoding)", r"\?\?"), ("'como uma IA' / 'modelo de linguagem'", r"(?i)como (uma|um) (ia|modelo)|modelo de linguagem")):
            parts = " + ".join(f"count(*) FILTER (regexp_matches(CAST(\"{c}\" AS VARCHAR), '{rx}'))" for c in text_cols)
            print(f"{label}: {con.execute(f'SELECT {parts} FROM p').fetchone()[0]:,} cells", file=f)
        for name in ("rimas", "mesmo_fingerprint"):
            path = out / f"{name}.parquet"
            if path.exists():
                r = con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]
                d = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()
                print(f"\n## {name}: {r:,} rows; columns: " + ", ".join(x[0] for x in d), file=f)
    print(f"-> {out / 'perfil_dicionario.txt'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="localhost")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--profile-only", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if not a.profile_only:
        export(a.server, a.out)
    profile(a.out)


if __name__ == "__main__":
    main()

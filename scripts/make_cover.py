"""Cover image (EN and PT) from data/stats.json, sample/palavras_sample.csv and docs/palavra-fazer.json.
Run: python scripts/make_cover.py"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, LINE, BG, CARD = "#111111", "#5c5c5c", "#d9dde3", "#fdfdfc", "#ffffff"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MONO = "DejaVu Sans Mono"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

FIELDS = {"significado": ("meaning", "significado"), "sinonimos": ("synonyms", "sinônimos"),
          "classe_gramatical": ("part of speech", "classe gramatical"), "separacao_silabica": ("syllables", "separação silábica"),
          "plural": ("plural", "plural"), "exemplos_de_uso": ("usage examples", "exemplos de uso")}
T = {
    "": dict(title="Portuguese Dictionary · Dicionário do Português",
             sub="{w} words · {t} AI-generated texts · {r} rhymes · phonetic keys and word frequency",
             p1="One word", p1s="rule-based fields", p2="AI texts by field", p2s="GPT-3.5 and davinci, 2022–2023, not reviewed",
             p3="Most frequent words", p3s="occurrences in searches, Bible and quotes", mi="M", lab=0,
             foot="dicionario-portugues · the data behind Tudo sobre as Palavras"),
    ".pt-BR": dict(title="Dicionário do Português",
                   sub="{w} palavras · {t} textos gerados por IA · {r} rimas · chaves fonéticas e frequência",
                   p1="Uma palavra", p1s="campos calculados por regra", p2="Textos de IA por campo", p2s="GPT-3.5 e davinci, 2022–2023, sem revisão",
                   p3="Palavras mais frequentes", p3s="ocorrências em buscas, Bíblia e frases", mi="mi", lab=1,
                   foot="dicionario-portugues · os dados por trás do Tudo sobre as Palavras"),
}


def mil(n, pt, unit):
    s = f"{n / 1e6:.1f}"
    return (s.replace(".", ",") if pt else s) + f" {unit}"


def num(n, pt):
    s = f"{n:,}"
    return s.replace(",", ".") if pt else s


def panel(ax, x, w, color, title, sub):
    ax.add_patch(FancyBboxPatch((x, 6), w, 52, boxstyle="round,pad=0,rounding_size=1.4", fc=CARD, ec=LINE, lw=1.1))
    ax.add_patch(FancyBboxPatch((x, 57.2), w, 0.8, boxstyle="square,pad=0", fc=color, ec="none"))
    ax.text(x + 2, 53, title, fontsize=13, weight="bold", color=INK, va="center")
    ax.text(x + 2, 49.2, sub, fontsize=8.6, color=MUTED, va="center")


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    word = json.loads((ROOT / "docs" / "palavra-fazer.json").read_text(encoding="utf-8"))
    with open(ROOT / "sample" / "palavras_sample.csv", encoding="utf-8") as f:
        top = [(r["palavra"], int(r["ocorrencias"])) for r in csv.DictReader(f)][:6]
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    for suf, t in T.items():
        pt = bool(suf)
        fig = plt.figure(figsize=(12, 6.2), dpi=100)
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 74)
        ax.axis("off")
        ax.text(3, 69, t["title"], fontsize=21, weight="bold", color=INK, va="center")
        ax.text(3, 63.6, t["sub"].format(w=num(st["palavras"], pt), t=mil(st["textos_publicados_dicionario"], pt, t["mi"]),
                                         r=mil(st["rimas"], pt, t["mi"])), fontsize=10.5, color=MUTED, va="center")

        x1, w1 = 3, 33
        panel(ax, x1, w1, AQUA, t["p1"], t["p1s"])
        ax.text(x1 + 2, 43, word["palavra"], fontsize=17, weight="bold", color=INK, va="center")
        rows = [("metaphone", word["metaphone"]), ("radical", word["radical"]), ("ao_contrario", word["ao_contrario"]),
                ("vogais", word["vogais"]), ("consoantes", word["consoantes"]),
                ("rimas", ", ".join(word["rimas"][:2]) + "…")]
        for i, (k, v) in enumerate(rows):
            y = 36 - i * 4.6
            ax.text(x1 + 2, y, k, fontsize=8.6, color=MUTED, va="center", family=MONO)
            ax.text(x1 + 14, y, v, fontsize=9.2, color=INK, va="center", family=MONO)

        x2, w2 = x1 + w1 + 2.5, 40
        panel(ax, x2, w2, BLUE, t["p2"], t["p2s"])
        counts = st["textos_por_campo"]
        mx = max(v["davinci"] + v["chatgpt"] for v in counts.values())
        for i, (k, names) in enumerate(FIELDS.items()):
            y = 42 - i * 6.2
            v = counts[k]["davinci"] + counts[k]["chatgpt"]
            ax.text(x2 + 2, y + 1.4, names[t["lab"]], fontsize=8.8, color=INK, va="center")
            bw = max(0.6, 24 * v / mx)
            ax.add_patch(FancyBboxPatch((x2 + 2, y - 2.1), bw, 1.9, boxstyle="square,pad=0", fc=BLUE, ec="none"))
            ax.text(x2 + 2.8 + bw, y - 1.15, num(v, pt), fontsize=8, color=MUTED, va="center")

        x3 = x2 + w2 + 2.5
        w3 = 117 - x3
        panel(ax, x3, w3, ORANGE, t["p3"], t["p3s"])
        tm = top[0][1]
        for i, (k, v) in enumerate(top):
            y = 42 - i * 6.2
            ax.text(x3 + 2, y + 1.4, k, fontsize=8.8, color=INK, va="center")
            bw = max(0.6, 20 * v / tm)
            ax.add_patch(FancyBboxPatch((x3 + 2, y - 2.1), bw, 1.9, boxstyle="square,pad=0", fc=ORANGE, ec="none"))
            ax.text(x3 + 2.8 + bw, y - 1.15, num(v, pt), fontsize=8, color=MUTED, va="center")

        ax.text(3, 2.6, t["foot"], fontsize=8.4, color=MUTED)
        ax.text(117, 2.6, "github.com/CaiqueDourado", fontsize=8.4, color=MUTED, ha="right")
        fig.savefig(out / f"cover{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

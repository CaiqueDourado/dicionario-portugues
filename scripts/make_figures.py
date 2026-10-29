"""README figure (EN and PT): AI texts per field and model, from data/stats.json.
Run: python scripts/make_figures.py"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GRID, BG = "#111111", "#5c5c5c", "#e6e8eb", "#fdfdfc"
CHATGPT, DAVINCI = "#2a78d6", "#eb6834"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

NAMES = {
    "significado": ("meaning", "significado"), "definicoes": ("definitions", "definições"),
    "exemplos_de_uso": ("usage examples", "exemplos de uso"), "sinonimos": ("synonyms", "sinônimos"),
    "antonimos": ("antonyms", "antônimos"), "ortografia_pronuncia": ("spelling and pronunciation", "ortografia e pronúncia"),
    "historia_da_palavra": ("word history", "história da palavra"),
    "significado_idiomatico_regional": ("idiomatic and regional meaning", "significado idiomático e regional"),
    "significado_em_contexto": ("meaning in context", "significado em contexto"),
    "classe_gramatical": ("part of speech", "classe gramatical"), "separacao_silabica": ("syllable split", "separação silábica"),
    "silaba_tonica": ("stressed syllable", "sílaba tônica"), "singular": ("singular", "singular"), "plural": ("plural", "plural"),
    "feminino": ("feminine", "feminino"), "masculino": ("masculine", "masculino"), "infinitivo": ("infinitive", "infinitivo"),
    "gerundio": ("gerund", "gerúndio"), "participio": ("past participle", "particípio"),
}
T = {"": dict(title="AI texts per field", sub="published texts in each field, by model", x="texts", lab=0,
              g="gpt-3.5-turbo", d="text-davinci-002 (most frequent words)", sep=","),
     ".pt-BR": dict(title="Textos de IA por campo", sub="textos publicados em cada campo, por modelo", x="textos", lab=1,
                    g="gpt-3.5-turbo", d="text-davinci-002 (palavras mais frequentes)", sep=".")}


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))["textos_por_campo"]
    rows = sorted(st.items(), key=lambda kv: kv[1]["chatgpt"] + kv[1]["davinci"])
    out = ROOT / "docs" / "img"
    for suf, t in T.items():
        fig, ax = plt.subplots(figsize=(10, 7.2), dpi=110)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        labels = [NAMES[k][t["lab"]] for k, _ in rows]
        g = [v["chatgpt"] for _, v in rows]
        d = [v["davinci"] for _, v in rows]
        ax.barh(labels, g, color=CHATGPT, label=t["g"], height=0.62)
        ax.barh(labels, d, left=g, color=DAVINCI, label=t["d"], height=0.62)
        for i, (a, b) in enumerate(zip(g, d)):
            ax.text(a + b + 1500, i, f"{a + b:,}".replace(",", t["sep"]), va="center", fontsize=8.5, color=MUTED)
        ax.set_xlim(0, max(a + b for a, b in zip(g, d)) * 1.15)
        ax.xaxis.set_major_formatter(lambda v, _: f"{int(v / 1000)}k" if suf == "" else f"{int(v / 1000)} mil")
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=INK, labelsize=9.5, length=0)
        ax.set_xlabel(t["x"], color=MUTED, fontsize=9)
        fig.text(0.02, 0.965, t["title"], fontsize=15, weight="bold", color=INK)
        fig.text(0.02, 0.93, t["sub"], fontsize=10, color=MUTED)
        ax.legend(loc="lower right", frameon=False, fontsize=9)
        fig.subplots_adjust(left=0.27, right=0.97, top=0.89, bottom=0.08)
        fig.savefig(out / f"campos{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

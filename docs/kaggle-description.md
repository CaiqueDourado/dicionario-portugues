**Dicionário do Português**: a Brazilian Portuguese word list of **272,626 words**, each with **rule-based fields** (word without accents, stem, reversed word, vowels, consonants, last characters, number of letters, Metaphone and fingerprint keys) and how often it appears in the author's corpora, plus **2,916,780 AI-generated texts** for 187,949 of them: meaning, definitions, synonyms, antonyms, part of speech, syllables, stressed syllable, plural, feminine, gerund, participle… Also **2,287,766 rhymes** and **11,868,060 pairs of words that share a key**.

> **The AI texts were not reviewed.** They were generated in 2022–2023 by `text-davinci-002` and `gpt-3.5-turbo` and contain mistakes (*"Fazer significa fazer algo"*, *Curso* as a proper noun, *Brasils* as a plural). Use them as a starting point, as training or evaluation data for language tools, or to study what those models got wrong, not as an authority on Portuguese.

![Dicionário do Português](https://raw.githubusercontent.com/CaiqueDourado/dicionario-portugues/main/docs/img/cover.png)

## How a word is structured

![One word in JSON](https://raw.githubusercontent.com/CaiqueDourado/dicionario-portugues/main/docs/img/palavra-json.png)

*Fazer*, the most frequent word, with 16 of its 36 fields and the texts cut. The rule-based fields are reliable; the AI texts show the problem in this very word: the "feminine" of a verb.

## Files

- `palavras-*.parquet` (272,626 rows): one word per row: rule-based fields, `ocorrencias`, and the 19 AI text fields (the `gpt-3.5-turbo` text when there is one, otherwise the `text-davinci-002` text).
- `textos_ia-*.parquet` (2,916,780 rows): every AI text with its model: `id_palavra`, `campo`, `modelo`, `texto`.
- `rimas-*.parquet` (2,287,766 rows): `palavra`, `rima`, up to 10 rhymes per word (same last characters).
- `mesmo_fingerprint-*.parquet` (11,868,060 rows): `palavra`, `outra`, words with the same normalized key, mostly inflections.
- `stats.json`: totals and every cleaning count.

## The site this comes from

![Tudo sobre as Palavras](https://raw.githubusercontent.com/CaiqueDourado/dicionario-portugues/main/docs/img/tudosobreaspalavras.com_screenshot.png)

**Tudo sobre as Palavras** (2023) had about 187 thousand pages, one per word with AI texts, with these fields in the left menu. Static HTML generated in C# from SQL Server, hosted on Google Cloud Storage. Archived page: [Arrogado](https://web.archive.org/web/20250923215535/https://tudosobreaspalavras.com/tudo-sobre-a-palavra-arrogado).

## What the data shows

![AI texts per field](https://raw.githubusercontent.com/CaiqueDourado/dicionario-portugues/main/docs/img/campos.png)

`text-davinci-002` (temperature 0) wrote the texts of the ~9,100 most frequent words; `gpt-3.5-turbo` (temperature 0.9) wrote most of the rest. In the source table the davinci columns held copies of the ChatGPT text in 2,754,358 cells; those copies were removed, so each text appears once, with its real model. Typical mistakes are kept as written: definitions that repeat the word, "proper noun" for common nouns, letters split one by one (*C-U-R-S-O*), English answers (*Noun*), plurals of invariable words, "feminine" of verbs.

## How it was made

![Flow](https://raw.githubusercontent.com/CaiqueDourado/dicionario-portugues/main/docs/img/flow.png)

- **Word list**: compiled from several word lists and from the author's corpora. `ocorrencias` counts occurrences in the Bible, a quotes collection and Google searches with volume (109,230 words appear at least once).
- **Rule-based fields**: computed by the author's C# code; `palavra_sem_acento`, `ao_contrario` and `numero_letras` were recomputed (the old code turned *ss* into *B* in 28,046 words).
- **AI texts**: one prompt per field per word. The build removed the davinci copies, trimmed spaces and line breaks, cut 5,883 prompt echoes and 45,686 broken phonetic transcriptions, and dropped 1,280 texts where the model talks about itself and 6,330 with characters lost mid-word. 37 words marked as ignored are left out.

## Limits

- The AI texts were not reviewed; some still carry prompt echoes mid-text.
- The list mixes Brazilian Portuguese with inflections, names, loanwords and a few typos.
- `ocorrencias` reflects the author's corpora, not Portuguese in general.
- Rhymes are by spelling, not sound; same-key pairs include unrelated words.

## Code, sample and related data

GitHub: [CaiqueDourado/dicionario-portugues](https://github.com/CaiqueDourado/dicionario-portugues) (build scripts, CSV sample, notebook). Related: [Google Keywords](https://www.kaggle.com/datasets/caiquedourado/google-keywords-dataset), [palavras-da-biblia](https://github.com/CaiqueDourado/palavras-da-biblia), [brazilian-names-surnames](https://github.com/CaiqueDourado/brazilian-names-surnames), [DedupKit](https://github.com/CaiqueDourado/DedupKit).

License: CC BY 4.0 (data), MIT (code). Author: Caique Dourado.

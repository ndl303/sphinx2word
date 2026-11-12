"""
Default labels of the Word document in the language of the project (``language`` in ``conf.py``).

LaTeX gets these words from babel. Sphinx's own translations cover only some of them ("Contents", "Index", "Python
Module Index", "Fig. %s"), so this module has a small table, like babel's, for common languages, and falls back to
Sphinx's translations and then to English. ``word_translate_labels = False`` keeps the English labels.
"""

from __future__ import annotations

from typing import Dict, Optional

ENGLISH = {
    "figure": "Figure",
    "table": "Table",
    "code-block": "Listing",
    "contents": "Contents",
    "list_of_figures": "List of Figures",
    "list_of_tables": "List of Tables",
    "index": "Index",
    "module_index": "Python Module Index",
    "appendix": "Appendix",
    "see": "see %s",
    "see_also": "see also %s",
}

# figure, table, contents, list of figures, list of tables, index, appendix (as babel names them)
_TABLE = {
    "de": ("Abbildung", "Tabelle", "Inhaltsverzeichnis", "Abbildungsverzeichnis", "Tabellenverzeichnis",
           "Stichwortverzeichnis", "Anhang"),
    "fr": ("Figure", "Tableau", "Table des matières", "Table des figures", "Liste des tableaux", "Index",
           "Annexe"),
    "es": ("Figura", "Tabla", "Índice", "Índice de figuras", "Índice de tablas", "Índice alfabético", "Apéndice"),
    "it": ("Figura", "Tabella", "Indice", "Elenco delle figure", "Elenco delle tabelle", "Indice analitico",
           "Appendice"),
    "nl": ("Figuur", "Tabel", "Inhoudsopgave", "Lijst van figuren", "Lijst van tabellen", "Index", "Bijlage"),
    "pt": ("Figura", "Tabela", "Sumário", "Lista de Figuras", "Lista de Tabelas", "Índice", "Apêndice"),
    "sv": ("Figur", "Tabell", "Innehåll", "Figurer", "Tabeller", "Sakregister", "Bilaga"),
    "da": ("Figur", "Tabel", "Indhold", "Figurer", "Tabeller", "Indeks", "Bilag"),
    "nb": ("Figur", "Tabell", "Innhold", "Figurer", "Tabeller", "Register", "Tillegg"),
    "fi": ("Kuva", "Taulukko", "Sisältö", "Kuvat", "Taulukot", "Hakemisto", "Liite"),
    "pl": ("Rysunek", "Tabela", "Spis treści", "Spis rysunków", "Spis tabel", "Indeks", "Dodatek"),
    "cs": ("Obrázek", "Tabulka", "Obsah", "Seznam obrázků", "Seznam tabulek", "Rejstřík", "Příloha"),
}
_TABLE_KEYS = ("figure", "table", "contents", "list_of_figures", "list_of_tables", "index", "appendix")

# Labels that Sphinx's message catalogs translate: key -> msgid. A "%s" in the msgid is removed from the result.
_SPHINX_MSGIDS = {
    "figure": "Fig. %s",
    "table": "Table %s",
    "code-block": "Listing %s",
    "contents": "Contents",
    "index": "Index",
    "module_index": "Python Module Index",
    "see": "see %s",
    "see_also": "see also %s",
}


def language_code(language: Optional[str]) -> str:
    """"de_DE" -> "de", "pt-BR" -> "pt", "no" -> "nb"; English for None."""
    code = (language or "en").replace("-", "_").lower().split("_")[0]
    return {"no": "nb", "nn": "nb"}.get(code, code)


def default_labels(language: Optional[str], translate: bool = True, gettext=None) -> Dict[str, str]:
    """
    The default labels for ``language``.

    Parameters
    ----------
    language:
        Sphinx's ``language`` setting.
    translate:
        ``False`` gives the English labels.
    gettext:
        Sphinx's translation function for its own catalog (``sphinx.locale._``), used for the words the table
        does not have.
    """
    labels = dict(ENGLISH)
    code = language_code(language)
    if not translate or code == "en":
        return labels
    if gettext is not None:
        for key, msgid in _SPHINX_MSGIDS.items():
            text = gettext(msgid)
            if text and text != msgid:
                labels[key] = text if key in ("see", "see_also") else text.replace("%s", "").strip()
    if code in _TABLE:
        labels.update(zip(_TABLE_KEYS, _TABLE[code]))
    return labels

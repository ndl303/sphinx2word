"""
Convert LaTeX mathematics, as written in Sphinx ``:math:`` roles and ``.. math::`` directives, into Office Math
Markup Language (OMML), the native equation format of Microsoft Word.

The converter is a small recursive-descent parser. It does not try to be a TeX engine; it understands the subset of
LaTeX that MathJax/KaTeX users write in documentation: scripts, fractions, roots, delimiters, accents, fonts, big
operators, functions, matrices, cases and aligned multi-line equations. Anything it does not understand raises
:class:`LatexMathError` so the caller can report it instead of silently producing a wrong equation.

Main entry points:

* :func:`latex_to_omml` - returns an ``<m:oMath>`` element (inline) or ``<m:oMathPara>`` (display) as an XML string.
* :func:`split_display_math` - splits a Sphinx math block into separate equations the same way Sphinx does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class LatexMathError(ValueError):
    """Raised when a LaTeX expression cannot be converted."""


# ----------------------------------------------------------------------------------------------------------------------
#   Symbol tables
# ----------------------------------------------------------------------------------------------------------------------

GREEK = {
    "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3", "delta": "\u03b4", "epsilon": "\u03f5",
    "varepsilon": "\u03b5", "zeta": "\u03b6", "eta": "\u03b7", "theta": "\u03b8", "vartheta": "\u03d1",
    "iota": "\u03b9", "kappa": "\u03ba", "varkappa": "\u03f0", "lambda": "\u03bb", "mu": "\u03bc", "nu": "\u03bd",
    "xi": "\u03be", "omicron": "\u03bf", "pi": "\u03c0", "varpi": "\u03d6", "rho": "\u03c1", "varrho": "\u03f1",
    "sigma": "\u03c3", "varsigma": "\u03c2", "tau": "\u03c4", "upsilon": "\u03c5", "phi": "\u03d5",
    "varphi": "\u03c6", "chi": "\u03c7", "psi": "\u03c8", "omega": "\u03c9", "digamma": "\u03dd",
    "Gamma": "\u0393", "Delta": "\u0394", "Theta": "\u0398", "Lambda": "\u039b", "Xi": "\u039e", "Pi": "\u03a0",
    "Sigma": "\u03a3", "Upsilon": "\u03a5", "Phi": "\u03a6", "Psi": "\u03a8", "Omega": "\u03a9",
    "varGamma": "\U0001d6e4", "varDelta": "\U0001d6e5", "varTheta": "\U0001d6e9", "varLambda": "\U0001d6ec",
    "varXi": "\U0001d6ef", "varPi": "\U0001d6f1", "varSigma": "\U0001d6f4", "varUpsilon": "\U0001d6f6",
    "varPhi": "\U0001d6f7", "varPsi": "\U0001d6f9", "varOmega": "\U0001d6fa",
}

# Upper case Greek letters are upright in standard LaTeX; Word italicises everything unless told otherwise.
UPRIGHT_GREEK = {GREEK[k] for k in ("Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon", "Phi",
                                    "Psi", "Omega")}

SYMBOLS = {
    # binary operators
    "pm": "\u00b1", "mp": "\u2213", "times": "\u00d7", "div": "\u00f7", "cdot": "\u22c5", "ast": "\u2217",
    "star": "\u22c6", "circ": "\u2218", "bullet": "\u2219", "cap": "\u2229", "cup": "\u222a", "wedge": "\u2227",
    "land": "\u2227", "vee": "\u2228", "lor": "\u2228", "oplus": "\u2295", "ominus": "\u2296", "otimes": "\u2297",
    "oslash": "\u2298", "odot": "\u2299", "setminus": "\u2216", "smallsetminus": "\u2216", "uplus": "\u228e",
    "sqcap": "\u2293", "sqcup": "\u2294", "dagger": "\u2020", "ddagger": "\u2021", "amalg": "\u2a3f",
    "wr": "\u2240", "diamond": "\u22c4", "triangleleft": "\u25c3", "triangleright": "\u25b9", "cdotp": "\u22c5",
    # relations
    "le": "\u2264", "leq": "\u2264", "ge": "\u2265", "geq": "\u2265", "ne": "\u2260", "neq": "\u2260",
    "leqslant": "\u2a7d", "geqslant": "\u2a7e", "approx": "\u2248", "approxeq": "\u224a", "sim": "\u223c",
    "simeq": "\u2243", "cong": "\u2245", "equiv": "\u2261", "propto": "\u221d", "ll": "\u226a", "gg": "\u226b",
    "lll": "\u22d8", "ggg": "\u22d9", "lesssim": "\u2272", "gtrsim": "\u2273", "prec": "\u227a", "succ": "\u227b",
    "preceq": "\u2aaf", "succeq": "\u2ab0", "subset": "\u2282", "supset": "\u2283", "subseteq": "\u2286",
    "supseteq": "\u2287", "subsetneq": "\u228a", "supsetneq": "\u228b", "sqsubseteq": "\u2291",
    "sqsupseteq": "\u2292", "in": "\u2208", "notin": "\u2209", "ni": "\u220b", "owns": "\u220b", "perp": "\u22a5",
    "parallel": "\u2225", "nparallel": "\u2226", "mid": "\u2223", "nmid": "\u2224", "vdash": "\u22a2",
    "dashv": "\u22a3", "models": "\u22a8", "asymp": "\u224d", "doteq": "\u2250", "triangleq": "\u225c",
    "coloneqq": "\u2254", "eqqcolon": "\u2255", "bowtie": "\u22c8", "smile": "\u2323", "frown": "\u2322",
    "nless": "\u226e", "ngtr": "\u226f", "nleq": "\u2270", "ngeq": "\u2271", "nsim": "\u2241", "ncong": "\u2247",
    # arrows
    "to": "\u2192", "rightarrow": "\u2192", "leftarrow": "\u2190", "gets": "\u2190", "leftrightarrow": "\u2194",
    "Rightarrow": "\u21d2", "Leftarrow": "\u21d0", "Leftrightarrow": "\u21d4", "implies": "\u27f9",
    "impliedby": "\u27f8", "iff": "\u27fa", "mapsto": "\u21a6", "longmapsto": "\u27fc", "uparrow": "\u2191",
    "downarrow": "\u2193", "updownarrow": "\u2195", "Uparrow": "\u21d1", "Downarrow": "\u21d3",
    "Updownarrow": "\u21d5", "longrightarrow": "\u27f6", "longleftarrow": "\u27f5", "longleftrightarrow": "\u27f7",
    "Longrightarrow": "\u27f9", "Longleftarrow": "\u27f8", "Longleftrightarrow": "\u27fa", "nearrow": "\u2197",
    "searrow": "\u2198", "swarrow": "\u2199", "nwarrow": "\u2196", "hookrightarrow": "\u21aa",
    "hookleftarrow": "\u21a9", "rightleftharpoons": "\u21cc", "leftharpoonup": "\u21bc", "rightharpoonup": "\u21c0",
    "leadsto": "\u21dd",
    # miscellaneous
    "infty": "\u221e", "partial": "\u2202", "nabla": "\u2207", "forall": "\u2200", "exists": "\u2203",
    "nexists": "\u2204", "emptyset": "\u2205", "varnothing": "\u2205", "hbar": "\u210f", "hslash": "\u210f",
    "ell": "\u2113", "Re": "\u211c", "Im": "\u2111", "wp": "\u2118", "aleph": "\u2135", "beth": "\u2136",
    "angle": "\u2220", "measuredangle": "\u2221", "triangle": "\u25b3", "square": "\u25a1", "Box": "\u25a1",
    "blacksquare": "\u25a0", "degree": "\u00b0", "prime": "\u2032", "dprime": "\u2033", "neg": "\u00ac",
    "lnot": "\u00ac", "top": "\u22a4", "bot": "\u22a5", "ldots": "\u2026", "dots": "\u2026", "cdots": "\u22ef",
    "dotsc": "\u2026", "dotsb": "\u22ef", "dotsm": "\u22ef", "vdots": "\u22ee", "ddots": "\u22f1",
    "therefore": "\u2234", "because": "\u2235", "checkmark": "\u2713", "S": "\u00a7", "P": "\u00b6",
    "copyright": "\u00a9", "imath": "\u0131", "jmath": "\u0237", "surd": "\u221a", "flat": "\u266d",
    "natural": "\u266e", "sharp": "\u266f", "clubsuit": "\u2663", "diamondsuit": "\u2662", "heartsuit": "\u2661",
    "spadesuit": "\u2660", "complement": "\u2201", "mho": "\u2127", "backprime": "\u2035", "colon": ":",
    "vert": "|", "Vert": "\u2016", "|": "\u2016", "backslash": "\\", "lbrace": "{", "rbrace": "}",
    "langle": "\u27e8", "rangle": "\u27e9", "lceil": "\u2308", "rceil": "\u2309", "lfloor": "\u230a",
    "rfloor": "\u230b", "lvert": "|", "rvert": "|", "lVert": "\u2016", "rVert": "\u2016", "ulcorner": "\u231c",
    "urcorner": "\u231d", "llcorner": "\u231e", "lrcorner": "\u231f", "lbrack": "[", "rbrack": "]",
    "{": "{", "}": "}", "#": "#", "%": "%", "&": "&", "$": "$", "_": "_",
}

# The characters that may follow \left, \right, \middle or \big etc.
DELIMITERS = {
    "(": "(", ")": ")", "[": "[", "]": "]", "|": "|", "/": "/", "<": "\u27e8", ">": "\u27e9",
    "\\{": "{", "\\}": "}", "\\lbrace": "{", "\\rbrace": "}", "\\langle": "\u27e8", "\\rangle": "\u27e9",
    "\\lceil": "\u2308", "\\rceil": "\u2309", "\\lfloor": "\u230a", "\\rfloor": "\u230b", "\\vert": "|",
    "\\lvert": "|", "\\rvert": "|", "\\|": "\u2016", "\\Vert": "\u2016", "\\lVert": "\u2016", "\\rVert": "\u2016",
    "\\uparrow": "\u2191", "\\downarrow": "\u2193", "\\updownarrow": "\u2195", "\\Uparrow": "\u21d1",
    "\\Downarrow": "\u21d3", "\\backslash": "\\", "\\lbrack": "[", "\\rbrack": "]", ".": "", "\\ulcorner": "\u231c",
    "\\urcorner": "\u231d",
}

# Large operators. The second value says whether limits are placed above/below in display style (as in LaTeX).
NARY = {
    "sum": ("\u2211", True), "prod": ("\u220f", True), "coprod": ("\u2210", True), "int": ("\u222b", False),
    "iint": ("\u222c", False), "iiint": ("\u222d", False), "oint": ("\u222e", False), "oiint": ("\u222f", False),
    "bigcup": ("\u22c3", True), "bigcap": ("\u22c2", True), "bigoplus": ("\u2a01", True),
    "bigotimes": ("\u2a02", True), "bigodot": ("\u2a00", True), "bigvee": ("\u22c1", True),
    "bigwedge": ("\u22c0", True), "biguplus": ("\u2a04", True), "bigsqcup": ("\u2a06", True),
}

# Function names that are written upright. Those in LIMIT_FUNCTIONS take subscripts underneath in display style.
FUNCTIONS = {
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "arccot", "sinh", "cosh", "tanh",
    "coth", "sech", "csch", "log", "ln", "lg", "exp", "det", "dim", "ker", "deg", "gcd", "hom", "arg", "Pr",
    "mod", "sgn", "erf", "Tr", "tr", "rank", "diag", "span", "lcm",
}
LIMIT_FUNCTIONS = {"lim", "liminf", "limsup", "max", "min", "sup", "inf", "argmax", "argmin", "injlim", "projlim"}
FUNCTION_TEXT = {"liminf": "lim\u2006inf", "limsup": "lim\u2006sup", "argmax": "arg\u2006max",
                 "argmin": "arg\u2006min", "injlim": "inj\u2006lim", "projlim": "proj\u2006lim"}

ACCENTS = {
    "hat": "\u0302", "widehat": "\u0302", "tilde": "\u0303", "widetilde": "\u0303", "bar": "\u0305",
    "vec": "\u20d7", "overrightarrow": "\u20d7", "overleftarrow": "\u20d6", "dot": "\u0307", "ddot": "\u0308",
    "dddot": "\u20db", "check": "\u030c", "widecheck": "\u030c", "breve": "\u0306", "acute": "\u0301",
    "grave": "\u0300", "mathring": "\u030a", "overleftrightarrow": "\u20e1",
}

SPACES = {",": "\u2009", "thinspace": "\u2009", ":": "\u205f", ">": "\u205f", "medspace": "\u205f",
          ";": "\u2004", "thickspace": "\u2004", "quad": "\u2003", "qquad": "\u2003\u2003", " ": "\u00a0",
          "\n": "\u00a0", "\t": "\u00a0", "\r": "\u00a0",
          "enspace": "\u2002", "!": "", "negthinspace": "", "negmedspace": "", "negthickspace": ""}

# Font commands: value is (sty, scr) where sty is the OMML style (p, b, i, bi) and scr the script.
FONTS = {
    "mathrm": ("p", None), "mathup": ("p", None), "rm": ("p", None), "mathbf": ("b", None),
    "bf": ("b", None), "mathit": ("i", None), "it": ("i", None), "boldsymbol": ("bi", None), "bm": ("bi", None),
    "mathbfit": ("bi", None), "mathcal": ("p", "script"), "cal": ("p", "script"), "mathscr": ("p", "script"),
    "mathbb": ("p", "double-struck"), "Bbb": ("p", "double-struck"), "mathfrak": ("p", "fraktur"),
    "mathsf": ("p", "sans-serif"), "sf": ("p", "sans-serif"), "mathtt": ("p", "monospace"),
    "tt": ("p", "monospace"),
}

TEXT_COMMANDS = {"text": None, "textrm": None, "mbox": None, "hbox": None, "textnormal": None,
                 "textup": None, "textbf": "b", "textit": "i", "emph": "i", "textsf": None, "texttt": None}

MATRIX_ENVIRONMENTS = {
    "matrix": ("", ""), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"), "Bmatrix": ("{", "}"),
    "vmatrix": ("|", "|"), "Vmatrix": ("\u2016", "\u2016"), "smallmatrix": ("", ""), "array": ("", ""),
    "subarray": ("", ""),
}
ALIGN_ENVIRONMENTS = {"aligned", "align", "align*", "split", "alignat", "alignat*", "alignedat", "eqnarray",
                      "eqnarray*", "flalign", "flalign*"}
GATHER_ENVIRONMENTS = {"gather", "gather*", "gathered", "multline", "multline*", "equation", "equation*",
                       "displaymath", "math"}
CASES_ENVIRONMENTS = {"cases": ("{", ""), "dcases": ("{", ""), "rcases": ("", "}"), "cases*": ("{", "")}

IGNORED_COMMANDS = {"displaystyle", "textstyle", "scriptstyle", "scriptscriptstyle", "nonumber", "notag",
                    "limits", "nolimits", "left.", "relax", "strut", "mathstrut", "allowbreak", "nobreak",
                    "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "Biggl",
                    "Biggr", "bigm", "Bigm", "biggm", "Biggm", "label", "tag", "color", "hspace", "vspace",
                    "kern", "mkern", "mskip", "hskip", "phantom", "hphantom", "vphantom"}

RELATION_CHARS = set("=<>") | {SYMBOLS[k] for k in (
    "le", "ge", "ne", "approx", "sim", "simeq", "cong", "equiv", "propto", "ll", "gg", "subset", "supset",
    "subseteq", "supseteq", "in", "notin", "ni", "to", "rightarrow", "leftarrow", "Rightarrow", "Leftarrow",
    "Leftrightarrow", "leftrightarrow", "implies", "iff", "mapsto", "leqslant", "geqslant", "coloneqq", "doteq",
    "lesssim", "gtrsim", "prec", "succ", "perp", "parallel", "mid", "asymp", "triangleq")}
NARY_STOP_CHARS = RELATION_CHARS | set("+-,;") | {"\u2212", "\u00b1", "\u2213"}

# ----------------------------------------------------------------------------------------------------------------------
#   Tokenizer
# ----------------------------------------------------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"\\([a-zA-Z]+\*?|.)|(%[^\n]*)|(\s+)|(.)", re.DOTALL)


@dataclass
class Token:
    kind: str        # 'cmd', 'char', 'space'
    value: str

    def __repr__(self):
        return f"{self.kind}:{self.value}"


def tokenize(latex: str) -> List[Token]:
    tokens: List[Token] = []
    for m in _TOKEN_RE.finditer(latex):
        cmd, comment, space, char = m.groups()
        if cmd is not None:
            tokens.append(Token("cmd", cmd))
        elif comment is not None:
            continue
        elif space is not None:
            tokens.append(Token("space", space))
        else:
            tokens.append(Token("char", char))
    return tokens


# ----------------------------------------------------------------------------------------------------------------------
#   Output items
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class Item:
    """One element of math output. ``xml`` is the OMML. ``kind`` helps with scripts and operator bodies."""
    xml: str
    kind: str = "ord"            # ord, rel, bin, open, close, nary, func, limfunc, group, align, space, brace
    char: str = ""               # the character for simple single-character items
    data: dict = field(default_factory=dict)


@dataclass
class Style:
    sty: Optional[str] = None    # None means Word's default (italic letters, upright digits)
    scr: Optional[str] = None
    normal_text: bool = False


def _run(text: str, style: Style = Style(), force_sty: Optional[str] = None) -> str:
    props = []
    sty = force_sty or style.sty
    if style.normal_text:
        props.append("<m:nor/>")
    if style.scr:
        props.append(f'<m:scr m:val="{style.scr}"/>')
    if sty:
        props.append(f'<m:sty m:val="{sty}"/>')
    mrpr = f"<m:rPr>{''.join(props)}</m:rPr>" if props else ""
    if style.normal_text:
        bold = "<w:b/>" if sty in ("b", "bi") else ""
        ital = "<w:i/>" if sty in ("i", "bi") else ""
        wrpr = f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>{bold}{ital}</w:rPr>'
    else:
        wrpr = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
    return f'<m:r>{mrpr}{wrpr}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


def _e(content: str, tag: str = "e") -> str:
    return f"<m:{tag}>{content}</m:{tag}>"


def _join(items: Sequence[Item]) -> str:
    return "".join(i.xml for i in items)


# ----------------------------------------------------------------------------------------------------------------------
#   Parser
# ----------------------------------------------------------------------------------------------------------------------

class _Parser:
    def __init__(self, latex: str, display: bool, macros: Optional[Dict[str, Tuple[str, int]]] = None):
        self.display = display
        self.macros = macros or {}
        self.tokens = tokenize(latex)
        self.pos = 0
        self.style_stack: List[Style] = [Style()]
        self.expansions = 0

    # ---------------------------------------------------------------------------------------------- token helpers
    def peek(self, skip_space: bool = True) -> Optional[Token]:
        p = self.pos
        while p < len(self.tokens):
            t = self.tokens[p]
            if skip_space and t.kind == "space":
                p += 1
                continue
            return t
        return None

    def next(self, skip_space: bool = True) -> Optional[Token]:
        while self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            self.pos += 1
            if skip_space and t.kind == "space":
                continue
            return t
        return None

    def expect_char(self, ch: str):
        t = self.next()
        if t is None or t.kind != "char" or t.value != ch:
            raise LatexMathError(f"expected '{ch}' but found {t.value if t else 'end of expression'}")

    @property
    def style(self) -> Style:
        return self.style_stack[-1]

    def read_raw_group(self) -> str:
        """Read a ``{...}`` group (or a single token) and return its raw text without parsing it."""
        t = self.next()
        if t is None:
            raise LatexMathError("missing argument")
        if t.kind == "char" and t.value == "{":
            depth = 1
            parts = []
            while True:
                t = self.next(skip_space=False)
                if t is None:
                    raise LatexMathError("unbalanced braces")
                if t.kind == "char" and t.value == "{":
                    depth += 1
                elif t.kind == "char" and t.value == "}":
                    depth -= 1
                    if depth == 0:
                        break
                parts.append("\\" + t.value if t.kind == "cmd" else t.value)
            return "".join(parts)
        return "\\" + t.value if t.kind == "cmd" else t.value

    def read_optional(self) -> Optional[str]:
        t = self.peek()
        if t is not None and t.kind == "char" and t.value == "[":
            self.next()
            depth = 0
            parts = []
            while True:
                t = self.next(skip_space=False)
                if t is None:
                    raise LatexMathError("unterminated optional argument")
                if t.kind == "char" and t.value == "{":
                    depth += 1
                elif t.kind == "char" and t.value == "}":
                    depth -= 1
                elif t.kind == "char" and t.value == "]" and depth == 0:
                    break
                parts.append("\\" + t.value if t.kind == "cmd" else t.value)
            return "".join(parts)
        return None

    def sub_parse(self, latex: str, style: Optional[Style] = None) -> List[Item]:
        sub = _Parser(latex, self.display, self.macros)
        sub.expansions = self.expansions
        if style is not None:
            sub.style_stack = [style]
        else:
            sub.style_stack = [self.style]
        items = sub.parse_sequence(stop=set())
        if sub.pos < len(sub.tokens) and sub.peek() is not None:
            raise LatexMathError(f"unexpected '{sub.peek().value}'")
        return items

    # ------------------------------------------------------------------------------------------------ main loops
    def parse(self) -> List[Item]:
        items = self.parse_sequence(stop=set())
        t = self.peek()
        if t is not None:
            raise LatexMathError(f"unexpected '{t.value}'")
        return items

    def parse_argument(self) -> List[Item]:
        """Parse one argument: a ``{group}`` or a single token/atom."""
        t = self.peek()
        if t is None:
            raise LatexMathError("missing argument")
        if t.kind == "char" and t.value == "{":
            self.next()
            items = self.parse_sequence(stop={"}"})
            self.expect_char("}")
            return items
        item = self.parse_atom()
        return [item] if item is not None else []

    def parse_sequence(self, stop: set) -> List[Item]:
        """Parse items until one of the stop tokens (char values or '\\\\', '&', 'end', 'right', 'middle')."""
        items: List[Item] = []
        while True:
            t = self.peek()
            if t is None:
                break
            if t.kind == "char" and t.value in stop:
                break
            if t.kind == "cmd" and t.value in stop:
                break
            if t.kind == "char" and t.value == "&" and "&" not in stop:
                self.next()
                items.append(Item(_run("&"), kind="align"))
                continue
            if t.kind == "cmd" and t.value == "\\" and "\\" not in stop:
                raise LatexMathError("line break '\\\\' outside an environment")
            if t.kind == "char" and t.value in "^_":
                self.next()
                base = items.pop() if items else Item("", kind="ord")
                items.append(self.parse_scripts(base, t.value))
                continue
            if t.kind == "char" and t.value == "'":
                primes = ""
                while self.peek(skip_space=False) is not None and self.peek(skip_space=False).value == "'":
                    self.next(skip_space=False)
                    primes += "\u2032"
                primes = {"\u2032\u2032": "\u2033", "\u2032\u2032\u2032": "\u2034"}.get(primes, primes)
                base = items.pop() if items else Item("", kind="ord")
                sup = [Item(_run(primes), kind="ord")]
                # A following ^ merges with the primes, e.g. f'^2
                sub = None
                for _ in range(2):
                    nt = self.peek()
                    if nt is not None and nt.kind == "char" and nt.value == "^":
                        self.next()
                        sup += self.parse_argument()
                    elif nt is not None and nt.kind == "char" and nt.value == "_" and sub is None:
                        self.next()
                        sub = self.parse_argument()
                items.append(self._build_scripts(base, sub, sup))
                continue
            if t.kind == "cmd" and t.value == "over":
                self.next()
                numerator = self._finish_nary(items)
                denominator = self._finish_nary(self.parse_sequence(stop))
                items = [Item(f"<m:f>{_e(_join(numerator), 'num')}{_e(_join(denominator), 'den')}</m:f>")]
                continue
            if t.kind == "cmd" and t.value in ("choose", "atop"):
                self.next()
                numerator = self._finish_nary(items)
                denominator = self._finish_nary(self.parse_sequence(stop))
                frac = (f'<m:f><m:fPr><m:type m:val="noBar"/></m:fPr>{_e(_join(numerator), "num")}'
                        f'{_e(_join(denominator), "den")}</m:f>')
                if t.value == "choose":
                    frac = _delimited(frac, "(", ")")
                items = [Item(frac)]
                continue
            item = self.parse_atom()
            if item is not None:
                items.append(item)
        return self._finish_nary(items)

    # ----------------------------------------------------------------------------------------- operator bodies
    def _finish_nary(self, items: List[Item]) -> List[Item]:
        """Give large operators (sums, integrals) and functions an operand, as Word requires."""
        out: List[Item] = []
        i = 0
        while i < len(items):
            item = items[i]
            if item.kind == "nary" and not item.data.get("done"):
                j = _operand_end(items, i + 1, sums_stop=not item.data.get("integral"))
                body = self._finish_nary(items[i + 1:j])
                out.append(Item(item.data["build"](_join(body)), kind="ord", data={"done": True}))
                i = j
                continue
            if item.kind in ("func", "limfunc") and not item.data.get("done"):
                j = i + 1
                if j < len(items) and items[j].kind in ("nary", "func", "limfunc"):
                    j = _operand_end(items, j)          # e.g. \log\sum_i x_i
                    body = self._finish_nary(items[i + 1:j])
                elif j < len(items) and items[j].char in ("(", "["):
                    depth = 0
                    k = j
                    while k < len(items):
                        if items[k].char in ("(", "["):
                            depth += 1
                        elif items[k].char in (")", "]"):
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    j = min(k + 1, len(items))
                    body = items[i + 1:j]
                elif j < len(items) and items[j].kind not in ("rel", "bin", "align", "close"):
                    j += 1
                    body = items[i + 1:j]
                else:
                    body = []
                out.append(Item(item.data["build"](_join(body)), kind="ord", data={"done": True}))
                i = j
                continue
            out.append(item)
            i += 1
        return out

    # ------------------------------------------------------------------------------------------------- scripts
    def parse_scripts(self, base: Item, first: str) -> Item:
        sub = sup = None
        if first == "_":
            sub = self.parse_argument()
        else:
            sup = self.parse_argument()
        t = self.peek()
        if t is not None and t.kind == "char" and t.value in "^_" and t.value != first:
            self.next()
            if t.value == "_":
                sub = self.parse_argument()
            else:
                sup = self.parse_argument()
        return self._build_scripts(base, sub, sup)

    def _build_scripts(self, base: Item, sub: Optional[List[Item]], sup: Optional[List[Item]]) -> Item:
        subx = _join(self._finish_nary(sub)) if sub is not None else None
        supx = _join(self._finish_nary(sup)) if sup is not None else None
        if base.kind == "nary":
            base.data["sub"] = subx if subx is not None else base.data.get("sub")
            base.data["sup"] = supx if supx is not None else base.data.get("sup")
            return base
        if base.kind == "limfunc":
            name_xml = base.data["name"]
            if base.data.get("undover", self.display):
                if subx is not None:
                    name_xml = f"<m:limLow>{_e(name_xml)}{_e(subx, 'lim')}</m:limLow>"
                if supx is not None:
                    name_xml = f"<m:limUpp>{_e(name_xml)}{_e(supx, 'lim')}</m:limUpp>"
            else:
                name_xml = _scripts_xml(name_xml, subx, supx)
            base.data["name"] = name_xml
            return base
        if base.kind == "func":
            base.data["name"] = _scripts_xml(base.data["name"], subx, supx)
            return base
        if base.kind == "brace":
            xml = base.xml
            if base.data.get("pos") == "top" and supx is not None:
                xml = f"<m:limUpp>{_e(xml)}{_e(supx, 'lim')}</m:limUpp>"
                supx = None
            if base.data.get("pos") == "bot" and subx is not None:
                xml = f"<m:limLow>{_e(xml)}{_e(subx, 'lim')}</m:limLow>"
                subx = None
            return Item(_scripts_xml(xml, subx, supx) if (subx or supx) else xml)
        return Item(_scripts_xml(base.xml, subx, supx), kind="ord")

    # ---------------------------------------------------------------------------------------------------- atoms
    def parse_atom(self) -> Optional[Item]:
        t = self.next()
        if t is None:
            return None
        if t.kind == "char":
            return self.parse_char(t.value)
        return self.parse_command(t.value)

    def parse_char(self, ch: str) -> Optional[Item]:
        if ch == "{":
            items = self.parse_sequence(stop={"}"})
            self.expect_char("}")
            return Item(_join(items), kind="group")
        if ch == "}":
            raise LatexMathError("unbalanced '}'")
        if ch == "~":
            return Item(_run("\u00a0"), kind="space")
        if ch == "$":
            return None
        if ch == "#":
            raise LatexMathError("macro parameter '#' outside a macro")
        text = {"-": "\u2212", "*": "\u2217"}.get(ch, ch)
        kind = "ord"
        if ch in "=<>":
            kind = "rel"
        elif ch in "+-*/":
            kind = "bin"
        elif ch in "([":
            kind = "open"
        elif ch in ")]":
            kind = "close"
        elif ch in ",;":
            kind = "punct"
        return Item(self._styled_run(text), kind=kind, char=ch)

    def _styled_run(self, text: str) -> str:
        style = self.style
        if style.scr in ("script", "fraktur", "double-struck", "sans-serif", "monospace") or style.sty:
            return _run(text, style)
        if text in UPRIGHT_GREEK:
            return _run(text, style, force_sty="p")
        return _run(text, style)

    def parse_command(self, name: str) -> Optional[Item]:
        # user macros first so they can override built-ins
        if name in self.macros:
            return self.expand_macro(name)
        if name in GREEK:
            return Item(self._styled_run(GREEK[name]), kind="ord", char=GREEK[name])
        if name in SYMBOLS:
            ch = SYMBOLS[name]
            kind = "rel" if ch in RELATION_CHARS else ("bin" if ch in NARY_STOP_CHARS else "ord")
            upright = ch.isalpha() and name not in ("ell", "hbar", "hslash", "imath", "jmath", "wp")
            upright = upright or name in ("nabla", "infty", "emptyset", "varnothing", "angle", "degree")
            return Item(_run(ch, force_sty="p" if upright else None), kind=kind, char=ch)
        if name in SPACES:
            sp = SPACES[name]
            return Item(_run(sp), kind="space") if sp else Item("", kind="space")
        if name == "\\":
            raise LatexMathError("line break '\\\\' outside an environment")
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            num = self._finish_nary(self.parse_argument())
            den = self._finish_nary(self.parse_argument())
            return Item(f"<m:f>{_e(_join(num), 'num')}{_e(_join(den), 'den')}</m:f>")
        if name in ("binom", "dbinom", "tbinom"):
            num = self.parse_argument()
            den = self.parse_argument()
            frac = (f'<m:f><m:fPr><m:type m:val="noBar"/></m:fPr>{_e(_join(num), "num")}'
                    f'{_e(_join(den), "den")}</m:f>')
            return Item(_delimited(frac, "(", ")"))
        if name == "sqrt":
            degree = self.read_optional()
            body = self.parse_argument()
            if degree is None:
                return Item(f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>{_e(_join(body))}</m:rad>')
            deg = self.sub_parse(degree)
            return Item(f"<m:rad>{_e(_join(deg), 'deg')}{_e(_join(body))}</m:rad>")
        if name in ACCENTS:
            body = self.parse_argument()
            return Item(f'<m:acc><m:accPr><m:chr m:val="{ACCENTS[name]}"/></m:accPr>{_e(_join(body))}</m:acc>')
        if name in ("overline", "underline"):
            body = self.parse_argument()
            pos = "top" if name == "overline" else "bot"
            return Item(f'<m:bar><m:barPr><m:pos m:val="{pos}"/></m:barPr>{_e(_join(body))}</m:bar>')
        if name in ("overbrace", "underbrace", "overbracket", "underbracket"):
            body = self.parse_argument()
            chars = {"overbrace": ("\u23de", "top"), "underbrace": ("\u23df", "bot"),
                     "overbracket": ("\u23b4", "top"), "underbracket": ("\u23b5", "bot")}
            ch, pos = chars[name]
            vert = "bot" if pos == "top" else "top"
            xml = (f'<m:groupChr><m:groupChrPr><m:chr m:val="{ch}"/><m:pos m:val="{pos}"/>'
                   f'<m:vertJc m:val="{vert}"/></m:groupChrPr>{_e(_join(body))}</m:groupChr>')
            return Item(xml, kind="brace", data={"pos": pos})
        if name in ("overset", "stackrel", "underset"):
            top = self.parse_argument()
            body = self.parse_argument()
            tag = "limLow" if name == "underset" else "limUpp"
            inner = _join(body)
            kind = "rel" if len(body) == 1 and body[0].kind == "rel" else "ord"
            return Item(f"<m:{tag}>{_e(inner)}{_e(_join(top), 'lim')}</m:{tag}>", kind=kind)
        if name in ("xrightarrow", "xleftarrow"):
            below = self.read_optional()
            above = self.parse_argument()
            arrow = "\u2192" if name == "xrightarrow" else "\u2190"
            xml = (f'<m:groupChr><m:groupChrPr><m:chr m:val="{arrow}"/><m:pos m:val="top"/>'
                   f'<m:vertJc m:val="bot"/></m:groupChrPr>{_e(_join(above))}</m:groupChr>')
            if below:
                xml = f"<m:limLow>{_e(xml)}{_e(_join(self.sub_parse(below)), 'lim')}</m:limLow>"
            return Item(xml, kind="rel")
        if name in ("boxed", "fbox"):
            body = self.parse_argument() if name == "boxed" else self.text_argument()
            return Item(f"<m:borderBox>{_e(_join(body))}</m:borderBox>")
        if name in ("cancel", "bcancel", "xcancel", "sout"):
            body = self.parse_argument()
            strikes = {"cancel": '<m:strikeBLTR m:val="1"/>', "bcancel": '<m:strikeTLBR m:val="1"/>',
                       "xcancel": '<m:strikeBLTR m:val="1"/><m:strikeTLBR m:val="1"/>',
                       "sout": '<m:strikeH m:val="1"/>'}[name]
            return Item(f'<m:borderBox><m:borderBoxPr><m:hideTop m:val="1"/><m:hideBot m:val="1"/>'
                        f'<m:hideLeft m:val="1"/><m:hideRight m:val="1"/>{strikes}</m:borderBoxPr>'
                        f'{_e(_join(body))}</m:borderBox>')
        if name in ("phantom", "hphantom", "vphantom"):
            body = self.parse_argument()
            return Item(f'<m:phant><m:phantPr><m:show m:val="0"/></m:phantPr>{_e(_join(body))}</m:phant>')
        if name in ("left",):
            return self.parse_left_right()
        if name in ("right", "middle"):
            raise LatexMathError(f"\\{name} without matching \\left")
        if name in ("big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "Biggl",
                    "Biggr", "bigm", "Bigm", "biggm", "Biggm"):
            delim = self.read_delimiter()
            kind = "open" if name.endswith("l") else ("close" if name.endswith("r") else "ord")
            return Item(_run(delim), kind=kind, char=delim)
        if name in NARY:
            ch, undover = NARY[name]
            limits = self._read_limits_modifier()
            if limits is not None:
                undover = limits
            loc = "undOvr" if (undover and self.display) else "subSup"
            item = Item("", kind="nary", data={"integral": "int" in name})

            def build(body_xml, item=item, ch=ch, loc=loc):
                sub = item.data.get("sub")
                sup = item.data.get("sup")
                pr = f'<m:chr m:val="{ch}"/><m:limLoc m:val="{loc}"/>'
                if sub is None:
                    pr += '<m:subHide m:val="1"/>'
                if sup is None:
                    pr += '<m:supHide m:val="1"/>'
                return (f"<m:nary><m:naryPr>{pr}</m:naryPr>{_e(sub or '', 'sub')}{_e(sup or '', 'sup')}"
                        f"{_e(body_xml)}</m:nary>")
            item.data["build"] = build
            return item
        if name in FUNCTIONS or name in LIMIT_FUNCTIONS or name in ("operatorname", "operatorname*"):
            if name.startswith("operatorname"):
                text = self.read_raw_group().replace("\\,", "\u2009").replace("\\ ", " ")
                text = re.sub(r"\\([a-zA-Z]+)", lambda m: GREEK.get(m.group(1), m.group(1)), text)
                text = text.replace("{", "").replace("}", "")
                is_limit = name.endswith("*")
            else:
                text = FUNCTION_TEXT.get(name, name)
                is_limit = name in LIMIT_FUNCTIONS
            limits = self._read_limits_modifier()
            item = Item("", kind="limfunc" if is_limit else "func")
            item.data["name"] = _run(text, Style(), force_sty="p")
            if limits is not None:
                item.data["undover"] = limits

            def build(body_xml, item=item):
                return f"<m:func>{_e(item.data['name'], 'fName')}{_e(body_xml)}</m:func>"
            item.data["build"] = build
            return item
        if name in FONTS:
            sty, scr = FONTS[name]
            t = self.peek()
            if name in ("rm", "bf", "it", "sf", "tt", "cal"):   # old-style switches apply to the rest
                self.style_stack[-1] = Style(sty=sty, scr=scr)
                return None
            self.style_stack.append(Style(sty=sty, scr=scr))
            try:
                body = self.parse_argument()
            finally:
                self.style_stack.pop()
            return Item(_join(body), kind="ord")
        if name in TEXT_COMMANDS:
            return Item(_join(self.text_argument(TEXT_COMMANDS[name])), kind="ord")
        if name in ("mathop", "mathord", "mathbin", "mathrel", "mathpunct", "mathinner", "mathopen",
                    "mathclose", "mathchoice", "smash", "mathclap", "mathllap", "mathrlap", "clap", "llap",
                    "rlap", "ensuremath"):
            body = self.parse_argument()
            kind = {"mathrel": "rel", "mathbin": "bin"}.get(name, "ord")
            return Item(_join(body), kind=kind)
        if name == "not":
            nxt = self.parse_atom()
            if nxt is None or not nxt.char:
                raise LatexMathError("\\not must be followed by a symbol")
            negated = {"=": "\u2260", "<": "\u226e", ">": "\u226f", "\u2208": "\u2209", "\u2264": "\u2270",
                       "\u2265": "\u2271", "\u2261": "\u2262", "\u223c": "\u2241", "\u2282": "\u2284",
                       "\u2283": "\u2285", "\u2286": "\u2288", "\u2287": "\u2289"}.get(nxt.char, nxt.char + "\u0338")
            return Item(_run(negated), kind="rel", char=negated)
        if name in ("pmod", "bmod", "mod", "pod"):
            if name == "bmod":
                return Item(_run("mod", force_sty="p"), kind="bin")
            arg = self.parse_argument()
            word = "" if name == "pod" else "mod\u2006"
            return Item(_run("\u2003(" + word, force_sty="p") + _join(arg) + _run(")", force_sty="p"))
        if name == "begin":
            return self.parse_environment()
        if name == "end":
            raise LatexMathError("\\end without matching \\begin")
        if name in ("label", "tag", "tag*", "hspace", "hspace*", "vspace", "vspace*", "color", "textcolor",
                    "mkern", "kern", "mskip", "hskip"):
            if name in ("hspace", "hspace*", "kern", "mkern", "mskip", "hskip"):
                arg = self.read_raw_group()
                return Item(_run("\u2009"), kind="space") if not arg.strip().startswith("-") else None
            if name == "textcolor":
                self.read_raw_group()
                return Item(_join(self.parse_argument()))
            self.read_raw_group()
            return None
        if name in IGNORED_COMMANDS:
            return None
        if name in ("dots", "ldots"):
            return Item(_run("\u2026"))
        raise LatexMathError(f"unsupported command \\{name}")

    def _read_limits_modifier(self) -> Optional[bool]:
        t = self.peek()
        if t is not None and t.kind == "cmd" and t.value in ("limits", "nolimits"):
            self.next()
            return t.value == "limits"
        return None

    def text_argument(self, sty: Optional[str] = None) -> List[Item]:
        """Read the argument of \\text{...} as normal (non-math) text, allowing nested $...$ math."""
        raw = self.read_raw_group()
        items: List[Item] = []
        for i, part in enumerate(re.split(r"(?<!\\)\$", raw)):
            if i % 2 == 1:
                items.extend(self.sub_parse(part, Style()))
            elif part:
                text = re.sub(r"\\([{}%&$#_ ])", r"\1", part)
                text = text.replace("~", "\u00a0").replace("\\,", "\u2009").replace("--", "\u2013")
                text = re.sub(r"\\([a-zA-Z]+)\s*", lambda m: SYMBOLS.get(m.group(1), GREEK.get(m.group(1), "")),
                              text)
                items.append(Item(_run(text, Style(sty=sty or "p", normal_text=True))))
        return items

    def expand_macro(self, name: str) -> Optional[Item]:
        self.expansions += 1
        if self.expansions > 1000:
            raise LatexMathError(f"macro \\{name} expands recursively")
        body, nargs = self.macros[name]
        args = [self.read_raw_group() for _ in range(nargs)]
        for i, arg in enumerate(args):
            body = body.replace(f"#{i + 1}", arg)
        # Splice the expansion back into the token stream so scripts etc. attach correctly.
        self.tokens[self.pos:self.pos] = [Token("char", "{")] + tokenize(body) + [Token("char", "}")]
        return self.parse_atom()

    # ------------------------------------------------------------------------------------------- delimiters
    def read_delimiter(self) -> str:
        t = self.next()
        if t is None:
            raise LatexMathError("missing delimiter")
        key = t.value if t.kind == "char" else "\\" + t.value
        if key not in DELIMITERS:
            raise LatexMathError(f"unknown delimiter {key}")
        return DELIMITERS[key]

    def parse_left_right(self) -> Item:
        begin = self.read_delimiter()
        parts: List[List[Item]] = []
        seps: List[str] = []
        while True:
            items = self.parse_sequence(stop={"right", "middle"})
            parts.append(items)
            t = self.next()
            if t is None:
                raise LatexMathError("\\left without matching \\right")
            if t.value == "middle":
                seps.append(self.read_delimiter())
                continue
            end = self.read_delimiter()
            break
        pr = f'<m:begChr m:val="{escape(begin, {chr(34): "&quot;"})}"/>'
        if seps:
            pr += f'<m:sepChr m:val="{escape(seps[0])}"/>'
        pr += f'<m:endChr m:val="{escape(end)}"/>'
        body = "".join(_e(_join(p)) for p in parts)
        return Item(f"<m:d><m:dPr>{pr}</m:dPr>{body}</m:d>", kind="ord")

    # ---------------------------------------------------------------------------------------- environments
    def parse_environment(self) -> Item:
        env = self.read_raw_group().strip()
        colspec = None
        if env in ("array", "subarray", "alignat", "alignat*", "alignedat"):
            colspec = self.read_raw_group()
        elif env in MATRIX_ENVIRONMENTS or env in CASES_ENVIRONMENTS:
            self.read_optional()   # e.g. pmatrix*[r]
        rows = self.parse_rows(env)
        if env in MATRIX_ENVIRONMENTS:
            left, right = MATRIX_ENVIRONMENTS[env]
            aligns = _colspec_aligns(colspec) if env in ("array", "subarray") and colspec else None
            xml = _matrix(rows, aligns)
            if left or right:
                xml = _delimited(xml, left, right)
            return Item(xml)
        if env in CASES_ENVIRONMENTS:
            left, right = CASES_ENVIRONMENTS[env]
            return Item(_delimited(_matrix(rows, ["left"] * 8, col_gap=True), left, right))
        if env in ALIGN_ENVIRONMENTS:
            return Item(_eqarray(rows, with_align=True))
        if env in GATHER_ENVIRONMENTS:
            return Item(_eqarray(rows, with_align=False))
        raise LatexMathError(f"unsupported environment {env}")

    def parse_rows(self, env: str) -> List[List[List[Item]]]:
        """Parse rows and cells until ``\\end{env}``. Returns rows -> cells -> items."""
        rows: List[List[List[Item]]] = []
        cells: List[List[Item]] = []
        while True:
            items = self.parse_sequence(stop={"&", "\\", "end", "cr"})
            cells.append(items)
            t = self.next()
            if t is None:
                raise LatexMathError(f"missing \\end{{{env}}}")
            if t.value == "&":
                continue
            if t.value in ("\\", "cr"):
                self.read_optional()   # \\[2pt]
                rows.append(cells)
                cells = []
                continue
            if t.value == "end":
                name = self.read_raw_group().strip()
                if name != env:
                    raise LatexMathError(f"\\begin{{{env}}} ended by \\end{{{name}}}")
                rows.append(cells)
                break
        # drop a trailing empty row produced by a final \\
        if len(rows) > 1 and all(not c for c in rows[-1]):
            rows.pop()
        return rows


def _operand_end(items: List[Item], start: int, sums_stop: bool = True) -> int:
    r"""
    Index one past the operand of a large operator: up to the next relation (and, for sums and products, the
    next + or -) at bracket depth 0. An integral runs to the next relation so that ``\int a + b\,dx`` keeps
    ``a + b`` under the integral sign.
    """
    depth = 0
    j = start
    while j < len(items):
        item = items[j]
        if item.kind == "open":
            depth += 1
        elif item.kind == "close":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and _stops_nary(item) and (sums_stop or item.kind != "bin"):
            break
        j += 1
    return j


def _stops_nary(item: Item) -> bool:
    if item.kind in ("rel", "align", "close", "punct"):
        return True
    if item.kind == "bin" and item.char in ("+", "-", "\u2212", "\u00b1", "\u2213"):
        return True
    return False


def _scripts_xml(base: str, sub: Optional[str], sup: Optional[str]) -> str:
    if sub is not None and sup is not None:
        return f"<m:sSubSup>{_e(base)}{_e(sub, 'sub')}{_e(sup, 'sup')}</m:sSubSup>"
    if sub is not None:
        return f"<m:sSub>{_e(base)}{_e(sub, 'sub')}</m:sSub>"
    if sup is not None:
        return f"<m:sSup>{_e(base)}{_e(sup, 'sup')}</m:sSup>"
    return base


def _delimited(inner_xml: str, left: str, right: str) -> str:
    return (f'<m:d><m:dPr><m:begChr m:val="{escape(left)}"/><m:endChr m:val="{escape(right)}"/></m:dPr>'
            f"{_e(inner_xml)}</m:d>")


def _colspec_aligns(spec: str) -> List[str]:
    out = []
    for ch in spec:
        if ch in "lcr":
            out.append({"l": "left", "c": "center", "r": "right"}[ch])
    return out


def _matrix(rows: List[List[List[Item]]], aligns: Optional[List[str]] = None, col_gap: bool = False) -> str:
    ncols = max(len(r) for r in rows) if rows else 1
    mcs = ""
    for c in range(ncols):
        jc = aligns[c] if aligns and c < len(aligns) else "center"
        mcs += f'<m:mc><m:mcPr><m:count m:val="1"/><m:mcJc m:val="{jc}"/></m:mcPr></m:mc>'
    gap = '<m:cGpRule m:val="3"/><m:cGp m:val="360"/>' if col_gap else ""
    pr = f'<m:mPr><m:baseJc m:val="center"/><m:plcHide m:val="1"/>{gap}<m:mcs>{mcs}</m:mcs></m:mPr>'
    body = ""
    for r in rows:
        cells = list(r) + [[] for _ in range(ncols - len(r))]
        body += "<m:mr>" + "".join(_e(_join(c)) for c in cells) + "</m:mr>"
    return f"<m:m>{pr}{body}</m:m>"


def _eqarray(rows: List[List[List[Item]]], with_align: bool) -> str:
    body = ""
    for r in rows:
        if with_align:
            parts = []
            for i, cell in enumerate(r):
                if i > 0:
                    parts.append(_run("&"))
                parts.append(_join(cell))
            body += _e("".join(parts))
        else:
            body += _e("".join(_join(c) for c in r))
    return f'<m:eqArr><m:eqArrPr><m:baseJc m:val="center"/></m:eqArrPr>{body}</m:eqArr>'


# ----------------------------------------------------------------------------------------------------------------------
#   Public API
# ----------------------------------------------------------------------------------------------------------------------

def _has_top_level_linebreak(latex: str) -> bool:
    depth = 0
    for t in tokenize(latex):
        if t.kind == "cmd" and t.value == "begin":
            depth += 1
        elif t.kind == "cmd" and t.value == "end":
            depth -= 1
        elif t.kind == "cmd" and t.value == "\\" and depth == 0:
            return True
    return False


def _has_top_level_ampersand(latex: str) -> bool:
    depth = 0
    for t in tokenize(latex):
        if t.kind == "cmd" and t.value == "begin":
            depth += 1
        elif t.kind == "cmd" and t.value == "end":
            depth -= 1
        elif t.kind == "char" and t.value == "&" and depth == 0:
            return True
    return False


def split_display_math(latex: str) -> List[str]:
    """Split a math block into equations on blank lines, as Sphinx does for ``.. math::`` content."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", latex.strip())]
    return [p for p in parts if p]


def latex_to_omml_items(latex: str, display: bool,
                        macros: Optional[Dict[str, Tuple[str, int]]] = None) -> str:
    """Convert one LaTeX equation into the OMML content of an ``<m:oMath>`` element (without the element)."""
    latex = latex.strip()
    # Strip a surrounding $...$, \(...\) or \[...\] if someone included it.
    for a, b in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if latex.startswith(a) and latex.endswith(b) and len(latex) > len(a) + len(b):
            latex = latex[len(a):-len(b)].strip()
            break
    if _has_top_level_linebreak(latex) or (display and _has_top_level_ampersand(latex)):
        # Sphinx wraps such blocks in \begin{split}...\end{split}; do the same.
        latex = "\\begin{aligned}" + latex + "\\end{aligned}"
    parser = _Parser(latex, display, macros)
    return _join(parser.parse())


def latex_to_omml(latex: str, display: bool = False,
                  macros: Optional[Dict[str, Tuple[str, int]]] = None) -> str:
    """
    Convert LaTeX to OMML.

    Parameters
    ----------
    latex:
        The LaTeX source without surrounding ``$``.
    display:
        ``True`` for display equations (returns ``<m:oMathPara>``), ``False`` for inline math (``<m:oMath>``).
    macros:
        Optional user macros, name -> (replacement, number of arguments), as in MathJax configuration.
    """
    if not display:
        return f"<m:oMath>{latex_to_omml_items(latex, False, macros)}</m:oMath>"
    equations = split_display_math(latex) or [""]
    if len(equations) == 1:
        body = latex_to_omml_items(equations[0], True, macros)
    else:
        # Several equations in one block (separated by blank lines) are stacked, one per line, like gather.
        rows = "".join(f"<m:e>{latex_to_omml_items(eq, True, macros)}</m:e>" for eq in equations)
        body = f'<m:eqArr><m:eqArrPr><m:baseJc m:val="center"/></m:eqArrPr>{rows}</m:eqArr>'
    return (f'<m:oMathPara><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr><m:oMath>{body}</m:oMath>'
            '</m:oMathPara>')


def parse_mathjax_macros(config_macros: Dict) -> Dict[str, Tuple[str, int]]:
    """Convert MathJax style macro definitions (``{'R': '\\\\mathbb{R}', 'v': ['\\\\mathbf{#1}', 1]}``)."""
    out: Dict[str, Tuple[str, int]] = {}
    for name, value in (config_macros or {}).items():
        if isinstance(value, (list, tuple)):
            out[name] = (str(value[0]), int(value[1]) if len(value) > 1 else 0)
        else:
            out[name] = (str(value), 0)
    return out


# Characters that get a space on each side when inline math is written as text (relations and binary operators).
_SPACED_RELATIONS = set("=<>≤≥≈≠≡∝→←⇒⇔∈∉⊂⊃")
_SPACED_BINARY = set("+−×±∓·÷")


def omml_as_text(omml: str) -> Optional[List[Tuple[str, Dict[str, object]]]]:
    r"""
    Write simple inline math as formatted text, if it can be.

    Word copies the text of a caption into the table of figures when it updates the field, but it flattens the
    structure of equations: :math:`\chi^2` in a caption appears as "χ2" in the list. Text runs keep their
    character formatting, so math that is only letters, digits, symbols and sub- and superscripts is better written
    as text in captions: letters in italics (unless the math makes them upright or bold), scripts as subscript or
    superscript text, and spaces around relations and binary operators.

    Parameters
    ----------
    omml:
        An ``<m:oMath>`` element as made by :func:`latex_to_omml` for inline math.

    Returns
    -------
    list of (text, format) or None
        The pieces of text with their format: ``{"italic": True}``, ``{"bold": True}`` and
        ``{"vert": "superscript"}`` or ``{"vert": "subscript"}``. ``None`` if the math has anything else, such as a
        fraction, a root or a delimiter, so it must stay an equation.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(f'<root xmlns:m="{M_NS}" xmlns:w="{W_NS}">{omml}</root>')
    except ET.ParseError:
        return None
    m = "{%s}" % M_NS
    w = "{%s}" % W_NS
    math = root.find(f"{m}oMath")
    if math is None or len(root) != 1:
        return None

    def run_pieces(run, vert: Optional[str]) -> List[Tuple[str, Dict[str, object]]]:
        sty = None
        for child in run:
            if child.tag == f"{m}rPr":
                for prop in child:
                    if prop.tag == f"{m}sty":
                        sty = prop.get(f"{m}val")
                    elif prop.tag != f"{m}nor":
                        raise ValueError(prop.tag)
            elif child.tag not in (f"{m}t", f"{w}rPr"):
                raise ValueError(child.tag)
        text = "".join(t.text or "" for t in run.findall(f"{m}t"))
        pieces = []
        for ch in text:
            fmt: Dict[str, object] = {}
            if sty in ("b", "bi"):
                fmt["bold"] = True
            if ch.isalpha() and sty not in ("p", "b"):
                fmt["italic"] = True
            if vert:
                fmt["vert"] = vert
            pieces.append((ch, fmt))
        return pieces

    def runs_only(element, vert: Optional[str]) -> List[Tuple[str, Dict[str, object]]]:
        pieces = []
        for child in element:
            if child.tag == f"{m}r":
                pieces.extend(run_pieces(child, vert))
            elif child.tag != f"{m}ctrlPr":
                raise ValueError(child.tag)
        return pieces

    pieces: List[Tuple[str, Dict[str, object]]] = []
    try:
        for child in math:
            if child.tag == f"{m}r":
                pieces.extend(run_pieces(child, None))
            elif child.tag in (f"{m}sSup", f"{m}sSub", f"{m}sSubSup"):
                parts = {part.tag: part for part in child}
                if set(parts) - {f"{m}e", f"{m}sub", f"{m}sup", f"{m}sSupPr", f"{m}sSubPr", f"{m}sSubSupPr"}:
                    return None
                pieces.extend(runs_only(parts[f"{m}e"], None))
                if f"{m}sub" in parts:
                    pieces.extend(runs_only(parts[f"{m}sub"], "subscript"))
                if f"{m}sup" in parts:
                    pieces.extend(runs_only(parts[f"{m}sup"], "superscript"))
            else:
                return None
    except (ValueError, KeyError):
        return None

    # Spaces around relations and binary operators at the base line, as Word puts them in an equation. A minus or
    # plus at the start, or after another operator or an opening bracket, is a sign and gets no space.
    out: List[Tuple[str, Dict[str, object]]] = []
    for i, (ch, fmt) in enumerate(pieces):
        if not fmt.get("vert") and (ch in _SPACED_RELATIONS or ch in _SPACED_BINARY):
            prev = out[-1][0].strip() if out else ""
            unary = ch in _SPACED_BINARY and (not prev or prev in _SPACED_RELATIONS or prev in _SPACED_BINARY
                                              or prev in "([{")
            if not unary:
                if out and not out[-1][0].endswith(" "):
                    out.append((" ", {}))
                out.append((ch, fmt))
                out.append((" ", {}))
                continue
        if ch == " " and out and out[-1][0] == " ":
            continue
        out.append((ch, fmt))
    # Merge neighbouring pieces with the same format into one run.
    merged: List[Tuple[str, Dict[str, object]]] = []
    for text, fmt in out:
        if merged and merged[-1][1] == fmt:
            merged[-1] = (merged[-1][0] + text, fmt)
        else:
            merged.append((text, fmt))
    return merged

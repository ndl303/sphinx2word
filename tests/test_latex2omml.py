"""Tests of the LaTeX to OMML converter."""

import xml.etree.ElementTree as ET

import pytest

from sphinx2word.latex2omml import LatexMathError, latex_to_omml, omml_as_text

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
WRAP = ('<root xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{}</root>')


def parse(latex, display=False, macros=None):
    xml = latex_to_omml(latex, display, macros)
    return ET.fromstring(WRAP.format(xml))


def tags(root):
    return [el.tag.replace(M, "m:") for el in root.iter() if el.tag.startswith(M)]


def text(root):
    return "".join(t.text or "" for t in root.iter(M + "t"))


# Expressions taken from real Sphinx documents; each must convert to well formed OMML.
CORPUS = [
    r"10^{-14}", r"1.2\times10^{-6}", r"(y+0.5, x+0.5)", r"m \le 9", r"\pm 30", r"T_1, T_2, T_3",
    r"\frac{1}{2L^2}\left( T_1 - 2T_2 + T_3\right)y^2 + \frac{1}{2L}\left(T_3 - T_1\right)y + T_2",
    r"\Phi_{\lambda}(\mathbf{X_i}) = \sum_{X'_y}\sum_{X'_x} I_{\lambda}(\mathbf{X'})\, A''(\mathbf{X'},\mathbf{X_i})",
    r"\boxed{\boldsymbol{B} = \boldsymbol{A}\,\boldsymbol{T}}",
    r"\int_{y_j}^{y_j+1} ay^2 + by + c \;\mathrm{d}y = ay_j^2 + (a+b)y_j + \left(\frac{a}{3} + \frac{b}{2} + c\right)",
    r"b(\boldsymbol{d}) = \sum_{\boldsymbol{s}\,\in\,\mathrm{window}} P_{\boldsymbol{s}}(\boldsymbol{d})\, t(\boldsymbol{s})",
    r"\mathcal{D}_k", r"\mathbb{R}^n", r"\hat{x} \bar{y} \tilde{z} \vec{v} \dot{q} \ddot{q}",
    r"\overline{AB} \underline{x}", r"\sqrt{x} \sqrt[3]{x}", r"\binom{n}{k}", r"\operatorname{sinc}(x)",
    r"\lim_{n\to\infty} a_n", r"\max_{k} |a_k|", r"\sin^2\theta + \cos^2\theta = 1", r"\log_{10} x",
    r"\left\| x \right\|_2", r"\left\langle a, b \right\rangle", r"\left. \frac{df}{dx} \right|_{x=0}",
    r"\left( \frac{a}{b} \middle| c \right)", r"\{ x : x > 0 \}", r"a \bmod b", r"a \pmod{n}",
    r"\underbrace{a+b+c}_{\text{three}}", r"\overbrace{x+y}^{n}", r"\overset{!}{=}", r"\stackrel{def}{=}",
    r"\text{if } x > 0 \text{ and $y$ small}", r"\mathrm{d}x\,\mathrm{d}y", r"\nabla \cdot \mathbf{E}",
    r"\partial_t u = \Delta u", r"f'(x) + f''(x)", r"x^{y^{z}}", r"{a \over b}", r"{n \choose k}",
    r"\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}", r"\begin{bmatrix} a \\ b \end{bmatrix}",
    r"\begin{vmatrix} a & b \\ c & d \end{vmatrix}", r"\begin{array}{lcr} a & b & c \\ d & e & f \end{array}",
    r"f(x) = \begin{cases} 1 & x > 0 \\ 0 & \text{otherwise} \end{cases}",
    r"\begin{aligned} a &= b \\ c &= d \end{aligned}", r"\alpha\beta\gamma\Gamma\Delta\varepsilon\varphi",
    r"\iint_D f \, dA", r"\oint_C \vec{F}\cdot d\vec{r}", r"\prod_{i=1}^{n} x_i", r"\bigcup_{i} A_i",
    r"x \in A \setminus B", r"a \neq b \approx c \equiv d", r"\not\in", r"A \Rightarrow B \iff C",
    r"\dots \cdots \ldots \vdots \ddots", r"\mathbf{x}^T \mathbf{A}^{-1}", r"e^{-2\pi i (u x + v y)}",
    r"\quad\qquad\,\;\:\!", r"x_{i,j}^{(k)}", r"\cancel{x}", r"\phantom{x}", r"\color{red}{x}",
    r"\left[ 0, 1 \right)", r"\lfloor x \rfloor \lceil y \rceil", r"\xrightarrow{f} B",
]


@pytest.mark.parametrize("latex", CORPUS)
@pytest.mark.parametrize("display", [False, True])
def test_corpus_is_well_formed(latex, display):
    root = parse(latex, display)
    assert root.find(".//" + M + "oMath") is not None


def test_fraction():
    root = parse(r"\frac{a}{b}")
    f = root.find(".//" + M + "f")
    assert text(f.find(M + "num")) == "a"
    assert text(f.find(M + "den")) == "b"


def test_sum_limits_display_and_inline():
    display = parse(r"\sum_{i=1}^{N} x_i", True)
    inline = parse(r"\sum_{i=1}^{N} x_i", False)
    assert display.find(".//" + M + "limLoc").get(M + "val") == "undOvr"
    assert inline.find(".//" + M + "limLoc").get(M + "val") == "subSup"
    nary = display.find(".//" + M + "nary")
    assert text(nary.find(M + "sub")) == "i=1"
    assert text(nary.find(M + "sup")) == "N"
    assert text(nary.find(M + "e")) == "xi"


def test_sum_operand_stops_at_plus_but_integral_does_not():
    s = parse(r"\sum_i a_i + b", True).find(".//" + M + "nary")
    assert text(s.find(M + "e")) == "ai"
    i = parse(r"\int_0^1 a + b \, dx = 1", True).find(".//" + M + "nary")
    assert "+" in text(i.find(M + "e")) and "dx" in text(i.find(M + "e")).replace(" ", "")
    assert "=" not in text(i.find(M + "e"))


def test_operand_includes_matched_brackets():
    nary = parse(r"\int T(y)\,dy = 1", True).find(".//" + M + "nary")
    assert text(nary.find(M + "e")).replace(" ", "") == "T(y)dy"


def test_aligned_rows_use_alignment_marks():
    root = parse("y_1 &= -L \\\\\n y_2 &= 0 \\\\\n y_3 &= +L", True)
    arr = root.find(".//" + M + "eqArr")
    rows = arr.findall(M + "e")
    assert len(rows) == 3
    for row in rows:
        assert [t.text for t in row.iter(M + "t")].count("&") == 1


def test_blank_line_separates_equations():
    root = parse("a = b\n\nc = d", True)
    rows = root.find(".//" + M + "eqArr").findall(M + "e")
    assert [text(r) for r in rows] == ["a=b", "c=d"]


def test_matrix_and_delimiters():
    root = parse(r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}")
    d = root.find(".//" + M + "d")
    assert d.find(".//" + M + "begChr").get(M + "val") == "["
    m = d.find(".//" + M + "m")
    assert len(m.findall(M + "mr")) == 2
    assert len(m.find(M + "mr").findall(M + "e")) == 2


def test_left_right_and_middle():
    d = parse(r"\left( a \middle| b \right]").find(".//" + M + "d")
    pr = d.find(M + "dPr")
    assert pr.find(M + "begChr").get(M + "val") == "("
    assert pr.find(M + "sepChr").get(M + "val") == "|"
    assert pr.find(M + "endChr").get(M + "val") == "]"
    assert len(d.findall(M + "e")) == 2


def test_fonts_and_text():
    root = parse(r"\mathrm{d}x \mathbf{A} \text{word}")
    runs = list(root.iter(M + "r"))
    styles = [(r.find(M + "rPr/" + M + "sty").get(M + "val") if r.find(M + "rPr/" + M + "sty") is not None
               else None) for r in runs]
    assert styles[0] == "p" and styles[2] == "b"
    assert runs[3].find(M + "rPr/" + M + "nor") is not None


def test_functions_are_upright():
    func = parse(r"\sin x").find(".//" + M + "func")
    assert text(func.find(M + "fName")) == "sin"
    assert func.find(".//" + M + "sty").get(M + "val") == "p"


def test_prime_with_subscript():
    root = parse(r"X'_y")
    sss = root.find(".//" + M + "sSubSup")
    assert text(sss.find(M + "sub")) == "y" and text(sss.find(M + "sup")) == "′"


def test_macros():
    macros = {"vect": (r"\mathbf{#1}", 1), "RR": (r"\mathbb{R}", 0)}
    root = parse(r"\vect{x} \in \RR^3", macros=macros)
    assert root.find(".//" + M + "sSup") is not None
    assert any(s.get(M + "val") == "double-struck" for s in root.iter(M + "scr"))


@pytest.mark.parametrize("bad", [r"\frac{a}", r"\left( a", r"\begin{pmatrix} a", r"\unknowncommand",
                                 r"a^", r"\end{matrix}", r"}", r"\right)"])
def test_errors_are_reported(bad):
    with pytest.raises(LatexMathError):
        latex_to_omml(bad)


# Simple inline math in captions is written as text, because Word flattens equations in the table of figures.
def as_text(latex):
    return omml_as_text(latex_to_omml(latex))


def test_caption_math_as_text_scripts():
    assert as_text(r"\chi^2") == [("χ", {"italic": True}), ("2", {"vert": "superscript"})]
    assert as_text(r"b_0") == [("b", {"italic": True}), ("0", {"vert": "subscript"})]
    assert as_text(r"x_i^2") == [("x", {"italic": True}), ("i", {"italic": True, "vert": "subscript"}),
                                 ("2", {"vert": "superscript"})]
    assert as_text(r"10^{-14}") == [("10", {}), ("−14", {"vert": "superscript"})]


def test_caption_math_as_text_styles_and_spacing():
    assert as_text(r"\Delta T") == [("Δ", {}), ("T", {"italic": True})]
    assert as_text(r"\mathbf{A}") == [("A", {"bold": True})]
    assert "".join(t for t, _ in as_text(r"\lambda = 550\,\mathrm{nm}")) == "λ = 550\u2009nm"
    assert "".join(t for t, _ in as_text(r"a+b")) == "a + b"
    assert "".join(t for t, _ in as_text(r"x = -1")) == "x = −1"     # a sign gets no space
    assert "".join(t for t, _ in as_text(r"-x")) == "−x"


@pytest.mark.parametrize("latex", [r"\frac{a}{b}", r"\sqrt{2}", r"\left( x \right)", r"\sum_i x_i",
                                   r"x^{a_b}", r"\begin{matrix} a \end{matrix}"])
def test_caption_math_stays_an_equation(latex):
    assert as_text(latex) is None

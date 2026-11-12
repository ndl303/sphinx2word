# Math

Math from the `:math:` role and the `.. math::` directive becomes native Word equations (Office Math, OMML). In
Word they are ordinary equations: they can be edited with the equation editor and they scale with the text.

The converter (`sphinx2word/latex2omml.py`) reads the LaTeX itself. Earlier versions of sphinx2word typed the
LaTeX into Word and asked Word to "build up" the equation. Word's own parser only understands part of LaTeX, which
is why multi-line equations and column vectors used to come out wrong.

## Inline, display and numbered equations

- **Inline math,** `` :math:`E = mc^2` ``, is an equation within the line of text.
- **Math in captions.** When Word fills in a list of figures or tables, it copies the caption text but flattens
  equations: `` :math:`\chi^2` `` in a caption would appear as "χ2" in the list. So simple inline math in a
  caption (letters, numbers, symbols, subscripts and superscripts) is written as text instead: letters in italics,
  scripts as subscript or superscript text, and spaces around `=`, `+` and the like. Word keeps that formatting in
  the list. Math with fractions, roots, brackets that grow or other structure stays an equation.
- **Display math,** `.. math::`, is a centred equation in its own paragraph.
- **Numbered equations.** A display equation with `:label:` (or with `math_number_all = True`) is numbered.
  - **Layout:** the equation is centred and the number, such as "(3)", is on the right.
  - **Numbers:** by default Word numbers the equations through the document, with `SEQ Equation` fields. With
    `word_caption_numbering = "sphinx"` and `math_numfig` the numbers include the chapter, as Sphinx numbers them.
  - **References:** `` :eq:`label` `` becomes a cross-reference field to the equation number. See
    [Numbering](numbering.md).
- **Several equations in one directive.** Sphinx's conventions are followed:
  - lines that end in `\\` become one aligned group, aligned on `&`;
  - equations separated by a blank line are stacked one above the other.

## Supported LaTeX

| Area                     | Commands                                                                              |
|--------------------------|---------------------------------------------------------------------------------------|
| Scripts                  | `^`, `_`, primes (`x'`, `x''_i`), `{}^{14}C`                                         |
| Fractions                | `\frac`, `\dfrac`, `\tfrac`, `\cfrac`, `\over`, `\binom`, `\dbinom`, `\tbinom`, `\choose`, `\atop` |
| Roots                    | `\sqrt{x}`, `\sqrt[n]{x}`                                                             |
| Delimiters               | `\left … \middle … \right` with `( ) [ ] \{ \} | \| \langle \rangle \lfloor \rfloor \lceil \rceil` and `.`; `\big`, `\Big`, … are accepted |
| Large operators          | `\sum`, `\prod`, `\coprod`, `\int`, `\iint`, `\iiint`, `\oint`, `\oiint`, `\bigcup`, `\bigcap`, `\bigoplus`, `\bigotimes`, … with limits; `\limits`, `\nolimits` |
| Functions                | `\sin`, `\cos`, `\log`, `\exp`, `\det`, … (37); `\lim`, `\max`, `\min`, `\sup`, `\inf`, `\argmax`, `\argmin`, `\liminf`, `\limsup` with limits below; `\operatorname{}`, `\operatorname*{}` |
| Accents                  | `\hat`, `\widehat`, `\bar`, `\vec`, `\dot`, `\ddot`, `\dddot`, `\tilde`, `\widetilde`, `\acute`, `\grave`, `\breve`, `\check`, `\mathring`, `\overrightarrow`, `\overleftarrow`, … |
| Over and under           | `\overline`, `\underline`, `\overbrace`, `\underbrace`, `\overset`, `\underset`, `\stackrel`, `\xrightarrow`, `\xleftarrow` |
| Boxes and strikes        | `\boxed`, `\fbox`, `\cancel`, `\bcancel`, `\xcancel`, `\phantom`, `\hphantom`, `\vphantom` |
| Fonts                    | `\mathrm`, `\mathbf`, `\boldsymbol`, `\bm`, `\mathit`, `\mathbfit`, `\mathcal`, `\mathscr`, `\mathbb`, `\mathfrak`, `\mathsf`, `\mathtt`, and the old `\rm`, `\bf`, `\it`, … |
| Text                     | `\text{…}` (with nested `$…$`), `\textrm`, `\textbf`, `\textit`, `\emph`, `\mbox`     |
| Spacing                  | `\,`, `\:`, `\;`, `\!`, `\quad`, `\qquad`, `\ `, `~`, `\hspace{}`, `\kern`, …          |
| Modulo, negation         | `\pmod`, `\bmod`, `\mod`, `\pod`, `\not`                                              |
| Symbols                  | 54 Greek letters (and variants) and about 210 symbols: relations, arrows, operators, sets, logic, dots |
| Matrices                 | `matrix`, `pmatrix`, `bmatrix`, `Bmatrix`, `vmatrix`, `Vmatrix`, `smallmatrix`, `array` (with column alignment), `subarray` |
| Cases                    | `cases`, `dcases`, `rcases`                                                           |
| Aligned equations        | `aligned`, `align`, `split`, `alignat`, `alignedat`, `eqnarray`, `flalign` (and the starred forms) |
| Gathered equations       | `gather`, `gathered`, `multline`, `equation`                                          |

Style commands that have no meaning in Word (`\displaystyle`, `\nonumber`, `\label`, `\strut`, …) are ignored.

Letters are italic and digits, function names and symbols such as `\nabla` and `\infty` are upright, as in LaTeX.

## Macros

Define macros for the Word output in `conf.py`:

```python
word_math_macros = {
    "R": r"\mathbb{R}",                    # \R
    "vect": [r"\mathbf{#1}", 1],           # \vect{x}: definition and number of arguments
}
```

Macros defined for MathJax in `mathjax3_config = {"tex": {"macros": {...}}}` are used too, so a document whose math
renders in HTML also renders in Word. `\newcommand` inside the math itself, and `\substack`, are not supported.

## When an equation cannot be converted

If an equation uses something the converter does not support, or has a LaTeX error (an unbalanced brace, say),
the build prints a warning with the file and line:

```
docs/source/theory.rst:42: WARNING: sphinx2word: cannot convert math to a Word equation (expected '}' but found end of expression): ...
```

The LaTeX source of that equation is written in red in the document, so it is easy to find, and the rest of the
document is not affected. At the end of the build a warning gives the number of such equations. MathJax would
usually fail on the same input, so it is worth checking the HTML output too.

# Contract reports

Reports delivered to agencies and customers often start with front matter that is not part of the Sphinx sources:

1. **Cover page:** the contract identification, an optional figure (a mission or company logo), the document
   title, and a **Contributor List** (prepared by, reviewed by).
2. **Second page:** a **Distribution List** and a **Change Record**.
3. Then the table of contents, the list of figures and the list of tables.

All of this is set in `conf.py`. Setting any of `word_contract`, `word_cover_figure`, `word_prepared_by`,
`word_reviewed_by`, `word_distribution` or `word_change_record` replaces the plain title page with this front
matter. A table whose setting is empty is left out.

## Example

```python
word_contract = ["BigSat Phase B2/C/D", "Contract No. BS-26-001"]         # lines above the figure
word_cover_figure = "figures/bigsat_patch.png"                        # relative to conf.py
word_cover_figure_width = "3in"
word_document_title = ["Algorithm Theoretical Basis Document:",
                       "BigSat In-Flight Calibration"]                 # default: the master document's title
word_prepared_by = [("Ada Marsh", "Calibration Scientist"), ("Ben Okafor", "Instrument Engineer")]
word_reviewed_by = [("Clara Voss", "Principal Investigator"), ("Dev Raman", "Project Manager")]
word_distribution = [("J. Smith", "Example Space Agency"), ("R. Patel", "Example Aerospace Ltd")]
word_change_record = [
    # (issue, revision, date, affected pages, description)
    ("", "Draft A", "2023/06/16", "All", "CDR draft for review"),
    # or a dict with the keys issue, revision, date, pages, description
    {"revision": "Rev 0", "date": "2023/06/28", "pages": "All", "description": "CDR"},
]
```

This gives:

| Page | Contents                                                                                           |
|------|----------------------------------------------------------------------------------------------------|
| i    | The two contract lines, the logo, the two title lines, the Contributor List ("Prepared By" and "Reviewed By" tables with Name and Function columns) |
| ii   | The Distribution List (Name, Company) and the Change Record (ISS, REV, Date, Affected Pages, Description) |
| iii… | Contents, List of Figures, List of Tables                                                          |
| 1…   | The body of the document                                                                           |

- **Page numbers and footer.** The cover page has no footer. The other pages have `word_footer_text` on the left
  and the page number on the right. The footer text defaults to the first line of `word_contract`. The front
  matter is numbered i, ii, iii, …, and the body starts at page 1.
- **Table layout.** The tables have a bold header row with a rule below, grey banding and light column lines. A
  table that runs over a page repeats its header row.

## The change record from git

Instead of a list, the change record can be built from the version tags of the repository:

```python
word_change_record = "git"
word_change_record_tags = "v*"            # optional: which tags (an fnmatch pattern), default "*"
word_change_record_notes = {              # optional: replace or add to what git gives
    "v1.0": "CDR draft for review",
    "v1.1": {"issue": "1", "description": "CDR", "pages": "3-7"},
}
```

Each tag on `main` (or `master`) that matches the pattern is one row, oldest first:

| Column         | From git                                                                   |
|----------------|----------------------------------------------------------------------------|
| ISS            | Empty, unless set in `word_change_record_notes`                            |
| REV            | The tag name                                                               |
| Date           | The date of an annotated tag, or of the tagged commit, as `YYYY/MM/DD`     |
| Affected Pages | "All", unless set in `word_change_record_notes`                            |
| Description    | The message of an annotated tag, or the subject of the tagged commit       |

Things to know:

- **Branches.** Tags that are only on other branches are left out. The local `main`/`master` is used, or
  `origin/main`/`origin/master` if there is no local branch.
- **Descriptions.** Annotated tags give the best descriptions without notes: `git tag -a v1.1 -m "CDR"`. For
  lightweight tags the description is the commit message, which is often "Merge branch …". Use
  `word_change_record_notes` to replace it.
- **Repository.** The repository is the one that contains the Sphinx source directory.
- **CI.** CI jobs usually make a shallow clone without tags. Run `git fetch --tags --unshallow` before the build,
  or the change record will be empty.
- **No git.** If git or the branch is missing, the build warns and the change record is empty.

## Changing the words

The headings and column titles can be changed, for example for another language or a customer's terms:

```python
word_front_matter_labels = {"issue": "Issue", "revision": "Revision", "changes": "Document Change Record"}
```

The keys and their defaults:

| Key            | Default            | Key           | Default            |
|----------------|--------------------|---------------|--------------------|
| `contributors` | Contributor List   | `changes`     | Change Record      |
| `prepared_by`  | Prepared By        | `issue`       | ISS                |
| `reviewed_by`  | Reviewed By        | `revision`    | REV                |
| `name`         | Name               | `date`        | Date               |
| `function`     | Function           | `pages`       | Affected Pages     |
| `distribution` | Distribution List  | `description` | Description        |
| `company`      | Company            |               |                    |

## Styles

The cover and front matter use these paragraph styles, which a [template](templates.md) can redefine:

| Style                  | Used for                                              |
|------------------------|-------------------------------------------------------|
| `Spx Cover Title`      | The contract lines and the title lines on the cover   |
| `Spx Cover Figure`     | The paragraph holding the cover figure                |
| `Spx Front Heading`    | Contributor List, Distribution List, Change Record    |
| `Spx Front Table Text` | The text in the front-matter tables                   |

The front-matter headings are not Word headings, so they do not appear in the table of contents.

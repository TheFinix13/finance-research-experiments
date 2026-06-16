# Building the PDF report

From the repository root:

```bash
cd docs/reports
pdflatex confluence_experiment_research_report.tex
pdflatex confluence_experiment_research_report.tex
```

Output: `confluence_experiment_research_report.pdf`

Requires a LaTeX distribution with `booktabs`, `hyperref`, `csquotes`,
`cleveref`, and `xcolor` (e.g. TinyTeX, MacTeX, TeX Live).

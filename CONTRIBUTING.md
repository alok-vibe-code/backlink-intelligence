# Contributing to Backlink Intelligence

Thanks for your interest in improving Backlink Intelligence.

## Project principles

Contributions should preserve the project's core principles:

1. **Evidence over opaque scores.** If the tool makes a recommendation, users should be able to inspect the evidence behind it.
2. **Editorial fit over forced insertion.** Placement recommendations should prioritize usefulness and natural language over exact-match keyword insertion.
3. **Local-first core.** Paid SEO or AI APIs may be optional integrations, but should not become mandatory for core functionality.
4. **Human review.** Automated outputs should support professional judgment, not pretend to reproduce a search engine's ranking system.
5. **Safe crawling.** Network features must include reasonable limits and protect against unsafe URL handling.
6. **Deterministic tests.** Automated tests should prefer local fixtures over live websites wherever possible.

## Development setup

```bash
git clone https://github.com/alok-vibe-code/backlink-intelligence.git
cd backlink-intelligence
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Workflow

- Create a focused feature branch.
- Keep changes scoped to one issue or capability when practical.
- Add or update tests for behavioral changes.
- Update documentation when public behavior changes.
- Open a pull request against `main`.

## Pull request checklist

Before requesting review, confirm that:

- tests pass locally,
- public behavior is documented,
- new URL-fetching code follows the security guidance,
- recommendations expose evidence and confidence where relevant,
- no secrets or credentials are committed,
- and generated/bulk data is not added unless it is intentionally part of a test fixture.

## Methodology discussions

Methodology contributions are welcome, especially when they improve transparency, reproducibility, or limitations. Claims about search-engine behavior should be framed carefully and should not be presented as confirmed ranking factors without appropriate evidence.

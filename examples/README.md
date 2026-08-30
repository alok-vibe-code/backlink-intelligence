# Examples

## Audit

```bash
backlink-intelligence audit "https://publisher.example/article" "https://brand.example/page"
```

## Placement

```bash
backlink-intelligence place \
  "https://publisher.example/article" \
  "https://brand.example/page" \
  --anchor "data science course" \
  --top 3
```

## Bulk qualification

Use `sample-data/prospects.csv` as the input format.

```bash
backlink-intelligence qualify sample-data/prospects.csv --output qualification-report.csv
```

## Monitoring

Use `sample-data/links.csv` as the input format.

```bash
backlink-intelligence monitor sample-data/links.csv
```

## Portfolio

Use `sample-data/backlinks.csv` as an example structure.

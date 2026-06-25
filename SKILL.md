---
name: spirits-creative-performance-ai
description: Export, structure, and quality-check Skai performance data for creative analytics. Use when Codex needs to build date- and country-specific datasets, compare periods, inspect campaigns, brands, channels, ads, drivers, outliers, and prepare analysis-ready CSV/JSON outputs. If no country is specified, assume USA.
---

# Spirits Creative Performance AI

## Overview

Use this skill to read Skai platform data and convert it into analysis-ready exports for creative performance work. It is designed for workflows that need repeatable data pulls by date range and country, configurable fields, quality checks, and period comparisons.

## Workflow

1. Confirm the business or research question, date range, country, and whether a prior period is needed.
2. Read [configuration.md](references/configuration.md) if credentials are missing or fields need to be changed.
3. Use [default-field-config.json](references/default-field-config.json) by default for an `AdId`-level export.
4. Run [skai_report_export.py](scripts/skai_report_export.py) to export Skai data.
5. Load `skai_report_records` and answer with reproducible calculations, not intuition.
6. For period comparisons, run the script twice and perform the comparison locally.

## Quick Start

Base command:

```bash
python3 scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --output-dir /tmp/spirits-creative-performance-ai-es
```

To compare periods:

```bash
python3 scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --output-dir /tmp/spirits-creative-performance-ai-current

python3 scripts/skai_report_export.py \
  --start-date 2026-03-01 \
  --end-date 2026-03-31 \
  --country ES \
  --output-dir /tmp/spirits-creative-performance-ai-prior
```

If the analysis should follow the same exclusion convention as the `skai` enrichment skill, add `--exclude-brand`. If the analysis should keep only non-video creatives, add `--exclude-video`.

## Question Types

Use this skill for questions such as:

- which campaigns, brands, or sources explain a CTR drop
- top ads or campaigns by volume, clicks, conversions, or CTR
- comparisons between countries, channels, or brands within a period
- outliers with high impressions and low CTR
- quality checks, for example rows without `Country`, `AdId`, or `CampaignId`
- downstream enrichment with `ImageUrl` and creative metadata

## Analysis Rules

- Recalculate derived metrics after aggregation. Do not average row-level `CTR`.
- Treat `CTR` as a percentage unless the real export indicates otherwise.
- For comparisons, show absolute and relative deltas.
- Flag small samples before drawing conclusions. High CTR with few clicks may be noise.
- If the question requires fields that are not in the default export, copy and extend the field config. Do not invent answers.
- If the user asks for canonical business data and a curated source exists outside Skai, state clearly that the answer is based on Skai platform data.

See [analysis-playbook.md](references/analysis-playbook.md) for formulas and analysis patterns.

## Outputs

The script generates:

- `skai_report_records.csv` and/or `skai_report_records.json`
- `summary.json`

`skai_report_records` is the main analytical table. `summary.json` documents applied filters, coverage, and available columns.

## Deliverable

Responder como un senior data analyst:

- respuesta directa primero
- evidencia cuantitativa despues
- explicacion del metodo y filtros usados
- caveats si falta algun campo, si hubo que excluir EXCLUDED_BRAND, o si el volumen es bajo

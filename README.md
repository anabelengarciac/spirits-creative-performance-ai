---
name: skai-skill
description: Consulta datos de Skai por API, exporta reportes de performance listos para analisis y responde preguntas de senior data analyst sobre ads, campaigns, brands, channels, comparativas entre periodos, drivers, outliers y checks de calidad. Use when Codex needs to leer datos directamente desde Skai, no solo enriquecer datasets con ImageUrl. Si no se especifica pais, asumir USA.
---

# Skai Skill

## Overview

Usa esta skill para leer datos de Skai desde la plataforma y convertirlos en un export analitico listo para responder preguntas de negocio y performance. Reutiliza el mismo acceso API que la skill `skai`, pero en lugar de hacer solo mapping de `ImageUrl`, prepara un reporte completo para analisis.

## Workflow

1. Confirmar la pregunta de negocio, el rango de fechas, el pais y si hace falta comparar contra otro periodo.
2. Revisar [configuration.md](./skai-skill/references/configuration.md) si faltan credenciales o si necesitas cambiar campos.
3. Usar por defecto [default-field-config.json](./skai-skill/references/default-field-config.json) para sacar un reporte a nivel `AdId`.
4. Ejecutar [skai_report_export.py](./skai-skill/scripts/skai_report_export.py) para exportar datos de Skai.
5. Cargar `skai_report_records` y contestar la pregunta con calculos reproducibles, no con intuicion.
6. Si la pregunta es comparativa entre periodos, ejecutar el script dos veces y hacer el analisis local despues.

## Quick Start

Comando base:

```bash
python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --output-dir /tmp/skai-skill-es
```

Para comparar periodos:

```bash
python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --output-dir /tmp/skai-skill-current

python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-03-01 \
  --end-date 2026-03-31 \
  --country ES \
  --output-dir /tmp/skai-skill-prior
```

Si la pregunta debe seguir la misma convencion de la skill `skai` para excluir `EXCLUDED_BRAND`, anadir `--exclude-brand`. Si el analisis debe quedarse solo con creatividades no-video, anadir `--exclude-video`.

## Question Types

Usar esta skill para preguntas como:

- que campaigns, brands o sources explican una caida de CTR
- top ads o campaigns por volumen, clicks, conversions o CTR
- comparativas entre paises, channels o brands dentro de un periodo
- outliers con muchas impresiones y bajo CTR
- chequeos de calidad, por ejemplo filas sin `Country`, `AdId` o `CampaignId`
- enriquecimiento de una investigacion posterior con `ImageUrl` y metadata de creatividad

## Analysis Rules

- Recalcular metricas derivadas despues de agregar. No promediar `CTR` fila a fila.
- Tratar `CTR` como porcentaje, no como proporcion decimal, salvo que el export real diga otra cosa.
- Para comparativas, mostrar delta absoluto y delta relativo.
- Senalar muestras pequenas antes de sacar conclusiones. Por ejemplo, alto CTR con pocos clicks puede ser ruido.
- Si la pregunta requiere campos no presentes en el export por defecto, copiar el field config y extenderlo. No inventar respuestas.
- Si el usuario pide datos canonicos de negocio y existe una fuente curada fuera de Skai, explicitar que estas respondiendo desde Skai platform data.

Ver [analysis-playbook.md](./skai-skill/references/analysis-playbook.md) para formulas y patrones de analisis.

## Outputs

El script genera:

- `skai_report_records.csv` y/o `skai_report_records.json`
- `summary.json`

`skai_report_records` es la base analitica principal. `summary.json` documenta filtros aplicados, cobertura y columnas disponibles.

## Deliverable

Responder como un senior data analyst:

- respuesta directa primero
- evidencia cuantitativa despues
- explicacion del metodo y filtros usados
- caveats si falta algun campo, si hubo que excluir EXCLUDED_BRAND, o si el volumen es bajo

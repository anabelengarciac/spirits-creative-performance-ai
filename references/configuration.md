# Configuration

## Credenciales

El script usa el mismo modelo de acceso API que la skill `skai`.

Orden de busqueda del `.env`:

1. `--env-file`
2. `skai-skill/.env`
3. `${CODEX_HOME:-$HOME/.codex}/skills/skai/.env`
4. `.env` del directorio actual

Variables esperadas:

- `SKAI_CLIENT_ID`
- `SKAI_REFRESH_TOKEN`
- `SKAI_KS`
- `SKAI_PROFILE_IDS`
- `SKAI_COUNTRY`

Tambien admite variantes por pais:

- `SKAI_REFRESH_TOKEN_ES`
- `SKAI_KS_ES`
- `SKAI_PROFILE_IDS_ES`

Si no se especifica `--country`, el script usa `SKAI_COUNTRY`; si no existe, usa `USA`.

## Comando Base

```bash
python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --output-dir /tmp/skai-skill-es
```

## Convenciones

- El export por defecto trabaja a nivel `AdId`.
- Incluye dimensiones utiles para analisis: `CampaignName`, `brand`, `source`, `Country`, `AdTypeName`.
- Incluye metricas basicas: `Impressions`, `Clicks`, `Conversions`, `CTR`.
- Mantiene `ImageUrl` para diagnostico creativo.

## Ajuste De Campos

El field config por defecto esta en [default-field-config.json](./skai-skill/references/default-field-config.json).

Si la cuenta usa otros nombres de campo:

1. copiar ese JSON
2. ajustar `group_by`, `name`, `group`, `type` o `aliases`
3. ejecutar con `--field-config /ruta/a/tu-config.json`

Ejemplo:

```bash
python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-04-01 \
  --end-date 2026-04-30 \
  --country ES \
  --field-config /tmp/skai-fields.json \
  --output-dir /tmp/skai-skill-es
```

## Campos Adicionales

Si necesitas `Spend`, `Date`, `CPA`, `ROAS` u otros campos, anadelos al field config. Si el API responde que una columna no existe, el script la quita del request y lo deja registrado en `summary.json`.

## Filtros Opcionales

- `--exclude-brand`: excluye `EXCLUDED_BRAND` y `Excluded Brand`
- `--exclude-video`: excluye creatividades de video
- `--profile-ids 775,776`: limita el export a ciertos perfiles

## Testing Sin API

Puedes validar el flujo con el fixture ya existente de la otra skill:

```bash
python3 ./skai-skill/scripts/skai_report_export.py \
  --start-date 2026-03-01 \
  --end-date 2026-03-31 \
  --output-dir /tmp/skai-skill-sample \
  --input-json ./skai/scripts/fixtures/sample_report.json
```

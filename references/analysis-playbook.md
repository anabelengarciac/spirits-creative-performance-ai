# Analysis Playbook

## Core Rules

- Sumar metricas base primero.
- Recalcular ratios despues de agregar.
- No promediar `CTR` fila a fila.
- Mostrar siempre el rango de fechas y los filtros usados.
- Si el volumen es bajo, decirlo explicitamente.

## Derived Metrics

Usar estas formulas sobre agregados:

- `CTR = Clicks / Impressions * 100`
- `CVR = Conversions / Clicks * 100`
- `Clicks per 1k impressions = Clicks / Impressions * 1000`

Si anades `Spend` al field config, usar:

- `CPC = Spend / Clicks`
- `CPM = Spend / Impressions * 1000`
- `CPA = Spend / Conversions`

## Common Question Patterns

### Ranking

1. agrupar por la dimension pedida
2. sumar `Impressions`, `Clicks`, `Conversions`
3. recalcular `CTR` y cualquier ratio derivado
4. ordenar por la metrica principal

### Period Comparison

1. exportar el periodo actual
2. exportar el periodo de comparacion
3. agregar ambos al mismo grain
4. calcular:
   - delta absoluto = actual - previo
   - delta relativo = (actual - previo) / previo

### Driver Analysis

Para explicar una caida o subida:

1. calcular el delta total
2. calcular el delta por brand, source, campaign o ad
3. ordenar por impacto absoluto
4. separar causa estructural de ruido de bajo volumen

### Outlier Detection

Patrones utiles:

- muchas impresiones y CTR bajo
- CTR alto con pocas impresiones
- clicks altos y conversions bajas
- creatives sin `ImageUrl`
- rows sin `Country`, `CampaignId` o `AdId`

## Answer Shape

Responder con este orden:

1. respuesta directa
2. evidencia numerica
3. drivers o causas principales
4. metodologia y filtros
5. caveats

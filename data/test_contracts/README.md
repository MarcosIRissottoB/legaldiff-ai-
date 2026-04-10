# Contratos de prueba

Pares de contratos simulados para testing del pipeline LegalDiff AI.
Cada par consiste en un contrato original y su enmienda (adenda).

## Par 1 — Licencia de Software (cambios simples)

- `documento_1__original.jpg` — Contrato entre TechNova S.A. y DataBridge Soluciones S.R.L.
- `documento_1__enmienda.jpg` — Enmienda al mismo contrato

**Cambios esperados:**

| Seccion | Cambio |
|---------|--------|
| Plazo | 12 meses → 24 meses |
| Pago | USD 12.000 → USD 15.000 |
| Soporte | Solo email → email + chat |
| Terminacion | 30 dias de anticipacion → 60 dias |
| Proteccion de Datos | Clausula nueva (no existia en el original) |

## Par 2 — Consultoria (cambios complejos)

- `documento_2__original.jpg` — Contrato entre Orion Consulting y GreenWave Industries
- `documento_2__enmienda.jpg` — Enmienda al mismo contrato

**Cambios esperados:**

| Seccion | Cambio |
|---------|--------|
| Alcance | Se agrega analisis regulatorio |
| Duracion | 6 meses → 9 meses |
| Honorarios | USD 8.000 → USD 9.500 |
| Entregables | Reportes mensuales → quincenales |
| Propiedad Intelectual | Clausula nueva |

## Par 3 — SaaS (cambios minimos)

- `documento_3__original.jpg` — Contrato entre CloudMetrics y RetailPulse
- `documento_3__enmienda.jpg` — Enmienda al mismo contrato

**Cambios esperados:**

| Seccion | Cambio |
|---------|--------|
| Precio | USD 1.200 → USD 1.250 |
| Disponibilidad (SLA) | 99,5% → 99,9% |
| Soporte | Solo email → email + tickets |

## Uso

```bash
# CLI
python src/main.py data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg

# API
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: $LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_1__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_1__enmienda.jpg"
```

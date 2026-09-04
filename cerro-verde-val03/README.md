# RE-CO-005 · Control de Trabajo Remoto — VAL 03 (Cerro Verde)

Llenado del registro **RE-CO-005 "Control de Trabajo Remoto"** (Kämpfer, Versión 01,
19/07/2021) a partir de la bitácora de actividades de la jornada de sustento de
horas para la **Valorización 03 (VAL 03)** del proyecto Cerro Verde.

## Archivos

| Archivo | Contenido |
|---|---|
| `RECO005_Control_de_Trabajo_Remoto_VAL03.pdf` | Documento final llenado (1 página, A4). |
| `bitacora_val03.json` | Bitácora fuente (17 registros, 04:28 – 20:54). |
| `generar_reco005.py` | Generador del PDF a partir de la bitácora. |
| `assets/reco005_cabecera.png` | Cabecera institucional extraída del formato original. |

Regenerar: `python3 generar_reco005.py` (requiere `reportlab`).

## Fidelidad al formato

La geometría se tomó directamente del PDF original del formato, de modo que el
documento generado es visualmente idéntico al vigente y solo cambia el contenido:

- Cabecera institucional reutilizada tal cual (logo, `REGISTRO`, código RE-CO-005,
  versión y fecha).
- Bloque de datos generales (`MES`, `APELLIDOS Y NOMBRES COLABORADOR`, `DNI`,
  `GERENCIA RESPONSABLE`) en sus posiciones originales.
- Columnas de la tabla en sus coordenadas exactas: `N°`, `FECHA`,
  `HR. LABORADAS`, `ACTIVIDADES REALIZADAS` (`Hrs` + `Descripción`),
  `FIRMA COLABORADOR`, `VºBº GERENCIA`, `OBSERVACIONES GERENCIA RESPONSABLE`.
- Pie de firmas (Jefatura / Gerencia Responsable) sin cambios.
- Las filas no utilizadas (2 y 3) se conservan en blanco con sus renglones
  internos, para seguir usando el registro en jornadas posteriores.

## Criterio de imputación de horas

La bitácora registra la hora de **culminación** de cada actividad ("Culminación
de…", "Finalización de…"), por lo que a cada registro se le imputa el tiempo
transcurrido desde el registro anterior. El primer registro (04:28) es la marca de
inicio de jornada y no consume tiempo; se muestra como `inicio` en la columna `Hrs`.

La jornada cierra a las **20:58**, cuatro minutos después del último registro de la
bitácora (20:54). Ese tiempo de cierre se imputa al último registro, que es
justamente el de cierre de jornada; los sellos de tiempo de la bitácora no se
alteran. El campo que lo controla es `hora_cierre_jornada` en
`informacion_general`.

```
04:28 (inicio) … 20:54 (último registro) … 20:58 (cierre)  →  16:30 h
```

`HR. LABORADAS` = **16:30**, y la última subfila repite el total como control.

## Contenido de cada actividad

Cada subfila de `Descripción` se compone de:

```
HH:MM · Nombre de la actividad:  descripción.  (Sustento: medio de verificación)
```

El medio de verificación proviene del campo `referencia_visual` de la bitácora y
se cita en cursiva, de modo que el registro queda trazable contra las evidencias
(capturas de Excel, fotos de partes diarios, planos amarillados, etc.).

## Campos pendientes de llenado

Estos datos no figuran en la bitácora y se dejaron en blanco para su completado
manual antes de la firma:

- `MES` y `FECHA` de la jornada.
- `APELLIDOS Y NOMBRES COLABORADOR` y `DNI`.
- `GERENCIA RESPONSABLE - Apellidos y Nombres`.
- `FIRMA COLABORADOR`, `VºBº GERENCIA` y `OBSERVACIONES GERENCIA RESPONSABLE`.

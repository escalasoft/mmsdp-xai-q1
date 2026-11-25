# Auditoría final de alineación E1–E2 — 1.0.0

Fecha: 2026-10-12. Alcance: Apache ActiveMQ/T1. Dictamen general **PARTIAL**, con rutas específicas **READY**. No se generaron figuras integradas.

## Evidencia e integridad

Se verificaron contra sus manifiestos los artefactos consumidos de E1 CODE, E1 TEXT, cierre E2 1.1.0, congelamiento de población E2, journal de reconstrucción y G4. `integrity.json` contiene 29 referencias: 27 verificadas contra manifiesto y dos documentos cuyo digest actual se registra (política numérica e informe PROCESS). No se afirma una verificación exhaustiva de archivos ajenos a esta selección. Los hashes de los manifiestos también se registran. No se abrieron modelos ni representaciones de características ni contenedores mixtos. El gzip leído es exclusivamente la tabla publicada de atribuciones E2/T1.

La unión usa proyecto, partición y `row_identifier`, con correspondencia al SHA de commit desde los registros E1. Se comprobaron identidades únicas, los 245 miembros, orden temporal CODE, orden foreground TEXT y orden foreground E2. Los órdenes no son intercambiables. TEXT no incrusta identidades en su NPZ: su vínculo se sostiene en el ledger congelado, la indexación documentada del productor (líneas 911–918) y el cruce independiente `foreground_index` de CODE. No se interpretó posición como identidad sustituta.

Los digests de pipelines publicados por E1 coinciden con el journal, y tanto la identidad unimodal como cada identidad de fusión figuran como consumidores del mismo componente FINAL_BASE. Esta evidencia documental no afirma identidad con ejecutables históricos originales ni supone volver a cargar modelos.

## Matriz de alineación

| Familia | E1 CODE → entrada E2 | E1 TEXT → entrada E2 | Configuraciones E2 disponibles |
|---|---|---|---|
| LR | 245/245 exactas en cada una de 3 configuraciones | 245/245 exactas en cada una de 3 configuraciones | C+P, C+T, P+T, C+P+T |
| RF | 245/245 exactas en cada una de 3 configuraciones | Sin atribuciones TEXT aceptadas | Las cuatro |
| XGB | 245/245 exactas en cada una de 3 configuraciones | 245/245 exactas en cada una de 3 configuraciones | Las cuatro |
| LGB | 245/245 exactas en cada una de 3 configuraciones | 245/245 exactas en cada una de 3 configuraciones | Las cuatro |

CODE participa en C+P/C+T/C+P+T; TEXT en C+T/P+T/C+P+T. Son 16 instancias de modelo/configuración, 3.920 filas E2 y 24 enlaces modalidad/instancia: 21 enlaces explicativos comprobados, 3 sin E1 TEXT RF. Los 21 enlaces comprenden 5.145 comparaciones, no 5.145 commits independientes: reutilizan las mismas 245 identidades. Error absoluto y relativo máximo: **0**; discrepancias de decisión: **0**. Se aplican absoluta ≤1e-12 y relativa ≤1e-10 cuando |referencia|≥1e-8.

CODE aporta probabilidades guardadas. TEXT aporta salidas logit/margen: se aplicó únicamente `expit` aritmético al array guardado, preservando su dtype (XGB float32; LR/LGB float64). No es inferencia ni ajuste/calibración. La coincidencia exacta obtenida no exige tolerancias nuevas. El detalle por fila queda en `row_level_comparisons.jsonl` y los modelos/digests en `alignment_matrix.csv`.

RF TEXT falló históricamente el chequeo exacto TreeSHAP de aditividad y publicó `values_published=false`. La alineación de su predictor no convierte en admisibles explicaciones inexistentes. CODE RF conserva su PASS.

## Cobertura local real

Los ocho casos E1 CODE y E1 TEXT son el mismo conjunto congelado. Todos están entre las 245 filas E2 de cada una de las 16 instancias. Por tanto pueden construirse vistas ancladas en esos ocho casos, recuperando sus contribuciones E2 ya persistidas en la tabla global. Deben denominarse «casos preseleccionados E1 con evidencia E2», sin afirmar que son los ocho locales originalmente seleccionados por E2.

Intersección estricta entre los dos conjuntos locales históricos:

| Familia | C+P | C+T | P+T | C+P+T |
|---|---:|---:|---:|---:|
| LR | 1 | 0 | 0 | 0 |
| RF | 0 | 0 | 2 | 0 |
| XGB | 0 | 0 | 0 | 0 |
| LGB | 1 | 0 | 0 | 0 |

Los dos casos RF/P+T compartidos por identidad no tienen E1 TEXT RF válido ni rama CODE en esa configuración. No se deben presentar como una jerarquía E1–E2 completa. `local_coverage.csv` identifica cada intersección; `identity_crosswalk.json` conserva los ocho marcadores y SHA de commit completos. No se seleccionaron casos nuevos.

## Escalas, referencias y calibración

E1 CODE: LR logit, RF probabilidad positiva, XGB/LGB margen nativo. E1 TEXT aceptado: LR logit, XGB/LGB margen nativo, 2.557 características. E2: contribuciones aditivas al **meta-logit previo a calibración**, referencia OOF; su probabilidad RAW es el sigmoid del meta-logit. Las referencias E1 (TRAIN, centrado LR o conteos de rutas de árboles) no son la referencia OOF de E2.

La tabla E2 no contiene una probabilidad calibrada independiente. El estado de calibración histórico registrado en G4 es **RAW en las 16 instancias ActiveMQ** (`calibration_boundary.csv`), por lo que no hay base para dibujar una corrección isotónica numérica en estas instancias. Esta auditoría verifica ese metadato y el endpoint RAW; no revalida G5 ni calcula una probabilidad calibrada. Un rótulo de «probabilidad final calibrada» no está respaldado por esta lectura. Una eventual etapa de calibración debe separarse visualmente y documentarse con su propia evidencia, sin propagarle la aditividad E2.

## Figuras propuestas y dictamen

READY significa suficiencia de evidencia para una futura visualización, no autorización de ejecución en esta tarea. PARTIAL significa una figura deliberadamente incompleta y etiquetada, no imputación de explicaciones faltantes.

| Figura propuesta | Alcance | Dictamen |
|---|---|---|
| Panel global enlazado: contribuciones E2 arriba, ranking E1 CODE y E1 TEXT abajo, ejes separados | C+T; LR/XGB/LGB; mismos 245 commits | READY |
| Panel local: waterfall E2 meta-logit, probabilidad RAW y dos paneles E1, flechas de identidad sin anchuras cuantitativas entre niveles | Los ocho casos E1, C+T; LR/XGB/LGB | READY |
| Extensión global/local C+P+T con PROCESS visible en E2 y recuadro E1 PROCESS no evaluado | LR/XGB/LGB | PARTIAL; ramas CODE/TEXT READY |
| Panel E2 + E1 CODE con ramas TEXT/PROCESS ausentes explícitamente señaladas cuando correspondan | RF C+P/C+T/C+P+T; también C+P en las demás familias | PARTIAL; enlace CODE READY |
| Panel E2 P+T + E1 TEXT | LR/XGB/LGB | PARTIAL; enlace TEXT READY, PROCESS sin E1 |
| Mapa de cobertura por modelo/modalidad/configuración, sin magnitudes de atribución | Las 16 instancias | READY |
| Jerarquía completa de características PROCESS o RF TEXT | Cualquier instancia que las requiera | NO-GO |
| Sankey conservativo o waterfall único que sume E1 y E2 hasta probabilidad calibrada | Todas | NO-GO |

Recomendación: una figura principal C+T con LR/XGB/LGB y un mapa de cobertura; dejar la extensión C+P+T explícitamente parcial y los ocho casos completos como suplemento. No seleccionar modelo ni caso por magnitud o apariencia favorable. Para un único caso principal se requiere una regla prospectiva explícita; esta auditoría no lo elige.

Rótulo obligatorio PROCESS: **“E1 not evaluated: temporal provenance unproven (PROCESS_ANCESTRAL_UNPROVEN)”**. Su contribución E2 y papel predictivo permanecen visibles. Ausencia de E1 no significa contribución cero, inutilidad predictiva ni leakage demostrado. Para RF TEXT usar un rótulo diferente: **“E1 unavailable: exact TreeSHAP additivity check failed”**.

## Afirmaciones admisibles y límites

Se puede afirmar correspondencia empírica exacta de salidas unimodales explicadas con entradas E2 en los 21 enlaces comprobados y trazabilidad de identidades/componentes congelados. Se puede describir qué características explican un predictor unimodal y qué probabilidades de modalidad contribuyen al meta-logit en la misma instancia.

No se puede afirmar una descomposición algebraica completa características→probabilidad fusionada: los métodos, bases y escalas difieren y existe no linealidad entre niveles. No multiplicar atribuciones E1 por coeficientes E2 para presentarlas como atribuciones finales. No comparar ni sumar magnitudes entre logit, margen y probabilidad. La concordancia exacta no demuestra causalidad, robustez ante perturbaciones, utilidad industrial ni aumento de confianza empíricamente evaluado. No generalizar ActiveMQ/T1 a 14 proyectos. La fidelidad/estabilidad históricas no se reejecutaron; no subsanan la procedencia PROCESS. Los ocho casos no son una muestra inferencial representativa por sí solos.

## Reproducción y parada

`audit.py` lee una lista explícita de evidencia, verifica hashes, cruza por identidad y produce tablas; no importa predictores ni SHAP. Ejecutar con `.venv-xai-s56/bin/python -B`, `PYTHONDONTWRITEBYTECODE=1`, desde el repositorio. Su salida pertenece exclusivamente a esta nueva auditoría. `verify.py` relee las tablas y las fuentes, comprueba invariancia, conteos y cálculos persistidos en un proceso separado. `MANIFEST.sha256` sella los archivos nuevos. No se modificaron las auditorías históricas, el manuscrito ni los modelos. No se generaron figuras, ni se accedió a T2. Se detiene aquí.

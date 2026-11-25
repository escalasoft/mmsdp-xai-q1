# Última revisión documental de recuperabilidad temporal de E1 PROCESS

Fecha: 2026-10-12 (America/Lima).

**Dictamen: NOT RECOVERABLE WITH CURRENT EVIDENCE.**

**Recomendación: NO-GO para iniciar una recuperación controlada; cerrar E1 PROCESS para el artículo actual.** Es una recomendación documental, no una modificación de contratos ni una ejecución del cierre. No se ha demostrado leakage: falta demostrar la procedencia temporal de los valores usados. Se mantiene `PROCESS_ANCESTRAL_UNPROVEN`.

## Alcance y método

Se revisaron contratos, informes, registros de procedencia y código estático del repositorio; se contrastó la ficha pública de ApacheJIT v2. Se inspeccionaron directamente el README, `gitminer.py` y `collector.py` de la copia original ya extraída, y se buscaron funciones y referencias a las métricas en `gumtree.py`. Se contrastaron los SHA-256 de los tres primeros archivos con el inventario R4B: coinciden.

No se abrieron ZIP, notebooks, CSV, matrices, modelos, datasets comprimidos ni otros contenedores mixtos; no se accedió a datos T2 ni se extrajeron valores PROCESS. La lectura de contratos que describen particiones no constituye lectura de sus datos. No se ejecutaron scripts del proyecto, entrenamiento, inferencia, SHAP, reconstrucción ni tests experimentales. Sólo se añade este informe; no se modifican contratos ni resultados anteriores.

El PASS de E1 CODE en LR/RF/XGB/LGB, la evaluación histórica TEXT, la evidencia E2 y G4 PROCESS ActiveMQ se conservan como antecedentes. Los estados históricos de CODE/TEXT en informes antiguos no sustituyen los avances posteriores comunicados para esta revisión. No se revalidaron mediante ejecución.

## Fuentes identificadas y alcance probatorio

1. [Ficha oficial ApacheJIT v2](https://zenodo.org/records/5907847), Keshavarz y Nagappan, 26-01-2022, DOI `10.5281/zenodo.5907847`. Describe el paquete de replicación y atribuye a sus scripts tareas de búsqueda, recogida, trazado y filtrado. La ficha identifica la publicación del dataset; no ofrece una cadena de ejecución por métrica que demuestre el cálculo de los valores congelados. No se descargó ni previsualizó el archivo.
2. [Código del congelamiento 48F-R1](/Users/alex/MMSDP-XAI-Q1/src/dataset/apachejit_final_dataset_freeze.py:496): definiciones conceptuales; [contrato generado](/Users/alex/MMSDP-XAI-Q1/src/dataset/apachejit_final_dataset_freeze.py:615): ancestros estrictos; [copia de valores](/Users/alex/MMSDP-XAI-Q1/src/dataset/apachejit_final_dataset_freeze.py:811): importa columnas mediante `getattr(row, name)`. Identifica `apache_metrics_kamei.csv` unido a `apachejit_total.csv` como fuente histórica. Esto es una implementación de importación, no el generador original de las métricas.
3. [Informe de congelamiento](/Users/alex/MMSDP-XAI-Q1/audits/q1-apachejit-final-dataset-freeze/1.0.0/REPORT.md): declara explícitamente `NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1` para PROCESS. Su regeneración determinista acredita la copia/construcción local descrita; no reproduce la historia que originó cada valor.
4. [Registro de definiciones y brechas](/Users/alex/MMSDP-XAI-Q1/audits/q1-primary-xai-canonical-source-rematerialization-feasibility/1.0.0/process_feature_definition_registry.jsonl): clasifica las seis métricas como `SEMANTICS_UNRESOLVED`; faltan agregación exacta, recencia, renombrados y merges. Una agregación sustituta sería una redefinición científica hasta demostrar equivalencia.
5. [Procedencia temporal R4B](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/apachejit_process_temporal_provenance.jsonl) y [mapeo PROCESS](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/apachejit_process_feature_mapping.jsonl): las seis características conservan `PROCESS_ANCESTRAL_UNPROVEN`, sin subconjunto elegible acreditado. No afirman una infracción observada.
6. [Inventario original](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/apachejit_v2_inventory.jsonl) y [contrato de fuente](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/apachejit_canonical_source_contract.json): identifican scripts y notebooks. `data_linking_filtering.ipynb` y `dataset_construction.ipynb` contienen salidas no admitidas; su contenido no fue abierto. No se concluye que carezcan de evidencia útil, sino que no hay una copia de código separada y certificada identificada en estos registros que cierre la prueba.
7. [gitminer.py original](/Users/alex/MMSDP-XAI-Q1/data/external/apachejit-v2/extracted/apachejit/src/gitminer.py) y [collector.py original](/Users/alex/MMSDP-XAI-Q1/data/external/apachejit-v2/extracted/apachejit/src/collector.py): implementan recogida de commits y búsqueda por issues, no los seis agregadores PROCESS. `gitminer.py` usa fechas de committer en la recogida; eso no demuestra las fechas usadas por un generador de métricas no identificado. `gumtree.py` trata filtrado y árboles sintácticos. El [generador local PROCESS](/Users/alex/MMSDP-XAI-Q1/src/feature_engineering/process_features.py) sólo produce número de padres, indicador de merge e igualdad autor/committer; no calcula estas seis métricas.
8. [Orden temporal congelado](/Users/alex/MMSDP-XAI-Q1/audits/q1-apachejit-final-dataset-freeze/1.0.0/temporal_ordering_contract.json): timestamp de autor normalizado a UTC y SHA para desempate. Ordenar filas o separar TRAIN/TEST no demuestra cómo se computó la historia de cada fila.
9. [Cierre R4B](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/SPRINT56_3B_R4B_CANONICAL_APACHEJIT_REENTRY_REPORT.md) y [terminación](/Users/alex/MMSDP-XAI-Q1/audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/r4b_termination_contract.json): la ruta canónica ya fue cerrada por insuficiencia de evidencia; no recomiendan otra ronda exclusivamente para encontrar más archivos.

## Matriz por característica

En las columnas de implementación, ejecución y correspondencia, «no acreditada» se refiere al **cálculo original de la característica**, no a la existencia del CSV o a su uso predictivo posterior. Las definiciones siguientes son las del contrato local; no son fórmulas verificadas del productor original.

| Característica | Definición conceptual documentada | Implementación original identificada | Ejecución histórica del cálculo | Correspondencia reproducible con valores congelados | Prueba concreta faltante |
|---|---|---|---|---|---|
| `ndev` | Desarrolladores previos de archivos tocados | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Código de unión/deduplicación de autores por archivos; identidad por nombre/email/alias; universo histórico anterior; reglas de renombrados y merges; vínculo verificable a los valores |
| `age` | Tiempo medio desde cambios previos de archivos tocados | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Selección del último cambio previo por archivo; reloj autor/committer, unidad, zona y redondeo; promedio y archivos nuevos; timestamps iguales o no monótonos; continuidad tras renombrados y merges |
| `nuc` | Cambios únicos previos en archivos tocados | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Definición de cambio único; unión de commits frente a suma por archivo; deduplicación; inclusión de ramas alcanzables y tratamiento de merges/renombrados; exclusión del commit actual |
| `aexp` | Commits anteriores del autor | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Identidad y normalización del autor; contar toda la historia o sólo commits seleccionados; alcance de ramas/repositorio; consulta antes de actualizar el contador; política de merges |
| `arexp` | Experiencia del autor ponderada por recencia | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Fórmula exacta, ventana o decaimiento, unidades y origen temporal, límites inclusivos/exclusivos, agregación y redondeo; identidad y actualización anterior al commit |
| `asexp` | Commits anteriores del autor en subsistemas tocados | No acreditada | No acreditada | No acreditada; sólo linaje de importación | Definición original de subsistema y rutas raíz; suma/unión/promedio entre subsistemas; deduplicación; identidad del autor; renombrados entre subsistemas, ramas y merges |

Las fuentes 2–5 sostienen las seis filas. En todas faltan además versión/hash del productor real, configuración y dependencias, alcance del historial de entrada, evidencia de ejecución vinculada al CSV y una comparación identificada por repositorio+SHA contra los valores congelados. La integridad del archivo distribuido no sustituye esos eslabones.

## Comprobación del límite temporal

| Exigencia | Evidencia disponible | Resultado |
|---|---|---|
| Información exclusivamente anterior | Contrato de ancestros estrictos | Declarada; no demostrada para el productor original |
| Exclusión del commit actual y posteriores | Prohibición contractual | No hay flujo de actualización/consulta original verificable ni trazas vinculadas |
| Fechas y orden temporal | Orden local por autor/UTC/SHA; recogida original con fechas de committer | Falta identificar el reloj y orden del cálculo PROCESS; no se infiere error sólo por esta diferencia |
| Agregación de experiencia | Descripciones de `aexp`, `arexp`, `asexp` | Sin algoritmos originales completos |
| Recencia | Descripciones de `age` y `arexp` | Sin fórmula, unidad y tratamiento de extremos acreditados |
| Identidad de autores | Referencia contractual a identidad Git upstream | Sin normalización, alias ni clave original verificados |
| Renombrados | Referencia a semántica upstream y prohibición de información futura | Sin algoritmo original de continuidad de archivos/subsistemas |
| Merges | Ancestros alcanzables en el contrato; primer padre en CODE | La política CODE no prueba la agregación PROCESS |
| Valores congelados | Procedencia de importación; G4 histórico | No prueba reproducción temporal por característica |

Ancestro topológico y fecha estrictamente anterior no son equivalentes cuando los timestamps son no monótonos. Se necesita una regla original explícita para esa situación, además del desempate entre fechas iguales. Imputación TRAIN y escalado LR posteriores tampoco subsanan la procedencia temporal de una entrada.

## Ruta de recuperación y trabajo pendiente

Una ruta limitada requeriría **evidencia nueva y concreta**, admitida sin abrir contenedores mixtos: (a) productor original completo y versionado; (b) parámetros, dependencias e historial de entrada identificados; (c) registros o atestación técnica verificable que vinculen esa ejecución con `apache_metrics_kamei.csv`; (d) un mecanismo autorizado y aislado para cotejar valores congelados por identidad, con cobertura y criterio de equivalencia explícitos. Ninguno de esos requisitos se considera resuelto por la publicación de definiciones conceptuales o por G4.

G4 responde a equivalencia predictiva del modelo reconstruido bajo entradas históricas; no demuestra que dichas entradas se calcularon sólo con pasado. Incluso predicciones coincidentes no certifican igualdad de todas las características ni su linaje.

No se identificó un generador concreto pendiente sólo de una pequeña adaptación o una prueba delimitada. Sin él, elegir fórmulas de Kamei, recorrer Git y recalcular seis métricas introduciría decisiones nuevas sobre historia, autores, tiempo, archivos y agregación. Eso sería una reconstrucción sustancial del sustrato PROCESS, no una recuperación acreditada de los valores históricos; no permite reutilizar automáticamente modelos o resultados. Esta revisión no demuestra que toda recuperación futura sea imposible, ni autoriza esa reconstrucción.

No se asignan horas, días ni plazos: faltan implementación, entorno y ruta de validación con los que dimensionarlos. Es verificable que quedan seis características sin prueba original, junto con las brechas transversales de ejecución y correspondencia; no es verificable el esfuerzo de resolverlas.

No se elige `CONDITIONAL`: una posibilidad abstracta de que aparezca código o documentación no constituye una ruta localizada y delimitada. Tampoco se elige `RECOVERABLE`: no hay prueba temporal suficiente ni secuencia de recuperación verificable con los insumos admitidos actuales.

## Recomendación para el artículo y parada

Cerrar E1 PROCESS para el artículo actual y no prolongar la investigación para completar la figura. Presentar E2 y los E1 CODE/TEXT dentro de sus poblaciones y alcances acreditados, señalando PROCESS como «no evaluado en E1 por procedencia temporal no demostrada». No representar esa ausencia como importancia cero, irrelevancia predictiva ni leakage probado; tampoco afirmar una descomposición jerárquica completa E2 + CODE + PROCESS + TEXT.

Se preservan E1 CODE, E1 TEXT, E2 y G4. Esta revisión termina aquí. Cualquier acción posterior queda a la espera de autorización explícita; no se inicia recuperación ni una nueva fase experimental.

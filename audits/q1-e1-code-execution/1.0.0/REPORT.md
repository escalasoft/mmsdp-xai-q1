# E1 CODE — ejecución científica 1.0.0

Dictamen global: PASS. LR/RF/XGB/LGB: PASS. Cobertura completa de 245 commits ActiveMQ/T1 y los ocho locales preseleccionados, seis características, veinte repeticiones por familia. No se descartó ningún commit.

| Modelo | Residual absoluto máximo | Residual normalizado máximo | Repetibilidad | Estabilidad |
|---|---:|---:|---:|---|
| LGB | 1.0658141036401503e-14 | 8.3997382638171991e-15 | 0.0 | STABLE |
| LR | 4.4408920985006262e-16 | 4.2131571490142926e-16 | 0.0 | STABLE |
| RF | 1.7541523789077473e-14 | 9.3517373459735834e-15 | 0.0 | STABLE |
| XGB | 3.2233074307441711e-06 | 8.2302464922779558e-07 | 0.0 | STABLE |

LR: límite normalizado 1e-10, reconstrucción sigmoid <=1e-10. Árboles: límite normalizado 1e-6. El residual XGB absoluto puede exceder 1e-6 sin incumplir la cota escalada 1e-6*(1+abs(margen)). Las 190 parejas por modelo pasan Jaccard top3, Spearman, signos y TV; top6 es no informativo y no basta para acreditar estabilidad.

## Persistencia

Cada scientific/<familia>/explanations.npz contiene phi [20,245,6], base/model_output/reconstructed/residual/probability [20,245], IDs, commits, features, model identity y semillas. Carga abierta con numpy.load(...,allow_pickle=False). metadata.json fija escala/método/procedencia, global.json conserva estadísticas de cada repetición y 190 comparaciones, local.jsonl conserva 160 explicaciones locales por familia. scientific/identities.jsonl distingue orden temporal, foreground y orden local. No depende de modelos serializados ni de la sesión para leer/reconstruir las explicaciones.

Publicación: staging privado 0700, validación completa y fsync de archivos, renamex_np RENAME_EXCL atómico sin sobrescritura. No hay staging residual. MANIFEST.json cubre todos los archivos del conjunto científico. El contrato y hash de código fueron fijados antes de atribuir.

## Relectura

Otro proceso, sin cargar modelos ni SHAP, reabrió los arrays; verificó hashes, identidades, formas, finitud, bases, reconstrucciones, todos los residuales, agregados, estabilidad y locales. También contrastó la media absoluta mediante math.fsum. Resultado PASS. El archivo report_statistics.json contiene los datos de esta tabla global, derivados de archivos publicados.

## Resumen global primario (repetición 0; idénticas las veinte)

| Modelo | la | ld | nf | nd | ns | ent |
|---|---:|---:|---:|---:|---:|---:|
| LGB | 0.86941362857367943 | 0.19969049103215938 | 0.11020176646855259 | 0.095837681015773182 | 0.09839185276645003 | 0.097251479392954768 |
| LR | 0.075537523467402598 | 0.0034039828991773934 | 0.1816202261860532 | 0.18684622703076631 | 0.085969439683886331 | 0.49063801569798182 |
| RF | 0.088516528950008 | 0.033488702552024033 | 0.027080452835329775 | 0.017651878833875641 | 0.0072274069128571245 | 0.022932627692138656 |
| XGB | 0.75554724327307576 | 0.14642191643289729 | 0.043631999462614861 | 0.10540803643513699 | 0.051905341340437991 | 0.078500291226165642 |

Medias absolutas de atribución; no comparar magnitudes entre RF (probabilidad) y LR (logit)/XGB/LGB (margen nativo). No son contribuciones E2 de modalidades. No implican efectos causales.

## Controles y límites

Pipelines, referencia de 256 filas, media LR, recibo C y secuencias T1 verificados por hash. Probabilidades RAW de cada modelo coinciden por digest con el entorno aprobado. Transformadores congelados; sin fit, recalibración ni ajustes. TreeSHAP exacto, data=None, tree_path_dependent, approximate=False; clase positiva 1. LR analítico centrado. Salidas originales del modelo se evaluaron una vez y reutilizaron para comprobar las veinte atribuciones: 245 filas de predicción directa RF y 490 LR/XGB/LGB, no veinte inferencias nuevas. Cada árbol realizó 20 llamadas explicativas; cada familia produjo 4900 evaluaciones de atribución. Operaciones internas no medibles registradas null, no cero.

LGB emitió advertencia sklearn sobre ausencia de nombres en la matriz de entrada; se verificaron las seis columnas y la igualdad predictiva. NumPy 2.3.5 en el entorno explicativo aprobado; D histórico conserva 2.4.6. El PASS no demuestra robustez a otra referencia, perturbaciones, poblaciones o sistemas; es fidelidad y estabilidad numérica en el alcance congelado. Se utilizan pipelines reconstruidos.

No se abrió el contenedor mixto ni T2; no se ejecutó PROCESS, no se modificó TEXT/E2 ni auditorías históricas inventariadas. No se generaron figuras, ramas, commits ni PR. E1 CODE terminado; no se inicia otra fase.

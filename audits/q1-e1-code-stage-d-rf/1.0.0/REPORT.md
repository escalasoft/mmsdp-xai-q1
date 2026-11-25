# D-RF — Auditoría prospectiva independiente, versión 1.0.0

Dictamen: **D-RF PASS**. Ampliación autorizada exclusivamente a Random Forest. La auditoría D no fue ejecutada de nuevo, modificada ni invalidada; sus nueve archivos inventariados conservan sus hashes.

## Resultado

245 probabilidades RAW comparadas por identidad vinculada a commit y modelo, en orden temporal congelado: 245 coincidencias exactas; error absoluto máximo y medio 0; error relativo máximo 0; cero filas fuera de tolerancia; cero discrepancias de clasificación a 0.5; sin NaN/Inf. Los ocho casos locales congelados están incluidos. Las tres ejecuciones independientes presentan igualdad exacta del estado canónico y de los bytes float64 de probabilidades.

Tolerancias: absoluta <= 1e-12 y relativa <= 1e-10 cuando |referencia| >= 1e-8 (las 245 filas cumplen el dominio relativo). No se modificó la política. Clase positiva: 1, orden de clases [0,1].

## Artefactos y procedencia

Pipeline reconstruido: `audits/q1-xai-reconstruction-execution/1.0.0/objects/3950ddec4e97c3477e6e8d653474c6640aa790812cba52280ed472dc60dde998.pipeline.joblib`.

- SHA-256 pipeline: `3950ddec4e97c3477e6e8d653474c6640aa790812cba52280ed472dc60dde998`.
- Estado canónico: `07c0436d5229c4d4b5c6f91723e9c2d3bb6a6d427e09b8766631d02eb04822b4`.
- Identidad modelo confirmatorio: `a14a321bb3ed77d06b03a7ec3921181b60105448d0e4500244d4bacf084d245b`.
- Digest idéntico de probabilidades reconstruidas y referencia (float64): `634f0b19fe42280747645eca6eb14cb7e95195f91998ab389c8172393bdc0c69`.
- Salida T1 aceptada C: `16a30607ce34bb11703b8810f026fbdf0fd39725e2ee9774c55e2c0e9211e91c`.
- Evidencia T1: `audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz`, SHA-256 `eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8`.

Se verificaron el recibo PASS de C, procedencia, esquema de siete campos, tipos numéricos finitos, claves únicas y 245 identificadores únicos de 64 hexadecimales. Cada row_identifier se vinculó al commit mediante el esquema SHA-256 congelado. Coinciden el universo foreground de TEXT, el orden temporal del registro y el subconjunto de ocho casos; no se seleccionaron casos por resultados.

RF corresponde a ActiveMQ/CODE/FINAL_BASE, candidato RF_LEAF_5, población TRAIN congelada. Se verificaron los parámetros seleccionados (300 árboles, min_samples_leaf=5, max_features=sqrt, random_state=20260901, n_jobs=1, class_weight=null), clases, imputador y digests de los 300 árboles según la canonicalización histórica. La identidad confirmatoria está vinculada como consumidor del pipeline y coincide en población TRAIN y candidato. No se afirma identidad binaria con un ejecutable original histórico.

Las entradas float64 siguen el procedimiento histórico y el orden `la, ld, nf, nd, ns, ent`. Solo se llamó predict_proba del pipeline, que aplica sus transformadores ya ajustados; no se llamó fit ni se recalculó imputación.

La fuente predictiva es exclusivamente T1 aunque incluye otros proyectos/configuraciones. Se filtraron las líneas por ActiveMQ/C/RF antes de decodificar JSON. El parser decodifica el registro admitido completo, que también contiene etiquetas y campos calibrados; únicamente se retuvieron metadatos de identidad/procedencia y probabilidad RAW. No se usaron etiquetas ni resultados calibrados, ni se analizaron otros proyectos/modelos. No se abrió el contenedor CODE mixto ni se accedió a T2.

## Ejecución e invariancia

Tres procesos nuevos con nuevas cargas del mismo RF; no tres reconstrucciones o entrenamientos. Python 3.11.14, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.0, joblib 1.5.3; se comprobó también la coincidencia del runtime congelado para xgboost/lightgbm sin cargar sus pipelines. PYTHONDONTWRITEBYTECODE=1, PYTHONHASHSEED=20260901 y límites de hilos OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1.

Lock cooperativo compartido: dispositivo 16777225, inode 131286779. Todos los archivos históricos inventariados se verificaron antes/después y al cierre. Los hashes de D se preservan en prospective_record.json. No se guardaron copias de características ni arrays de predicciones por fila; se registraron métricas, versiones y digests.

## Limitaciones y detención

Sistema macOS 15.7.9 frente a 15.7.7 histórico: no se certifica igualdad de imagen del sistema, aunque dependencias predictivas y resultados coinciden. El lock es cooperativo, no un sandbox. La comprobación de invariancia abarca los archivos inventariados, no todo el repositorio. La equivalencia se limita a RAW RF en estas 245 filas, no a calibración, T2 o explicaciones.

No se ejecutaron calibración, E1 ni SHAP. D-RF terminada; cualquier actividad posterior requiere nuevas instrucciones.

Estado stderr por repetición: [false, false, false]. Los retornos fueron 0. Se registra digest de stderr, sin contenido; no se infiere clasificación de advertencias si existieran.

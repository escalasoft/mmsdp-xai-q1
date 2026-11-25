# E1-CODE — Etapa D, versión 1.0.0

Dictamen: D PASS. Autorización del usuario limitada a equivalencia predictiva RAW T1; no autoriza E1 ni SHAP.

## Resultado

| Familia | Comparados | Coincidencias exactas | Error absoluto máximo | Error absoluto medio | Error relativo máximo | Fuera de tolerancia | Discrepancias a 0.5 | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| LR | 245 | 245 | 0 | 0 | 0 | 0 | 0 | PASS |
| XGB | 245 | 245 | 0 | 0 | 0 | 0 | 0 | PASS |
| LGB | 245 | 245 | 0 | 0 | 0 | 0 | 0 | PASS |

No NaN/Inf. Los ocho casos locales están incluidos en cada comparación. Tres procesos independientes, con nuevas cargas de los mismos pipelines, produjeron igualdad exacta de estado canónico y bytes float64 de probabilidades. No se reconstruyó ni ajustó ningún modelo durante D.

## Identidad y representación

Se verificaron el recibo PASS de C, la procedencia y el SHA-256 de la salida aceptada. Las 245 identidades únicas coinciden exactamente, en orden, con el registro temporal T1. Cada identificador se vinculó al commit mediante SHA-256 de `apachejit-v2|apache/activemq|apache/activemq|<commit>`. El foreground conserva su universo y los ocho locales son un subconjunto; no se usó posición como sustituto de identidad.

Se validaron siete campos, identificadores hexadecimales de 64 caracteres, claves únicas y números JSON finitos. Conversión explícita a float64 en orden `la, ld, nf, nd, ns, ent`, conforme a `raw_features` histórico. Los archivos fuente y su representación léxica permanecen intactos.

Se comprobaron hashes binarios, parámetros seleccionados, clases [0,1], seis características y estado canónico completo: imputación, escalado LR, coeficientes LR, booster/configuración XGB y booster LGB. Se emplearon pipelines reconstruidos; no se afirma que sean los ejecutables originales.

## Evidencia confirmatoria

Fuente: `audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz`, SHA-256 `eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8`.

Es un archivo T1 exclusivo, aunque contiene otros proyectos/configuraciones T1. Su productor y control de integridad histórico documentan pertenencia T1 y ausencia de contaminación T2. Se filtraron líneas por ActiveMQ, configuración C y las tres familias antes de decodificar JSON. De los registros admitidos se retuvieron únicamente identidad, modalidad, procedencia del modelo y probabilidad RAW; las etiquetas y probabilidades calibradas coexistentes no se usaron para comparación, selección ni construcción de entradas. El parser JSON sí decodifica el registro admitido completo antes de proyectar los campos necesarios. Ningún resultado de otros proyectos/configuraciones fue analizado.

Las 245 filas de referencia por familia coinciden con la secuencia temporal. Su identidad de modelo pertenece a los consumidores congelados del pipeline; coinciden candidato y digest de población TRAIN. La clase positiva es 1. La decisión comparada se deriva de RAW >= 0.5, no del campo histórico de decisión calibrada.

## Política y reproducibilidad

Se aplicó la política congelada (hash en authorization.json): error absoluto <= 1e-12 Y relativo <= 1e-10 cuando |referencia| >= 1e-8; decisiones idénticas a 0.5; NaN/Inf prohibidos. El dominio relativo abarca las 245 filas por familia. La repetibilidad exacta se aplicó adicionalmente a T1, sin reinterpretar la evidencia TRAIN histórica.

Runtime: Python 3.11.14, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0, joblib 1.5.3. Controles: PYTHONDONTWRITEBYTECODE=1, PYTHONHASHSEED=20260901 y OMP/OPENBLAS/MKL/NUMEXPR/VECLIB a un hilo.

## Invariancia y limitaciones

Todos los archivos históricos leídos y registrados se verificaron nuevamente tras cada repetición y al cerrar la auditoría, sin cambios. No se reabrió el contenedor CODE mixto ni se accedió a T2. No hubo entrenamiento, calibración, SHAP ni explicaciones. No se persistieron características ni probabilidades por fila adicionales; solo digests y métricas.

Se mantuvo un lock cooperativo compartido, dispositivo 16777225/inode 131286779. No proporciona sandbox ni protección frente a procesos no cooperativos. La invariancia se refiere a los artefactos inventariados, no a un hash global del repositorio.

El sistema actual es macOS 15.7.9 x86_64 frente al histórico 15.7.7; las versiones predictivas coinciden y los resultados observados son exactos. No se certifica identidad de imagen de sistema operativo. Los workers terminaron con código 0 y validación PASS; hubo salida stderr, cuyo contenido no se conservó, por lo que no se certifica ausencia ni clasificación de advertencias.

Alcance del PASS: probabilidades RAW de los tres pipelines reconstruidos sobre estos 245 commits; no acredita calibración, otras particiones, otras familias ni explicaciones. Etapa D terminada. E1 CODE/SHAP requieren autorización posterior.

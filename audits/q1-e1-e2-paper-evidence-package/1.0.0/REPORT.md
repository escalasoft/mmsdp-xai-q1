# Paquete científico E1 CODE y enlaces E1 E2

Versión 1.0.0 — 2026-10-12.

**Dictamen del paquete: READY para incorporación editorial con alcance delimitado. Cobertura científica multimodal: PARTIAL.** Los componentes ausentes se conservan como limitaciones explícitas, no como resultados pendientes que deban inventarse. No se editó ni abrió el Word; no hubo operaciones Git.

## Entregables

| Elemento | Estado | Archivos |
|---|---|---|
| A — jerarquía local LR/C+T | READY | figures/figure_A.svg y .png |
| B — importancia global CODE, cuatro familias | READY; copia exacta auditada | figures/figure_B.svg y .png |
| C — cobertura de explicabilidad | READY; muestra exclusiones | figures/figure_C.svg y .png |
| D — extensión local LR/C+P+T | PARTIAL; suplemento explícito | figures/figure_D.svg y .png |
| Tabla A — cobertura, métodos, fidelidad y estabilidad | READY | tables/table_A_coverage.csv |
| Tabla B — estadísticas globales CODE completas | READY | tables/table_B_global_CODE.csv |
| Tabla C — correspondencia E1–E2 por instancia | READY | tables/table_C_alignment.csv |
| Tabla D — límites y alcance | READY | tables/table_D_limitations.csv |
| Documento técnico en inglés | READY | scientific_summary.md |
| Leyendas y trazabilidad de afirmaciones | READY | figure_captions.md; claim_evidence_matrix.csv |

`index.html` permite revisar el paquete localmente. `tables/README.md` ofrece versiones Markdown compactas editables. Se incluyen concordancia de rankings y solapamiento local como dos tablas suplementarias, sin multiplicar figuras redundantes.

## Fuentes y verificaciones

Las fuentes científicas son los resultados E1 CODE 1.0.0, su síntesis 1.0.0, E1 TEXT aceptado, cierre E2 1.1.0 y auditoría de alineación E1–E2 1.0.0. Se verificaron sus archivos consumidos contra manifiestos. Se revalidaron asimismo las referencias de integridad de la auditoría de alineación, incluido el informe de cierre PROCESS del 12-10-2026. `provenance.json` conserva rutas, hashes y manifiestos; las 63 referencias registradas incluyen referencias repetidas al mismo archivo y no se presentan como 63 archivos científicos únicos. No se certifican archivos no consumidos de esos paquetes.

Se verificaron los cuatro NPZ CODE y los NPZ TEXT aceptados mediante la cadena de integridad de alineación. La generación lee valores científicos persistidos: no carga modelos, matrices de características, datasets mixtos ni etiquetas. Se lee únicamente el CSV comprimido E2 ya publicado y exclusivo de T1, no el contenedor CODE original.

La figura A utiliza el primer caso del orden local E1 congelado, LR y C+T. La política se persistió antes de leer sus valores. Identidad: `e947927511796484e2ae0a066df7fa7b4800a578`; row identifier `cfcd7eb8ff0a4695715b0a05efb531fd837a3e65937f54b648c1c9919d19662b`. El caso no se seleccionó por resultados. La figura D conserva el mismo caso/familia en la instancia C+P+T.

Los datos JSON de A/D incluyen las seis atribuciones CODE, las 2.557 atribuciones TEXT con su vocabulario por columna, valores base, salidas, probabilidades, residuales y registro E2 de cada figura. Siete términos TEXT se muestran individualmente y los restantes 2.550 se agregan dentro del mismo nivel. El texto de tokens ausentes no se interpreta como presencia en el mensaje. No se suman ni propagan atribuciones entre niveles.

## Lectura independiente y reproducción

`independent_verification.json`: PASS. Un proceso separado volvió a leer fuentes y productos; verificó integridad, reconstrucciones locales, igualdad de entradas E2, nombres/columnas de tokens y las 24 medias absolutas mediante `math.fsum`. A/C/D se regeneraron desde sus JSON y produjeron SVG idénticos; B conserva exactamente los bytes SVG/PNG originales. `image_verification.json` registra la igualdad de píxeles de las nuevas imágenes regeneradas y su densidad. La revisión visual de las cuatro figuras comprobó etiquetas, signos, paneles, escalas y ausencia de solapamientos.

Reproducibilidad: `build_data.py` vuelve a materializar datos/tablas desde fuentes verificadas; `plot.py [directorio_salida]` genera SVG A/C/D desde JSON persistidos; `render.cjs [directorio]` genera PNG con Sharp; `verify.py` comprueba los resultados y regenera los SVG en `verification/`. Usar `.venv-xai-s56/bin/python -B` con `PYTHONDONTWRITEBYTECODE=1` y el Node registrado en los metadatos de renderizado. No ejecutar productores históricos de modelos/SHAP. Para una nueva publicación conservar esta versión y trabajar en una copia nueva. La reproducción gráfica depende del runtime y fuentes locales registrados; la geometría y datos vectoriales se preservan.

Los PNG nuevos A/C/D tienen 2.160 píxeles de ancho a 300 dpi (7,2 pulgadas). B conserva sus dimensiones originales, con 300 dpi. SVG mantiene texto y formas vectoriales. Se recomiendan dos columnas para A/D. El manifiesto sella todos los archivos entregados, excepto él mismo para evitar recursión.

## Resultados y límites

Se mantienen 245 commits, ocho locales y 20 repeticiones por familia CODE. Las 16 instancias E2 y 21 enlaces explicativos válidos conservan 5.145 comparaciones exactas; no son commits independientes adicionales. Las estadísticas globales y sus diferencias entre modelos se describen en el documento técnico, separando evidencia empírica, interpretación e hipótesis.

No se admite E1 PROCESS: `PROCESS_ANCESTRAL_UNPROVEN`. Esto limita la acreditación temporal y la cobertura explicativa completa, sin demostrar leakage observado ni invalidar automáticamente resultados históricos. RF TEXT tampoco dispone de atribuciones aceptadas. Sus motivos son distintos y se rotulan por separado.

E2 explica meta-logit y probabilidades RAW; no se presenta una probabilidad calibrada independiente para estas instancias. El número de repeticiones mide estabilidad determinista, no robustez a perturbaciones. No hay nuevas afirmaciones de precisión predictiva, causalidad, utilidad industrial, confianza medida ni generalización a los 14 proyectos. No se modifica el estado confirmatorio del framework.

## Parada

El paquete está listo para que una tarea editorial posterior utilice sus tablas, leyendas, figuras y texto en ChatGPT. Deben mantenerse los límites y etiquetas. No se modificó el manuscrito, ningún artefacto histórico, contrato o modelo. No se ejecutó inferencia, SHAP, calibración, entrenamiento, nueva extracción ni acceso T2. No se inicia otra fase.

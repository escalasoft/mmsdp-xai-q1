# E1 CODE — validación de entorno y referencia, 1.0.0

Dictamen técnico global: READY para solicitar ejecución E1, que permanece NO AUTORIZADA. LR/RF/XGB/LGB: ENV PASS, REF PASS, METHOD PASS.

## Referencia TRAIN

Snapshot independiente CODE TRAIN de 3675 filas; manifiesto completo verificado. Todas las filas son apache/activemq/TRAIN, sin campos de etiqueta. Identidades únicas enlazadas a commit, seis características finitas; digest de secuencia 3acfd7b19e5e059277ffaeed4751dee21ccf2e8ce8752ac67757b746d18db858 coincide con población congelada de los modelos. No se abrieron fuentes mixtas ni T2.

Se seleccionaron exactamente 256 filas, sin exclusiones, un estrato UNLABELLED, seed 20260901, purpose TRAIN_REFERENCE, SHA-256 de JSON compacto ordenado UTF8 sin LF, desempate por identidad. Referencia compartida en la representación imputada común, cuyos seis estadísticos son idénticos en las cuatro familias; el escalado LR es una transformación posterior, no una afirmación de igualdad de la representación escalada con los árboles. Se congelan representación, identidad, claves de selección, orden, filas originales y digests. No se usaron etiquetas o resultados para seleccionar.

La media LR de las 256 entradas transformadas se almacena en lr_transformed_mean.json, con descriptor float64 y vínculo al pipeline. Es exactamente reproducible también en .venv. Árboles mantienen data=None y conteos de rutas TRAIN persistidos; la selección explícita es solo diagnóstica para ellos. Las fechas del intervalo temporal no están en el snapshot; se registra null, sin inferir fechas ni abrir otra partición. La pertenencia TRAIN se verifica por hash y secuencia completa.

## Entornos y equivalencia

Inventario por metadatos en environment_inventory.json. Python 3.11.14; .venv usa NumPy 2.4.6 y no tiene SHAP; .venv-xai-s56 usa NumPy 2.3.5, SHAP 0.51.0, numba 0.62.1. Coinciden sklearn 1.9.0, SciPy 1.17.1, XGB 3.2.0, LGB 4.6.0 y joblib 1.5.3. No se instalaron ni actualizaron dependencias.

Excepción prospectiva autorizada para evaluar el runtime explicativo, sin reescribir contratos históricos. Se verificaron hashes y estados aprendidos completos de los cuatro pipelines. En tres procesos independientes del entorno explicativo: 245/245 coincidencias exactas por familia, ocho locales incluidos, errores absoluto máximo/medio y relativo máximo cero, cero discrepancias a 0.5, sin NaN/Inf. Mismos digests de probabilidades y estados que D/D-RF. No se alteraron esas auditorías ni sus dictámenes. Política aplicada: absoluto <=1e-12 y relativo <=1e-10 cuando |p_ref|>=1e-8.

La evidencia de referencia es el archivo exclusivo T1 confirmatorio. Solo se decodifican líneas filtradas por ActiveMQ/C y las cuatro familias; de esos registros se retienen identidad, RAW y procedencia. El registro admitido contiene también campos históricos de etiqueta/calibración que JSON decodifica pero que no se utilizan. No se usan fuentes mixtas.

## Compatibilidad de métodos

Se cargaron los modelos congelados, sin entrenar. Solo cuatro entradas inventadas fijadas prospectivamente fueron objeto de atribución; ningún valor real T1 se pasó a SHAP ni a descomposición analítica.

- LR: logit centrado respecto a la media TRAIN; residual máximo 2.220446049250313e-16 y comprobación sigmoid frente a probabilidad. Repetición independiente de LR documentada en reference_cross_runtime.json; la copia de array del primer script no se considera evidencia independiente.
- RF: TreeSHAP exacto, tree_path_dependent, raw, data=None, clase 1; forma (4,6,2) validada, selección explícita de clase; salida aditiva en probabilidad. Residual máximo 1.8041124150158794e-15. No se cambió a interventional ni a aproximación.
- XGB: mismo método, margen nativo; residual máximo 4.76837158203125e-7, dentro de 1e-6*(1+|margen|).
- LGB: mismo método, margen nativo; residual máximo 4.440892098500626e-15. Se registró categoría UserWarning; su texto no se conservó y no se afirma ausencia de advertencias.

En los árboles se repitió la llamada exacta dos veces con igualdad binaria, check_additivity=True y validación manual; no es un ensayo científico de estabilidad sobre T1. LR: residual <=1e-10*(1+|eta|), sigmoid <=1e-10. Árboles: <=1e-6*(1+|salida nativa|).

## Límites y preservación

METHOD PASS certifica funcionamiento en fixtures, no fidelidad ni estabilidad de las 245 filas. Persisten diferencias de NumPy/OS respecto al runtime histórico, aunque sin diferencia predictiva observada en T1; pruebas sintéticas limitadas y atribuciones dependientes de referencia/correlación. La selección TRAIN representa su referencia determinista, no la media de las 3675 filas. El lock es cooperativo, no sandbox.

No se ejecutaron explicaciones científicas, E2, calibración, ajustes ni entrenamiento. Invariancia verificada de archivos históricos inventariados. PROCESS sigue excluido de E1 por procedencia temporal no demostrada, sin invalidar su evidencia predictiva. Detención: E1 CODE requiere nueva autorización expresa y sus pruebas de fidelidad completas.

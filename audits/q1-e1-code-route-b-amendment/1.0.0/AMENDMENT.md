# Enmienda prospectiva E1-CODE — Ruta B, versión 1.0.0

Estado: APROBADA como modelo prospectivo de control de acceso por instrucción
expresa del usuario en este chat. Permiso C: NO AUTORIZADO.
La fecha de registro UTC consta en record.json. No se infiere una fecha distinta
para la decisión humana ni se atribuye una firma digital a este registro.

## Texto normativo

1. Esta enmienda se aplica exclusivamente a la futura extracción complementaria
CODE/ActiveMQ/T1, vinculada a E1 CODE LR/XGB/LGB. Es una excepción prospectiva
específica al protocolo de acceso. No modifica, sustituye ni reinterpreta
retrospectivamente contratos o evidencias históricos, incluidos C.1/C.2.
2. Para una futura ejecución expresamente autorizada se permite poseer y verificar
los bytes comprimidos completos de la fuente congelada y transferir la misma
captura íntegra verificada al extractor. Se reconoce que esos bytes codifican T2.
La aprobación presente NO permite realizar ahora ninguna de esas operaciones.
3. No se certifica ausencia absoluta de procesamiento anticipado interno por zlib.
El descompresor no debe devolver a la aplicación ningún byte posterior al LF
número 5.145. No se debe continuar ni hacer flush para verificar el trailer gzip.
4. Quedan prohibidas la interpretación, emisión, almacenamiento deliberado y
utilización científica de registros T2. No se autoriza examinarlos, resumirlos,
seleccionarlos ni utilizarlos. Tampoco se autoriza influencia de T2 sobre selección,
características, transformaciones, predicciones o explicaciones. El hash integral
preestablecido solo controla integridad; tiempos, errores y contadores no se usarán
para decisiones científicas ni adaptación retrospectiva.
5. La prohibición de almacenamiento deliberado cubre artefactos, logs, volcados
solicitados y buffers de aplicación destinados a registros T2. No afirma ausencia
de estado transitorio nativo, memoria comprimida completa o paginación del OS.
No se conservarán copias adicionales del gzip en disco.
6. Fuente única relativa al repositorio /Users/alex/MMSDP-XAI-Q1:
`audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz`.
SHA-256 esperado inmutable:
`42ec61d2adf3c708a4e55d856a7f3e95ee58464da022f84552c846379d796be3`.
Tamaño exacto: 4.985.060 bytes. Este registro no vuelve a leer ni hashear esa fuente.
7. Segmento objetivo base cero [4900, 5145): exactamente 245 identidades T1
congeladas y ocho casos locales previamente seleccionados. Orden de extracción:
temporal congelado. Orden foreground y orden de casos locales se conservan
separadamente. Las posiciones delimitan transporte, nunca sustituyen identidad.
8. Salida exclusiva de siete campos: row_identifier, la, ld, nf, nd, ns, ent.
Identificadores hexadecimales minúsculos de 64 caracteres y números JSON finitos;
sin booleanos, null, duplicados, campos adicionales ni conversiones silenciosas.
Preservar bytes originales de las líneas, incluidos LF y notación numérica.
El orden nominal de los campos no exige reserializar sus bytes originales.
9. Se mantienen límites de 5.145 líneas de transporte; 4.096 bytes por línea
incluido LF; 4 MiB de prefijo; 12 MiB solicitud IPC; 2 MiB respuesta IPC;
10 segundos de timeout del extractor. No se amplían después de observar datos.
10. No cambia ningún modelo, entrenamiento, calibración, partición, identidad o
caso. Transformación numérica e inferencia T1 y explicaciones E1/SHAP quedan
fuera del Permiso C y requieren autorizaciones independientes posteriores.

## Garantías exigibles y evidencia

El futuro coordinador debe verificar autorización, código aprobado y hashes de
identidades; capturar fuente regular no symlink mediante descriptor de solo lectura,
comprobar tamaño/metadatos estables y SHA integral; transferir esa misma captura
inmutable; exigir verificación independiente del hash en el worker; validar respuesta,
identidad temporal, esquema, hashes y contadores antes de publicar.

El contador actual denominado compressed_bytes_consumed debe documentarse o
corregirse como bytes suministrados; no demuestra consumo interno ni frontera T2.
El consumidor cooperativo solo recibirá la salida CODE T1 validada y no se ejecutará
durante C. El worker no recibirá ruta ni descriptor de fuente. Solo el coordinador
publicará salida completa y procedencia sin valores, vinculadas a la misma captura.

Staging 0700 en el mismo filesystem, archivos 0600, validación de bytes escritos,
fsync y renamex_np RENAME_EXCL para publicar el directorio completo sin sobrescribir.
Sin salida parcial aceptada. Los errores no expondrán registros. La procedencia
incluirá autorización, hashes de código/contratos/captura/salida, versiones,
identidades/órdenes y controles, sin características ni predicciones.

Las evidencias previas registran 19/19 en B y 38/38 en C.1. No se ejecutan pruebas
nuevas aquí. Respaldan escenarios sintéticos de corte de salida, identidad,
preservación, rechazo, integridad y publicación; no certifican ejecución real ni
comportamiento interno de zlib. Las garantías de producción siguen pendientes
hasta implementar, revisar y validar sintéticamente el coordinador.

## Modelo de confianza y limitaciones aceptadas

Ejecución local controlada, código revisado y procesos cooperativos. No hay
sandbox del OS, protección frente a procesos maliciosos del mismo UID ni techo
duro RSS demostrado. Hooks Python, bloqueo consultivo y permisos POSIX no suplen
esas garantías. Los límites lógicos no cubren toda la memoria Python/base64/nativa.
No se certifica frontera comprimida, ausencia de anticipación interna, paginación,
volcados automáticos del OS o durabilidad completa ante corte eléctrico. Un crash
puede dejar staging privado sin aceptar; no debe consumirse automáticamente.

La ausencia de exposición de salida no demuestra ausencia de procesamiento interno.
La validez científica exige que T2 no entre en entradas ni decisiones científicas.
Fidelidad criptográfica al artefacto no prueba por sí sola la validez temporal
original de cada métrica; PASS TRAIN no demuestra equivalencia T1.

## Puertas pendientes y detención

Antes de C: autorización separada para implementar y probar sintéticamente el
coordinador; revisión de fuente/destino y enlace captura-validación-publicación;
pruebas afectadas y regresión pertinente; fijación de hashes de código; revisión
humana de resultados y autorización expresa y versionada del Permiso C.
Esta enmienda no concede autorización de implementación ni de pruebas.

Preflight futuro: sesión controlada sin procesos científicos simultáneos; fuente
no modificada ni reemplazada; destino ausente; inspección de staging residual antes
y después sin mostrar valores. No borrar, reutilizar ni consumir residuos de estado
incierto automáticamente. No reintentar automáticamente.

FAIL y parada: discrepancia determinada de hash, tamaño, identidad, orden, tipos,
esquema, límites o integridad; publicación rechazada; exposición prohibida de T2.
INCONCLUSIVE y parada: cambios de fuente o consistencia no demostrable; timeout,
crash, recursos agotados o publicación/staging inciertos. Ningún resultado parcial
se acepta. No cambiar límites, universo o digest esperado ante un fallo.
Sin autorización vigente o evidencia suficiente, detenerse antes de leer la fuente.
Cualquier resolución y nuevo intento requieren revisión y autorización humanas.

## Alcance del registro

AMENDMENT RECORDED indica únicamente que la decisión prospectiva fue registrada.
No es C READY, PASS de extracción ni autorización C. Los hashes preservados y los
antecedentes están en record.json; no se modificó ninguno de esos archivos.

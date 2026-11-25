# E1-CODE C.2 — propuesta prospectiva 1.0.0

Estado: PROPUESTA, NO AUTORIZADA. Dictamen: NOT READY para autorización
incondicional de ejecución. Registro fechado: risk_acceptance.json, mismo directorio.
No se modifica ni reinterpreta ningún contrato histórico. La aceptación humana
del modelo confiable no concede Permiso C ni convierte garantías pendientes en PASS.

## Modelo de confianza y riesgos aceptados para revisión formal

Ejecución local controlada, procesos cooperativos y código revisado. No se promete
sandbox del sistema operativo, resistencia a procesos maliciosos del mismo UID ni
límite duro de RSS. Los permisos 0700/0600 y los hooks Python son controles del
flujo confiable; no aíslan al mismo usuario ni a código nativo hostil. El bloqueo
de archivo es consultivo. Límites lógicos y timeout siguen siendo obligatorios.
Las copias Python/base64 y memoria nativa no están cubiertas por un techo RSS.

## Frontera temporal: evidencia y límite de la evidencia

El lector captura el gzip completo y el extractor recibe esos bytes comprimidos
completos mediante IPC: ambos poseen bytes que codifican T2. Esta excepción física
debe aprobarse expresamente; no autoriza descomprimir, interpretar, emitir, registrar
ni utilizar registros T2. No existe una frontera de bytes comprimidos por partición.

El candidato solicita un byte descomprimido por llamada y deja de invocar al
decodificador al LF de la línea 5145. Las líneas anteriores al segmento se descartan
sin interpretar JSON. Las pruebas sintéticas demuestran corte de salida y ausencia
de centinelas T2 en salida/errores bajo el flujo probado. No prueban una frontera
interna de zlib ni ausencia de trabajo anticipado en buffers nativos. Tampoco
verifican el trailer gzip, que queda fuera del prefijo; la integridad integral se
apoya en el SHA-256 histórico. No se autoriza completar la descompresión para CRC.

La decisión de C.2 acepta riesgos de RSS y mismo UID, no esta incertidumbre temporal.
Antes de autorizar ejecución debe documentarse evidencia suficiente para la
prohibición literal de descompresión T2. Si no puede demostrarse, detenerse; no
redefinir por inferencia «no descomprimir» como «no emitir».

## Alcance propuesto del futuro Permiso C

Una sola ejecución controlada, sin reintento automático, exclusivamente para
recuperar CODE ActiveMQ/T1. Fuente única relativa a /Users/alex/MMSDP-XAI-Q1:

`audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz`

Tamaño exacto 4.985.060 bytes; SHA-256 inmutable:
`42ec61d2adf3c708a4e55d856a7f3e95ee58464da022f84552c846379d796be3`.

La autorización futura incluiría lectura binaria completa en memoria, comprobación
del hash de esa captura, transmisión de esa misma captura al extractor, recuperación
acotada y publicación. No conservar gzip adicional en disco, volcados, logs o
artefactos; las copias transitorias en RAM/IPC son explícitas. No se garantiza que
el sistema operativo jamás pagine memoria a disco.

Destino propuesto, que debe estar ausente, en el mismo repositorio:
`audits/q1-e1-code-permission-c/1.0.0/validated/`.
Únicos contenidos publicados juntos: `code_t1.jsonl` y `provenance.json`.
El registro previo de autorización y el resultado operativo sin valores deben
quedar fuera de ese destino, en su directorio padre, sin sobrescritura.

Transformación numérica, imputación, escalado, inferencia T1 y explicaciones E1
CODE quedan excluidos y requieren autorizaciones posteriores separadas. También
se excluyen modelos, etiquetas, predicciones, entrenamiento y selección retrospectiva.

## Identidad, orden y tipos

Los tres registros de identidad congelados, sus hashes y el digest de pertenencia
están fijados en risk_acceptance.json mediante la evidencia C.1. Antes de extraer
se deben volver a verificar los archivos de identidad contra esos hashes.
245 identidades únicas ActiveMQ/T1; ocho casos locales como subconjunto inmutable.
Extracción en orden temporal del registro T1. Orden foreground E1 TEXT y orden de
casos locales se conservan como metadatos distintos, sin reordenar la salida.
Identidad por row_identifier y correspondencia proyecto/commit, nunca por posición.
Las posiciones son únicamente frontera de transporte.

Exactamente siete campos: row_identifier, la, ld, nf, nd, ns, ent.
Identificador hexadecimal minúsculo de 64 caracteres. Seis números JSON finitos:
enteros o decimales/exponenciales validados con int/Decimal, sin coerción a float.
Rechazar booleanos, null, cadenas, contenedores, duplicados y campos adicionales.
Conservar bytes originales de cada línea admitida, incluido LF, orden de claves,
espacios y notación numérica. El orden nominal de campos no impone reserialización.
La representabilidad en el dtype predictivo es una comprobación posterior; un
decimal JSON finito no garantiza representabilidad en float64.

## Límites inmutables

| Control | Límite |
|---|---:|
| Captura comprimida | exactamente 4.985.060 bytes |
| Líneas de transporte | máximo 5.145 |
| Segmento objetivo, base cero | [4900, 5145) |
| Registros admitidos | exactamente 245 |
| Línea incluyendo LF | máximo 4.096 bytes |
| Prefijo descomprimido | máximo 4 MiB |
| Solicitud IPC | máximo 12 MiB |
| Respuesta IPC | máximo 2 MiB |
| Subproceso extractor | timeout 10 segundos |

El timeout probado es el del subproceso; no constituye una duración máxima de
captura/publicación ni una garantía de planificación de tiempo real del OS.
Ningún límite se amplía después de observar datos reales.

## Integridad, publicación y consumidor

Verificar ruta canónica, archivo regular no symlink, tamaño, descriptor O_NOFOLLOW,
identidad y metadatos antes/después, bloqueo consultivo y SHA de captura inmutable.
El worker vuelve a comprobar SHA/tamaño de los bytes recibidos. El coordinador
valida hash de fuente devuelto, hash de salida, esquema, cardinalidad e identidad
antes de publicar. La procedencia debe derivar de esta misma ejecución verificada,
no de un hash proporcionado separadamente por un llamador sin vínculo comprobado.

Staging privado 0700 en el mismo filesystem, archivos 0600. Validación completa en
memoria antes de escribir; fsync de archivos y staging, luego renamex_np RENAME_EXCL
del directorio completo. Nunca sobrescribir destino existente. Este rename es el
punto de publicación. Un staging incompleto nunca es un resultado aceptado.
Una interrupción puede dejar staging; durabilidad ante corte eléctrico no demostrada.

El consumidor científico cooperativo solo podrá recibir la salida validada de 245
filas. No se ejecutará durante C; no recibirá ruta, descriptor ni gzip comprimido.
Esto es una obligación operativa futura, no una integración E1 ya comprobada.

Procedencia sin valores: autorización/versiones, hashes del código ejecutado y
contratos, identidades/órdenes, hash y metadatos de captura, hash de salida, límites,
contadores de transporte, versiones Python/zlib y estados de controles. Sin
características, etiquetas, predicciones o registros en logs/excepciones.

## Medidas operativas y puertas humanas

1. Aprobar expresamente una versión final de esta propuesta después de resolver
   las dos puertas pendientes que se indican abajo. Esta propuesta no es esa aprobación.
2. Revisar y fijar hash del coordinador de producción y sus rutas antes de abrir
   la fuente. C.1 solo tiene captura/publicación sintéticas; extract_real rechaza.
   C.2 no habilita ni implementa ese coordinador. Cualquier cambio necesita revisión
   y validación sintética bajo autorización correspondiente, sin tocar datos reales.
3. Confirmar sesión local controlada, ausencia de procesos científicos simultáneos,
   productor inactivo y compromiso de no modificar/reemplazar fuente. Inspeccionar
   metadatos de staging residual y destino antes de empezar, sin volcar contenidos.
   Si existe residuo o destino, detenerse para resolución humana; no borrar ni reutilizar.
4. Registrar autorización y preflight sin valores antes de la única ejecución.
   Conservar los límites, no instalar dependencias ni modificar contratos.
5. Capturar, validar, extraer y publicar según controles revisados. No reintentar
   automáticamente ni cambiar hash esperado, universo o límites ante error.
6. Revisar destino/staging después sin mostrar valores. Ante interrupción o estado
   incierto no consumir ni borrar residuos automáticamente: registrar y detenerse.
7. Emitir resultado operativo sin valores y detenerse. Inferencia y E1 requieren
   nuevas aprobaciones; PASS de extracción no demuestra equivalencia predictiva T1.

## PASS, FAIL e INCONCLUSIVE

PASS: aprobación vigente y puertas cerradas; captura histórica exacta y consistente;
todos los límites, hashes, identidades, orden, esquema y LF correctos; 245 filas y
siete campos; salida/procedencia publicadas juntas sin sobrescritura; inspección
final y aislamiento operacional documentados; ninguna violación temporal observada.
PASS no convierte las limitaciones aceptadas en garantías técnicas demostradas.

FAIL: discrepancia determinada de hash/tamaño, identidad, orden, cardinalidad,
esquema/tipo/LF, límites o integridad; violación temporal/aislamiento comprobada;
destino existente o publicación rechazada. No aceptar resultado parcial ni reintentar.

INCONCLUSIVE: fuente cambia o consistencia no demostrable; timeout, crash, agotamiento
de recursos o interrupción que impidan concluir controles; incertidumbre sobre
publicación, staging o frontera temporal. Un destino visible tras un crash no se
consume automáticamente. Resolver por revisión humana, sin nueva extracción implícita.

## Dictamen

NOT READY para aprobar ejecución real sin condiciones: (1) falta revisar y fijar
la orquestación de producción que vincule captura, extracción y publicación;
(2) falta resolver la garantía literal de no descompresión interna T2, distinta
de la ausencia de emisión demostrada. El modelo confiable permite aceptar las
limitaciones RSS/mismo UID, pero no suprime estas puertas. Documento listo para
revisión humana; Permiso C permanece NO AUTORIZADO.

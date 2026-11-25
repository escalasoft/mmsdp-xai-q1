# Coordinador E1 CODE — versión 1.0.0

Autorización: desarrollo y fixtures inventados únicamente. Permiso C no autorizado.
Se añaden archivos; no se cambia el candidato C.1, sus tests ni las evidencias A,
B, C.1, C.2 o Ruta B. La enmienda Ruta B sigue siendo una decisión prospectiva.

## Entradas y versión aprobada

`production_contract.json` fija fuente, SHA histórico, tamaño, partición, destino,
lock cooperativo, hashes de registros de identidad, digest temporal y límites.
`release.json` fija hashes del coordinador, worker C.1 y contratos. Este manifiesto
es evidencia local de la versión sometida a validación, no una firma criptográfica
ni aprobación humana del Permiso C. El preflight y la comprobación anterior al
rename verifican sus referencias. El manifiesto mismo se hashea en procedencia.

`production_specification()` lee solo contratos. `prepare_production_plan()`
prepara metadatos y verifica identidades por el adaptador C.1; no abre el payload.
Esta preparación de identidades reales no se ejecuta en las pruebas nuevas.
`run_production()` rechaza siempre. El motor compartido también rechaza planes
PRODUCTION_NOT_AUTHORIZED antes de toda captura. No existe flag CLI, variable de
entorno ni parámetro público que habilite el Permiso C.

La ruta ejecutable `run_synthetic(root, fixture_contract_sha256)` solo admite una
carpeta canónica temporal e1-code-coordinator-synthetic-*. Fuente y destino tienen
nombres fijos; el contrato sellado de fixture permite únicamente datos inventados.
Esta inyección para pruebas no es una vía autorizada para adaptar/copiar la fuente
real. El tipo regular y nlink=1 rechazan enlaces simbólicos y duros en la captura.
No es defensa contra un usuario hostil capaz de cambiar código o copiar datos.

## Orquestación y frontera de confianza

1. Verificar hashes del código y contratos, contrato de fixture, esquema y límites;
   construir plan inmutable con órdenes temporal, foreground y locales separados.
2. Obtener LOCK_EX no bloqueante sobre scientific.lock, regular y preexistente;
   mantenerlo hasta concluir publicación. Todos los consumidores cooperativos
   deben mantener LOCK_SH sobre el mismo inode durante todo su uso. Nunca borrar
   ni reemplazar el lock. No se enumeran ni excluyen procesos no cooperativos.
3. Rechazar destino existente (también symlink) y cualquier .private-stage-* residual.
4. Capturar mediante un único descriptor O_RDONLY|O_NOFOLLOW, bloqueo consultivo,
   tamaño exacto y metadatos antes/después. Calcular SHA de los bytes inmutables.
5. Transferir esa misma captura al worker C.1, sin reabrir fuente. El worker comprueba
   tamaño/hash antes de decodificar. Mantiene max_length=1 y para al LF 5145, sin
   flush ni lectura del trailer. Las primeras 4900 líneas no se interpretan como JSON.
6. Revalidar en el coordinador captura, contenido base64 de respuesta, SHA de captura
   devuelto, SHA y longitud de salida, identidad temporal, 245 filas y siete campos.
   Se reutiliza el validador revisado C.1 en una ejecución separada, no un algoritmo
   de validación desarrollado independientemente.
7. Rechazar contadores de tipo incorrecto, líneas distintas de 5145, prefijo fuera
   de límites compatibles y cantidad comprimida suministrada fuera de rango. Los
   contadores se contrastan con límites y longitud de salida; NO se repite la
   descompresión para medirlos de nuevo. El worker revisado permanece confiable.
8. Construir procedencia exclusivamente con datos de esta ejecución validada;
   escribir output y procedencia en staging 0700, archivos 0600; releer y comprobar
   bytes/hash/esquema y ausencia de archivos adicionales; fsync archivos/directorio.
9. Antes de publicar comprobar otra vez metadatos de fuente, hash de contrato y
   versión aprobada. El cambio posterior a la captura no altera sus bytes, pero
   cualquier cambio detectado impide publicar conforme a la política operativa.
10. Publicar ambos archivos por un único renamex_np RENAME_EXCL. No sobrescribir,
    reintentar ni aceptar salidas parciales. Los fallos manejados limpian staging;
    cualquier residuo que persista bloquea el siguiente preflight.

## Límites y salida

4985060 bytes comprimidos; [4900,5145); 245 filas; 4096 bytes/línea incluido LF;
4 MiB prefijo; 12 MiB solicitud; 2 MiB respuesta; timeout worker 10 segundos.
Sin ampliaciones. El timeout no cubre toda captura/publicación ni garantiza tiempo
real de planificación del OS. Los límites IPC se apoyan en el worker cooperativo;
capture_output no constituye una cuota de memoria contra un worker hostil.

Salida: row_identifier, la, ld, nf, nd, ns, ent. Hexadecimal minúsculo de 64 caracteres;
int o Decimal finitos, sin coerción float. Conservar literalmente líneas y LF.
La adecuación posterior a dtype predictivo no se evalúa aquí.

Solo validated/code_t1.jsonl y validated/provenance.json son resultados publicables.
Ninguna copia adicional del gzip, TRAIN o VALIDATION. No se entregan registros por
logs ni errores. La API de coordinación devuelve únicamente el directorio publicado;
no entrega resultados parciales. Errores exteriores: COORDINATOR_REJECTED, sin datos.

El nombre histórico compressed_bytes_consumed se recibe del worker sin modificar
C.1 y se registra como compressed_bytes_supplied. Es cantidad suministrada, no una
medición exacta de consumo nativo ni frontera de partición comprimida.

## Evidencia y limitaciones

Las pruebas usan un solo miembro gzip sintético con cola T2 inventada y padding
hasta el tamaño contractual. Comprueban vínculo por identidad del objeto de captura,
hashes, bytes escritos, visibilidad atómica, centinelas, errores, concurrencia y timeout.
El padding sintético no es una afirmación sobre la organización del archivo real.

No sandbox del OS, no límite duro RSS, no garantía sobre procesamiento anticipado
interno zlib, paginación o volcados automáticos. Staging privado no aísla del mismo
UID. Crash o fallo eléctrico pueden dejar residuo o publicación de estado incierto;
no consumir ni reintentar automáticamente. Los permisos no sustituyen revisión
humana. No se garantiza durabilidad completa ante corte de alimentación.

La identidad del código se verifica en disco bajo el supuesto cooperativo: no se
certifica resistencia a sustitución hostil del intérprete, memoria o código cargado.
La aplicación científica real no se integra aquí; antes de C debe comprometerse al
lock común y permanecer inactiva durante extracción. No se da acceso al contenedor
al consumidor. El hash integral es control de integridad, no criterio científico.

## Regresión y restricción extract_real

Las 38 pruebas históricas se conservan byte por byte. La prueba C.1 número 15 llama
normalmente a extract_real para comprobar su rechazo. La autorización presente
prohíbe ejecutar esa función: se comprueba por AST que su único cuerpo es el rechazo
incondicional y se sustituye esa llamada por un rechazo simulado en la ejecución de
regresión. Las demás aserciones de esa prueba sí se ejecutan. El informe identifica
la cobertura adaptada; no debe describirse como 38 ejecuciones originales sin cambios.
No se invoca extract_real ni se extraen valores reales.

## Puertas anteriores a C

Revisión humana del código, contratos y resultados; aceptación explícita de la
sustitución de cobertura o autorización de ejecutar únicamente el guard de rechazo;
provisión futura del lock estable y compromiso cooperativo; autorización C nueva,
fechada y versionada. Habilitar el plan real requerirá una versión revisada del gate
actual y procedencia con alcance real, sin alterar constantes o identidades, más las
pruebas afectadas. Esa habilitación no se realiza ahora.

FAIL ante discrepancia determinada; INCONCLUSIVE ante timeout, crash, cambios de
fuente o estado incierto; ambos detienen y prohíben consumir salida parcial. Inferencia,
transformación, entrenamiento y SHAP siguen fuera de esta implementación.

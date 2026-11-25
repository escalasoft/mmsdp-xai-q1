# Corrección final de liberación — 1.1.0

Desarrollo y validación sintética autorizados. Permiso C NO AUTORIZADO. No se crea
permission_C.json de producción ni se invoca production_entry. No se modifican las
versiones 1.0.0 ni artefactos A/B/C.1/C.2/Ruta B.

## Implementación acotada

Nueva entrada sin argumentos e1_code_release.production_entry. Lee solo el contrato
fijo 1.1.0 y construye el contexto real; el motor exige una aprobación futura antes
de capturar fuente o cargar identidades reales. No utiliza ni habilita extract_real.
No hay opciones CLI/env para cambiar fuente, hash, filas, identidades o límites.

Ambas entradas (real y fixture inventado) usan el mismo _execute. Se reutilizan,
sin modificarlas, capture, verify_response y publish de coordinator 1.0.0 y decode,
validate_output, write_private, rename_exclusive de C.1. El worker nuevo solo cambia
el sobre de errores para preservar categorías seguras: NO es un extractor alternativo.

Secuencia: hashes de versión/contrato/inventario → aprobación → lock EX → segunda
verificación de aprobación y ausencia de destino/residuos/intentos → consumo exclusivo
del intento → identidades → captura única+SHA → worker+SHA → validación → staging,
verificación de bytes escritos y publicación atómica → recibo PASS.

## Fijación sin ciclo de hashes

1. Fijar código y contratos finales (incluido inventario). release.json contiene
   sus SHA-256; no contiene el hash de una autorización futura ni su propio hash.
2. Revisar resultados y fijar SHA-256 de release.json en la decisión humana futura.
3. Solo tras autorización C expresa, crear permission_C.json en el directorio
   padre del destino fijado. Vincula release_sha256, contract_sha256 e inventory_sha256.
   La aprobación no participa en los hashes del código ni del manifiesto.
4. Procedencia de ejecución incluye hash de aprobación, release y captura. Todo
   cambio de código/contrato requiere nueva revisión/manifiesto/aprobación; no editar
   evidencia histórica. El manifiesto local no es firma ni prueba de identidad humana.

## Registro futuro de aprobación, aún ausente

Ruta fija: audits/q1-e1-code-permission-c/1.0.0/permission_C.json.
Archivo regular único, sin symlink/hardlink; máximo 1 MiB. Esquema exacto:

- version: "1.0.0"; decision: "APPROVE_ONCE"; scope: "CODE_ACTIVEMQ_T1".
- approval_id: identificador hexadecimal minúsculo de 64 caracteres.
- release_sha256, contract_sha256, inventory_sha256: hashes finales aprobados.
- approved_at y expires_at: ISO-8601 con zona; ventana máxima de 300 segundos.
  Verificación humana inmediata; máximo 300 segundos desde aprobación, también
  al publicar. Esta ventana operativa no modifica límites científicos ni tolerancias.
- lock_device y lock_inode: enteros del lock estable preparado y verificado.
- all_consumers_stopped, no_other_scientific_processes, source_writer_stopped,
  staging_reviewed: exactamente true, tras comprobación humana, no valores por defecto.
- human_reviewer: identificador no vacío del revisor, máximo 128 caracteres.

No se entrega plantilla ejecutable aprobada. La herramienta no certifica la voluntad
humana por criptografía: el revisor registra solo una autorización efectivamente
concedida en el canal de gobierno y archiva su referencia en la auditoría. Modelo
cooperativo, sin resistencia a falsificación por un usuario malicioso con escritura.

## Un solo intento

Bajo LOCK_EX se crea attempt.json con O_EXCL, modo 0600, fsync archivo/directorio,
antes de abrir el payload. Existencia de attempt.json o completion.json impide toda
reutilización, incluso con otro approval_id. No se borran ni reemplazan esos registros.
Un crash, fallo o timeout consume el intento si ya se registró. Un preflight que
rechaza antes del consumo no ejecuta extracción y no reintenta automáticamente.

Salida visible sin completion.json PASS/accepted=true coincidente NO es consumible.
El recibo incluye authorization_sha256 y output_sha256 en PASS; el consumidor futuro
verifica esos vínculos antes de usar la salida. Si la escritura del recibo falla, se
retorna INCONCLUSIVE. Puede quedar un directorio íntegro pero no aceptado; no se borra
ni se declara PASS automáticamente. Crash durante la creación del recibo puede dejar
JSON incompleto, que también es no aceptado. Durabilidad total ante fallo eléctrico
no demostrada. No se duplica el gzip ni se persisten TRAIN/VALIDATION.

## Clasificación y privacidad

PASS solo tras publicación completa y recibo válido.
FAIL: rechazo determinista de aprobación, integridad, identidad, esquema, límites o
publicación validada como rechazada. INCONCLUSIVE: interrupción, cambio concurrente,
timeout, memoria/recursos, estado IO o publicación inciertos. Desconocidos se tratan
conservadoramente como INCONCLUSIVE. No se reconstruye causa a partir de valores.

Outcome contiene solo status, reason de vocabulario controlado y accepted. Worker
emite códigos fijos sin valores, traza ni mensaje original. No hay reintentos. Tras
fallo manejado antes del rename, publish limpia staging; si no lo logra, el residuo
bloquea el siguiente preflight. Una caída abrupta puede dejar staging privado.

## Consumidores y control inmediato humano

consumers.json cierra el inventario funcional: transformación CODE T1; inferencia
LR/XGB/LGB; SHAP E1 CODE; figuras/publicación científica. Todos deshabilitados durante
C. No existe integración productiva de esos consumidores todavía; no se promete
inventario automático exhaustivo de procesos del usuario.

Antes de una futura ejecución autorizada:
- Detener procesos y tareas científicas, notebooks, terminales y automatizaciones
  pertinentes bajo control del operador; confirmar que no pueden reiniciarse durante C.
- Confirmar inactividad del escritor de la fuente y prohibición de reemplazarla.
- Crear una sola vez scientific.lock regular 0600 en el directorio contractual,
  sin reemplazar inode existente; registrar device/inode en aprobación. No eliminarlo.
- Todo consumidor futuro mantiene LOCK_SH sobre ese mismo inode durante su vida;
  el coordinador mantiene LOCK_EX durante captura/publicación/recibo. El lock se
  adquiere no bloqueante: conflicto implica parada. No protege frente a no participantes.
- Inspeccionar metadatos de destino, attempt/completion y .private-stage-*; cualquier
  estado residual requiere revisión humana, sin borrar/reusar automáticamente.
- Solo después registrar atestación reciente y aprobación C. Si no se puede comprobar
  suficientemente la inactividad, NO crear aprobación; mantener C bloqueado.

Esta tarea prepara el mecanismo pero no crea lock ni aprobación de producción.

## Riesgos conservados y pruebas

No sandbox del OS; no límite duro RSS; sin certificación de anticipación interna
zlib; paginación/volcados OS no excluidos; permisos no aíslan del mismo UID; contadores
se contrastan con límites sin repetir descompresión. Ruta B exclusivamente E1 CODE.
La función devuelve cero bytes posteriores al LF 5145 según el decoder revisado;
no se afirma frontera comprimida ni interna. TRAIN PASS no demuestra equivalencia T1.

Las pruebas reales de este desarrollo usan únicamente fixtures inventados. La entrada
production_entry se revisa estáticamente, nunca se llama. El gate común se ensaya con
scope de producción y rutas inventadas, sin aprobación. La regresión C.1 test_15 usa
la adaptación documentada (AST + rechazo simulado) para no ejecutar extract_real.

La entrada preparada ya no requiere cambios de código para autorizar C: requiere
aprobación futura válida de esta versión y condiciones operativas satisfechas.
No se autoriza transformación, inferencia, calibración ni SHAP.

-- ─── VISTA 1: OEE por turno ───────────────────────────────────────────────
CREATE OR REPLACE VIEW vista_oee AS
SELECT
    t.id AS turno_id,
    t.fecha,
    t.turno,
    t.cedula_empleado,
    t.nombre_empleado,
    o.numero_orden,
    o.tipo_maquina,
    o.numero_maquina,
    o.codigo_producto,
    o.descripcion_producto,
    o.cantidad_producir,
    COALESCE(SUM(r.cantidad), 0) AS total_producido,
    COALESCE(SUM(p.minutos) FILTER (WHERE p.programada = false), 0) AS minutos_paradas_np,
    COALESCE(SUM(p.minutos) FILTER (WHERE p.programada = true), 0) AS minutos_paradas_p,
    COALESCE(SUM(d.cantidad), 0) AS total_desperdicios,
    CASE
        WHEN o.cantidad_producir > 0
        THEN ROUND((COALESCE(SUM(r.cantidad), 0)::numeric / o.cantidad_producir) * 100, 2)
        ELSE 0
    END AS rendimiento_pct
FROM turnos t
JOIN ordenes o ON t.orden_id = o.id
LEFT JOIN registros_produccion r ON r.turno_id = t.id
LEFT JOIN paradas p ON p.turno_id = t.id
LEFT JOIN desperdicios d ON d.turno_id = t.id
GROUP BY t.id, t.fecha, t.turno, t.cedula_empleado, t.nombre_empleado,
         o.numero_orden, o.tipo_maquina, o.numero_maquina,
         o.codigo_producto, o.descripcion_producto, o.cantidad_producir;

-- ─── VISTA 2: Producción diaria por máquina ───────────────────────────────
CREATE OR REPLACE VIEW vista_produccion_diaria AS
SELECT
    t.fecha,
    o.tipo_maquina,
    o.numero_maquina,
    o.codigo_producto,
    o.descripcion_producto,
    COUNT(DISTINCT t.id) AS turnos_trabajados,
    COALESCE(SUM(r.cantidad), 0) AS total_producido,
    COALESCE(SUM(d.cantidad), 0) AS total_desperdicios
FROM turnos t
JOIN ordenes o ON t.orden_id = o.id
LEFT JOIN registros_produccion r ON r.turno_id = t.id
LEFT JOIN desperdicios d ON d.turno_id = t.id
GROUP BY t.fecha, o.tipo_maquina, o.numero_maquina,
         o.codigo_producto, o.descripcion_producto;

-- ─── VISTA 3: Paradas por causa ───────────────────────────────────────────
CREATE OR REPLACE VIEW vista_paradas AS
SELECT
    t.fecha,
    o.tipo_maquina,
    o.numero_maquina,
    p.descripcion AS causa,
    p.programada,
    COUNT(*) AS cantidad_paradas,
    SUM(p.minutos) AS total_minutos
FROM paradas p
JOIN turnos t ON p.turno_id = t.id
JOIN ordenes o ON t.orden_id = o.id
GROUP BY t.fecha, o.tipo_maquina, o.numero_maquina, p.descripcion, p.programada;

-- ─── VISTA 4: Desperdicios por tipo ──────────────────────────────────────
CREATE OR REPLACE VIEW vista_desperdicios AS
SELECT
    t.fecha,
    o.tipo_maquina,
    o.numero_maquina,
    d.defecto,
    COUNT(*) AS cantidad_registros,
    SUM(d.cantidad) AS total_unidades
FROM desperdicios d
JOIN turnos t ON d.turno_id = t.id
JOIN ordenes o ON t.orden_id = o.id
GROUP BY t.fecha, o.tipo_maquina, o.numero_maquina, d.defecto;

-- ─── VISTA 5: MTTR/MTBF por máquina ──────────────────────────────────────
CREATE OR REPLACE VIEW vista_mantenimiento AS
SELECT
    o.tipo_maquina,
    o.numero_maquina,
    COUNT(p.id) AS total_paradas,
    ROUND(AVG(p.minutos)::numeric, 2) AS mttr_promedio,
    SUM(p.minutos) AS total_minutos_parada,
    p.descripcion AS causa_principal
FROM paradas p
JOIN turnos t ON p.turno_id = t.id
JOIN ordenes o ON t.orden_id = o.id
WHERE p.programada = false
GROUP BY o.tipo_maquina, o.numero_maquina, p.descripcion;

-- ─── VISTA 6: Ranking empleados ───────────────────────────────────────────
CREATE OR REPLACE VIEW vista_empleados AS
SELECT
    t.cedula_empleado,
    t.nombre_empleado,
    COUNT(t.id) AS turnos_trabajados,
    COALESCE(SUM(r.cantidad), 0) AS total_producido,
    ROUND(AVG(
        CASE
            WHEN o.cantidad_producir > 0
            THEN (COALESCE(rp.cant, 0)::numeric / o.cantidad_producir) * 100
            ELSE 0
        END
    ), 2) AS oee_promedio
FROM turnos t
JOIN ordenes o ON t.orden_id = o.id
LEFT JOIN registros_produccion r ON r.turno_id = t.id
LEFT JOIN (
    SELECT turno_id, SUM(cantidad) AS cant
    FROM registros_produccion
    GROUP BY turno_id
) rp ON rp.turno_id = t.id
GROUP BY t.cedula_empleado, t.nombre_empleado;
"""
excel_export.py — Generación de reportes Excel con métricas Lean Manufacturing
Indicadores: OEE, Disponibilidad, Rendimiento, Calidad, Tasa de desperdicio,
             Tiempo productivo, MTTR, MTBF, Unidades/hora real vs teórica
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from io import BytesIO
import openpyxl
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.series import DataPoint

from ..database import get_db
from ..models import Turno, RegistroProduccion, Parada, Desperdicio, Relevo, Orden

router = APIRouter(tags=["reportes"])


# ─────────────────────────────────────────────
# CONSTANTES LEAN
# ─────────────────────────────────────────────

MINUTOS_TURNO = 480          # 8 horas estándar
HORAS_TURNO   = 8


# ─────────────────────────────────────────────
# PALETA DE COLORES
# ─────────────────────────────────────────────

COLOR_HEADER_DARK   = "1F3864"   # azul oscuro
COLOR_HEADER_MID    = "2E75B6"   # azul medio
COLOR_HEADER_LIGHT  = "D6E4F0"   # azul muy claro
COLOR_VERDE_GOOD    = "E2EFDA"   # verde suave (bueno)
COLOR_ROJO_BAD      = "FFDFD6"   # rojo suave (malo)
COLOR_AMARILLO_WARN = "FFF2CC"   # amarillo (advertencia)
COLOR_GRIS_ROW      = "F2F2F2"   # gris alterno filas
COLOR_LEAN_ACCENT   = "375623"   # verde oscuro Lean
COLOR_TITULO_SHEET  = "16365C"   # título principal


# ─────────────────────────────────────────────
# HELPERS DE ESTILO
# ─────────────────────────────────────────────

def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)

def _font(bold=False, color="000000", size=11) -> Font:
    return Font(bold=bold, color=color, size=size, name="Calibri")

def _border_thin() -> Border:
    thin = Side(style="thin", color="BFBFBF")
    return Border(left=thin, right=thin, top=thin, bottom=thin)

def _center() -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def _left() -> Alignment:
    return Alignment(horizontal="left", vertical="center", wrap_text=True)

def _header_cell(ws, row, col, value, bg=COLOR_HEADER_MID, fg="FFFFFF", size=10, bold=True):
    cell = ws.cell(row=row, column=col, value=value)
    cell.fill = _fill(bg)
    cell.font = _font(bold=bold, color=fg, size=size)
    cell.alignment = _center()
    cell.border = _border_thin()
    return cell

def _data_cell(ws, row, col, value, bg=None, bold=False, align="center", num_format=None):
    cell = ws.cell(row=row, column=col, value=value)
    if bg:
        cell.fill = _fill(bg)
    cell.font = _font(bold=bold, size=10)
    cell.alignment = _center() if align == "center" else _left()
    cell.border = _border_thin()
    if num_format:
        cell.number_format = num_format
    return cell

def _set_col_widths(ws, widths: dict):
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width

def _color_oee(valor: float) -> str:
    """Semáforo OEE: verde ≥85%, amarillo ≥60%, rojo <60%"""
    if valor >= 85:
        return COLOR_VERDE_GOOD
    elif valor >= 60:
        return COLOR_AMARILLO_WARN
    return COLOR_ROJO_BAD


# ─────────────────────────────────────────────
# CÁLCULOS LEAN
# ─────────────────────────────────────────────

def calcular_metricas_lean(turno: Turno, orden: Orden) -> dict:
    """
    Calcula todos los KPIs Lean para un turno dado.
    OEE = Disponibilidad × Rendimiento × Calidad
    """
    total_producido  = sum(r.cantidad for r in turno.registros_produccion)
    total_desperdicio = sum(d.cantidad for d in turno.desperdicios)
    piezas_buenas    = total_producido - total_desperdicio

    # Paradas
    min_paradas_no_prog = sum(p.minutos for p in turno.paradas if not p.programada)
    min_paradas_prog    = sum(p.minutos for p in turno.paradas if p.programada)
    total_paradas_min   = min_paradas_no_prog + min_paradas_prog

    # Tiempo disponible real (descontando paradas no programadas)
    tiempo_disponible   = MINUTOS_TURNO - min_paradas_prog
    tiempo_operativo    = tiempo_disponible - min_paradas_no_prog

    # DISPONIBILIDAD: tiempo operativo / tiempo disponible
    disponibilidad = (tiempo_operativo / tiempo_disponible * 100) if tiempo_disponible > 0 else 0

    # RENDIMIENTO: producción real / producción teórica
    # Producción teórica = ciclos/min × cavidades × tiempo operativo
    ciclos_min = (orden.ciclos / 60) if orden.ciclos else 0
    cavidades  = orden.cavidades or 1
    produccion_teorica = ciclos_min * cavidades * tiempo_operativo
    rendimiento = (total_producido / produccion_teorica * 100) if produccion_teorica > 0 else 0
    rendimiento = min(rendimiento, 100)  # no puede superar 100%

    # CALIDAD: piezas buenas / total producido
    calidad = (piezas_buenas / total_producido * 100) if total_producido > 0 else 0

    # OEE
    oee = (disponibilidad * rendimiento * calidad) / 10000

    # MTTR y MTBF (en minutos)
    num_paradas = len([p for p in turno.paradas if not p.programada])
    mttr = (min_paradas_no_prog / num_paradas) if num_paradas > 0 else 0
    mtbf = ((tiempo_operativo - min_paradas_no_prog) / num_paradas) if num_paradas > 0 else tiempo_operativo

    # Velocidad real vs teórica
    horas_operativas = tiempo_operativo / 60
    uph_real    = (total_producido / horas_operativas) if horas_operativas > 0 else 0
    uph_teorica = (produccion_teorica / horas_operativas) if horas_operativas > 0 else 0

    return {
        "total_producido":       total_producido,
        "total_desperdicio":     total_desperdicio,
        "piezas_buenas":         piezas_buenas,
        "produccion_teorica":    round(produccion_teorica),
        "min_paradas_prog":      min_paradas_prog,
        "min_paradas_no_prog":   min_paradas_no_prog,
        "total_paradas_min":     total_paradas_min,
        "tiempo_disponible":     tiempo_disponible,
        "tiempo_operativo":      tiempo_operativo,
        "disponibilidad":        round(disponibilidad, 1),
        "rendimiento":           round(rendimiento, 1),
        "calidad":               round(calidad, 1),
        "oee":                   round(oee, 1),
        "mttr":                  round(mttr, 1),
        "mtbf":                  round(mtbf, 1),
        "uph_real":              round(uph_real, 1),
        "uph_teorica":           round(uph_teorica, 1),
        "num_paradas":           len(turno.paradas),
        "num_paradas_no_prog":   num_paradas,
        "tasa_desperdicio":      round((total_desperdicio / total_producido * 100) if total_producido > 0 else 0, 2),
    }


# ─────────────────────────────────────────────
# HOJA: RESUMEN EJECUTIVO LEAN
# ─────────────────────────────────────────────

def _hoja_resumen_lean(wb, turnos: list, ordenes_map: dict, titulo: str):
    ws = wb.create_sheet("Resumen Lean")

    # Título
    ws.merge_cells("A1:R1")
    c = ws["A1"]
    c.value = titulo
    c.fill = _fill(COLOR_TITULO_SHEET)
    c.font = _font(bold=True, color="FFFFFF", size=14)
    c.alignment = _center()
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:R2")
    c = ws["A2"]
    c.value = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Metodología: Lean Manufacturing"
    c.fill = _fill(COLOR_HEADER_LIGHT)
    c.font = _font(color=COLOR_LEAN_ACCENT, size=10)
    c.alignment = _center()

    # Headers
    headers = [
        "Orden", "Producto", "Fecha", "Turno", "Empleado",
        "Prod. Real", "Prod. Teórica", "Piezas Buenas", "Desperdicio",
        "T. Paradas\n(min)", "Paradas\nNo Prog.",
        "Disponib.\n%", "Rendim.\n%", "Calidad\n%", "OEE\n%",
        "UPH Real", "UPH Teórica", "MTTR\n(min)"
    ]
    for col, h in enumerate(headers, 1):
        _header_cell(ws, 3, col, h, bg=COLOR_HEADER_DARK, size=9)
    ws.row_dimensions[3].height = 35

    # Datos
    for i, turno in enumerate(turnos, 4):
        orden = ordenes_map.get(turno.orden_id)
        if not orden:
            continue
        m = calcular_metricas_lean(turno, orden)
        bg = COLOR_GRIS_ROW if i % 2 == 0 else None

        _data_cell(ws, i, 1,  orden.numero_orden,       bg=bg, align="left")
        _data_cell(ws, i, 2,  orden.descripcion_producto, bg=bg, align="left")
        _data_cell(ws, i, 3,  turno.fecha,               bg=bg)
        _data_cell(ws, i, 4,  turno.turno,               bg=bg)
        _data_cell(ws, i, 5,  turno.nombre_empleado,     bg=bg, align="left")
        _data_cell(ws, i, 6,  m["total_producido"],      bg=bg)
        _data_cell(ws, i, 7,  m["produccion_teorica"],   bg=bg)
        _data_cell(ws, i, 8,  m["piezas_buenas"],        bg=bg)
        _data_cell(ws, i, 9,  m["total_desperdicio"],    bg=_color_oee(100 - m["tasa_desperdicio"]))
        _data_cell(ws, i, 10, m["total_paradas_min"],    bg=bg)
        _data_cell(ws, i, 11, m["num_paradas_no_prog"],  bg=bg)
        _data_cell(ws, i, 12, m["disponibilidad"],       bg=_color_oee(m["disponibilidad"]), num_format='0.0"%"')
        _data_cell(ws, i, 13, m["rendimiento"],          bg=_color_oee(m["rendimiento"]),    num_format='0.0"%"')
        _data_cell(ws, i, 14, m["calidad"],              bg=_color_oee(m["calidad"]),         num_format='0.0"%"')
        _data_cell(ws, i, 15, m["oee"],                  bg=_color_oee(m["oee"]),             num_format='0.0"%"', bold=True)
        _data_cell(ws, i, 16, m["uph_real"],             bg=bg)
        _data_cell(ws, i, 17, m["uph_teorica"],          bg=bg)
        _data_cell(ws, i, 18, m["mttr"],                 bg=bg)

    _set_col_widths(ws, {
        "A":12, "B":22, "C":11, "D":7, "E":18,
        "F":10, "G":10, "H":10, "I":10, "J":10,
        "K":10, "L":10, "M":10, "N":10, "O":10,
        "P":10, "Q":10, "R":10
    })
    ws.freeze_panes = "A4"
    return ws


# ─────────────────────────────────────────────
# HOJA: DETALLE DE TURNO
# ─────────────────────────────────────────────

def _hoja_detalle_turno(wb, turno: Turno, orden: Orden, metricas: dict):
    nombre = f"Turno {turno.id}"
    ws = wb.create_sheet(nombre)

    # Encabezado de información
    info = [
        ("Orden",        orden.numero_orden),
        ("Producto",     orden.descripcion_producto),
        ("Material",     orden.material),
        ("Tipo máquina", orden.tipo_maquina),
        ("Máquina N°",   orden.numero_maquina),
        ("Fecha",        turno.fecha),
        ("Turno",        turno.turno),
        ("Empleado",     turno.nombre_empleado),
        ("Cédula",       turno.cedula_empleado),
        ("Hora inicio",  turno.hora_inicio),
        ("Hora fin",     turno.hora_fin or "En curso"),
        ("Líder",        orden.nombre_lider),
    ]
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = f"DETALLE DE TURNO — {orden.numero_orden} / {turno.fecha} / Turno {turno.turno}"
    c.fill = _fill(COLOR_TITULO_SHEET)
    c.font = _font(bold=True, color="FFFFFF", size=12)
    c.alignment = _center()
    ws.row_dimensions[1].height = 25

    for i, (label, val) in enumerate(info, 2):
        ws.cell(row=i, column=1, value=label).font = _font(bold=True, size=10)
        ws.cell(row=i, column=1).fill = _fill(COLOR_HEADER_LIGHT)
        ws.cell(row=i, column=1).border = _border_thin()
        ws.cell(row=i, column=2, value=val).border = _border_thin()
        ws.cell(row=i, column=2).font = _font(size=10)

    # KPIs Lean en bloque
    fila_kpi = len(info) + 3
    ws.merge_cells(f"A{fila_kpi}:F{fila_kpi}")
    c = ws.cell(row=fila_kpi, column=1, value="KPIs LEAN MANUFACTURING")
    c.fill = _fill(COLOR_LEAN_ACCENT)
    c.font = _font(bold=True, color="FFFFFF", size=11)
    c.alignment = _center()

    kpis = [
        ("Producción real",       metricas["total_producido"],    "uds"),
        ("Producción teórica",    metricas["produccion_teorica"], "uds"),
        ("Piezas buenas",         metricas["piezas_buenas"],      "uds"),
        ("Total desperdicio",     metricas["total_desperdicio"],  "uds"),
        ("Tasa de desperdicio",   metricas["tasa_desperdicio"],   "%"),
        ("Tiempo operativo",      metricas["tiempo_operativo"],   "min"),
        ("Tiempo paradas",        metricas["total_paradas_min"],  "min"),
        ("Paradas no prog.",      metricas["num_paradas_no_prog"],"eventos"),
        ("DISPONIBILIDAD",        metricas["disponibilidad"],     "%"),
        ("RENDIMIENTO",           metricas["rendimiento"],        "%"),
        ("CALIDAD",               metricas["calidad"],            "%"),
        ("OEE",                   metricas["oee"],                "%"),
        ("UPH real",              metricas["uph_real"],           "uds/h"),
        ("UPH teórica",           metricas["uph_teorica"],        "uds/h"),
        ("MTTR",                  metricas["mttr"],               "min"),
        ("MTBF",                  metricas["mtbf"],               "min"),
    ]

    for j, (label, val, unidad) in enumerate(kpis):
        r = fila_kpi + 1 + j
        ws.cell(row=r, column=1, value=label).font  = _font(bold=True, size=10)
        ws.cell(row=r, column=1).fill   = _fill(COLOR_HEADER_LIGHT)
        ws.cell(row=r, column=1).border = _border_thin()
        c_val = ws.cell(row=r, column=2, value=val)
        c_val.font   = _font(bold=(label in ["OEE","DISPONIBILIDAD","RENDIMIENTO","CALIDAD"]), size=10)
        c_val.border = _border_thin()
        if label in ["OEE","DISPONIBILIDAD","RENDIMIENTO","CALIDAD"]:
            c_val.fill = _fill(_color_oee(val))
        ws.cell(row=r, column=3, value=unidad).font   = _font(size=9, color="666666")
        ws.cell(row=r, column=3).border = _border_thin()

    # Producción por hora
    fila_ph = fila_kpi + len(kpis) + 3
    ws.merge_cells(f"A{fila_ph}:C{fila_ph}")
    c = ws.cell(row=fila_ph, column=1, value="PRODUCCIÓN POR HORA")
    c.fill = _fill(COLOR_HEADER_DARK)
    c.font = _font(bold=True, color="FFFFFF", size=11)
    c.alignment = _center()

    for col, h in enumerate(["Hora", "Cantidad", "% vs Teórico/h"], 1):
        _header_cell(ws, fila_ph+1, col, h, bg=COLOR_HEADER_MID)

    teorico_hora = metricas["uph_teorica"]
    for k, reg in enumerate(sorted(turno.registros_produccion, key=lambda x: x.hora), fila_ph+2):
        pct = round(reg.cantidad / teorico_hora * 100, 1) if teorico_hora > 0 else 0
        bg_h = COLOR_VERDE_GOOD if pct >= 85 else (COLOR_AMARILLO_WARN if pct >= 60 else COLOR_ROJO_BAD)
        _data_cell(ws, k, 1, reg.hora)
        _data_cell(ws, k, 2, reg.cantidad)
        _data_cell(ws, k, 3, pct, bg=bg_h, num_format='0.0"%"')

    # Paradas
    fila_par = fila_ph + len(turno.registros_produccion) + 4
    ws.merge_cells(f"A{fila_par}:E{fila_par}")
    c = ws.cell(row=fila_par, column=1, value="REGISTRO DE PARADAS")
    c.fill = _fill(COLOR_HEADER_DARK)
    c.font = _font(bold=True, color="FFFFFF", size=11)
    c.alignment = _center()

    for col, h in enumerate(["Código", "Descripción", "Minutos", "Programada", "Tipo"], 1):
        _header_cell(ws, fila_par+1, col, h, bg=COLOR_HEADER_MID)

    for k, p in enumerate(turno.paradas, fila_par+2):
        tipo = "Programada" if p.programada else "No programada"
        bg_p = COLOR_VERDE_GOOD if p.programada else COLOR_ROJO_BAD
        _data_cell(ws, k, 1, p.codigo)
        _data_cell(ws, k, 2, p.descripcion, align="left")
        _data_cell(ws, k, 3, p.minutos)
        _data_cell(ws, k, 4, "Sí" if p.programada else "No")
        _data_cell(ws, k, 5, tipo, bg=bg_p)

    # Desperdicios
    fila_des = fila_par + len(turno.paradas) + 4
    ws.merge_cells(f"A{fila_des}:D{fila_des}")
    c = ws.cell(row=fila_des, column=1, value="REGISTRO DE DESPERDICIOS")
    c.fill = _fill(COLOR_HEADER_DARK)
    c.font = _font(bold=True, color="FFFFFF", size=11)
    c.alignment = _center()

    for col, h in enumerate(["Código", "Tipo de Defecto", "Cantidad", "% del Total"], 1):
        _header_cell(ws, fila_des+1, col, h, bg=COLOR_HEADER_MID)

    for k, d in enumerate(turno.desperdicios, fila_des+2):
        pct_d = round(d.cantidad / metricas["total_producido"] * 100, 2) if metricas["total_producido"] > 0 else 0
        _data_cell(ws, k, 1, d.codigo)
        _data_cell(ws, k, 2, d.defecto, align="left")
        _data_cell(ws, k, 3, d.cantidad)
        _data_cell(ws, k, 4, pct_d, bg=COLOR_ROJO_BAD if pct_d > 2 else None, num_format='0.00"%"')

    # Relevos
    if turno.relevos:
        fila_rel = fila_des + len(turno.desperdicios) + 4
        ws.merge_cells(f"A{fila_rel}:D{fila_rel}")
        c = ws.cell(row=fila_rel, column=1, value="RELEVOS")
        c.fill = _fill(COLOR_HEADER_DARK)
        c.font = _font(bold=True, color="FFFFFF", size=11)
        c.alignment = _center()
        for col, h in enumerate(["Empleado", "Cédula", "Hora inicio", "Hora fin"], 1):
            _header_cell(ws, fila_rel+1, col, h, bg=COLOR_HEADER_MID)
        for k, r in enumerate(turno.relevos, fila_rel+2):
            _data_cell(ws, k, 1, r.nombre_empleado, align="left")
            _data_cell(ws, k, 2, r.cedula_empleado)
            _data_cell(ws, k, 3, r.hora_inicio)
            _data_cell(ws, k, 4, r.hora_fin or "En curso")

    _set_col_widths(ws, {"A":18, "B":28, "C":14, "D":14, "E":16})
    ws.freeze_panes = "A2"


# ─────────────────────────────────────────────
# HOJA: ANÁLISIS DE PARADAS (Pareto Lean)
# ─────────────────────────────────────────────

def _hoja_pareto_paradas(wb, turnos: list):
    ws = wb.create_sheet("Pareto Paradas")

    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = "ANÁLISIS PARETO DE PARADAS — Lean Manufacturing"
    c.fill = _fill(COLOR_TITULO_SHEET)
    c.font = _font(bold=True, color="FFFFFF", size=12)
    c.alignment = _center()

    # Agrupar paradas por descripción
    paradas_agrup: dict = {}
    for turno in turnos:
        for p in turno.paradas:
            key = f"{p.codigo} - {p.descripcion}"
            if key not in paradas_agrup:
                paradas_agrup[key] = {"minutos": 0, "ocurrencias": 0, "programada": p.programada}
            paradas_agrup[key]["minutos"]     += p.minutos
            paradas_agrup[key]["ocurrencias"] += 1

    sorted_paradas = sorted(paradas_agrup.items(), key=lambda x: x[1]["minutos"], reverse=True)
    total_min = sum(v["minutos"] for _, v in sorted_paradas)

    for col, h in enumerate(["Parada", "Ocurrencias", "Minutos totales", "% del total", "% Acumulado", "Tipo"], 1):
        _header_cell(ws, 2, col, h, bg=COLOR_HEADER_DARK)

    acumulado = 0
    for i, (key, data) in enumerate(sorted_paradas, 3):
        pct      = round(data["minutos"] / total_min * 100, 1) if total_min > 0 else 0
        acumulado += pct
        tipo     = "Programada" if data["programada"] else "No programada"
        bg_acum  = COLOR_VERDE_GOOD if acumulado <= 80 else COLOR_AMARILLO_WARN
        _data_cell(ws, i, 1, key,                   align="left")
        _data_cell(ws, i, 2, data["ocurrencias"])
        _data_cell(ws, i, 3, data["minutos"])
        _data_cell(ws, i, 4, pct,                   num_format='0.0"%"')
        _data_cell(ws, i, 5, round(acumulado, 1),   bg=bg_acum, num_format='0.0"%"')
        _data_cell(ws, i, 6, tipo,                  bg=COLOR_ROJO_BAD if not data["programada"] else COLOR_VERDE_GOOD)

    # Gráfico Pareto
    if sorted_paradas:
        chart = BarChart()
        chart.type = "col"
        chart.title = "Pareto de Paradas (minutos)"
        chart.y_axis.title = "Minutos"
        chart.x_axis.title = "Tipo de parada"
        chart.style = 10
        chart.width = 20
        chart.height = 12

        n = len(sorted_paradas)
        data_ref = Reference(ws, min_col=3, min_row=2, max_row=2+n)
        cats_ref = Reference(ws, min_col=1, min_row=3, max_row=2+n)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        ws.add_chart(chart, f"H3")

    _set_col_widths(ws, {"A":35, "B":13, "C":15, "D":12, "E":13, "F":14})


# ─────────────────────────────────────────────
# HOJA: ANÁLISIS DE DESPERDICIOS
# ─────────────────────────────────────────────

def _hoja_desperdicios(wb, turnos: list):
    ws = wb.create_sheet("Análisis Desperdicios")

    ws.merge_cells("A1:E1")
    c = ws["A1"]
    c.value = "ANÁLISIS DE DESPERDICIOS — Lean Manufacturing"
    c.fill = _fill(COLOR_TITULO_SHEET)
    c.font = _font(bold=True, color="FFFFFF", size=12)
    c.alignment = _center()

    des_agrup: dict = {}
    total_prod = 0
    for turno in turnos:
        total_prod += sum(r.cantidad for r in turno.registros_produccion)
        for d in turno.desperdicios:
            key = d.defecto
            if key not in des_agrup:
                des_agrup[key] = {"cantidad": 0, "ocurrencias": 0}
            des_agrup[key]["cantidad"]    += d.cantidad
            des_agrup[key]["ocurrencias"] += 1

    sorted_des = sorted(des_agrup.items(), key=lambda x: x[1]["cantidad"], reverse=True)
    total_des  = sum(v["cantidad"] for _, v in sorted_des)

    for col, h in enumerate(["Defecto", "Ocurrencias", "Cantidad total", "% del desperdicio", "% de producción"], 1):
        _header_cell(ws, 2, col, h, bg=COLOR_HEADER_DARK)

    acumulado = 0
    for i, (defecto, data) in enumerate(sorted_des, 3):
        pct_des  = round(data["cantidad"] / total_des  * 100, 1) if total_des  > 0 else 0
        pct_prod = round(data["cantidad"] / total_prod * 100, 2) if total_prod > 0 else 0
        acumulado += pct_des
        _data_cell(ws, i, 1, defecto,              align="left")
        _data_cell(ws, i, 2, data["ocurrencias"])
        _data_cell(ws, i, 3, data["cantidad"])
        _data_cell(ws, i, 4, pct_des,              num_format='0.0"%"')
        _data_cell(ws, i, 5, pct_prod,             bg=COLOR_ROJO_BAD if pct_prod > 2 else COLOR_VERDE_GOOD, num_format='0.00"%"')

    _set_col_widths(ws, {"A":30, "B":13, "C":15, "D":18, "E":18})


# ─────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────

def _generar_libro(turnos: list, db: Session, titulo: str) -> BytesIO:
    if not turnos:
        raise HTTPException(status_code=404, detail="No hay datos para exportar")

    orden_ids = list({t.orden_id for t in turnos})
    ordenes   = db.query(Orden).filter(Orden.id.in_(orden_ids)).all()
    ordenes_map = {o.id: o for o in ordenes}

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # quitar hoja vacía por defecto

    # 1. Resumen Lean
    _hoja_resumen_lean(wb, turnos, ordenes_map, titulo)

    # 2. Detalle por cada turno
    for turno in turnos:
        orden = ordenes_map.get(turno.orden_id)
        if orden:
            m = calcular_metricas_lean(turno, orden)
            _hoja_detalle_turno(wb, turno, orden, m)

    # 3. Pareto paradas
    _hoja_pareto_paradas(wb, turnos)

    # 4. Análisis desperdicios
    _hoja_desperdicios(wb, turnos)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _response_excel(output: BytesIO, filename: str) -> StreamingResponse:
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/reporte/turno/{turno_id}")
def reporte_por_turno(turno_id: int, db: Session = Depends(get_db)):
    """Exporta el reporte completo Lean de un turno específico."""
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    orden = db.query(Orden).filter(Orden.id == turno.orden_id).first()
    titulo = f"Reporte Turno {turno_id} — {turno.fecha}"
    output = _generar_libro([turno], db, titulo)
    filename = f"reporte_turno_{turno_id}_{turno.fecha}.xlsx"
    return _response_excel(output, filename)


@router.get("/reporte/orden/{orden_id}")
def reporte_por_orden(orden_id: int, db: Session = Depends(get_db)):
    """Exporta el reporte completo Lean de todos los turnos de una orden."""
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    turnos = db.query(Turno).filter(Turno.orden_id == orden_id).all()
    titulo = f"Reporte Orden {orden.numero_orden} — {orden.descripcion_producto}"
    output = _generar_libro(turnos, db, titulo)
    filename = f"reporte_orden_{orden.numero_orden}.xlsx"
    return _response_excel(output, filename)


@router.get("/reporte/fechas")
def reporte_por_fechas(
    fecha_inicio: str,
    fecha_fin: str,
    db: Session = Depends(get_db)
):
    """
    Exporta reporte Lean de todos los turnos en un rango de fechas.
    Formato fechas: YYYY-MM-DD
    """
    turnos = db.query(Turno).filter(
        Turno.fecha >= fecha_inicio,
        Turno.fecha <= fecha_fin
    ).all()

    if not turnos:
        raise HTTPException(status_code=404, detail="No hay turnos en ese rango de fechas")

    titulo = f"Reporte Lean — {fecha_inicio} al {fecha_fin}"
    output = _generar_libro(turnos, db, titulo)
    filename = f"reporte_{fecha_inicio}_{fecha_fin}.xlsx"
    return _response_excel(output, filename)

@router.get("/empleados-mes")
def reporte_empleados_mes(
    mes: int,
    anio: int,
    db: Session = Depends(get_db)
):
    from app.models.models import Turno, RegistroProduccion, Parada, Orden
    from datetime import datetime, date
    import calendar

    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])

    turnos = db.query(Turno).filter(
        Turno.fecha >= str(primer_dia),
        Turno.fecha <= str(ultimo_dia),
        Turno.hora_fin != None
    ).all()

    empleados = {}

    for t in turnos:
        ced = t.cedula_empleado
        orden = db.query(Orden).filter(Orden.id == t.orden_id).first()
        if not orden:
            continue

        try:
            fmt = "%H:%M"
            h_inicio = datetime.strptime(t.hora_inicio[:5], fmt)
            h_fin = datetime.strptime(t.hora_fin[:5], fmt)
            tiempo_real = (h_fin - h_inicio).seconds / 3600
        except:
            tiempo_real = 0

        tiempo_programado = float(orden.ciclos or 12)
        registros = db.query(RegistroProduccion).filter(RegistroProduccion.turno_id == t.id).all()
        contador = sum(r.cantidad for r in registros)
        paradas = db.query(Parada).filter(Parada.turno_id == t.id).all()
        min_np = sum(p.minutos for p in paradas if not p.programada)

        tiempo_disponible = tiempo_real - (min_np / 60)
        disponibilidad = (tiempo_disponible / tiempo_programado) if tiempo_programado > 0 else 0

        ciclo = float(orden.ciclos or 0)
        cavidades = int(orden.cavidades or 1)
        prod_planeada = (tiempo_programado * 3600 / ciclo * cavidades) if ciclo > 0 else 0
        rendimiento = (contador / prod_planeada) if prod_planeada > 0 else 0
        oee = disponibilidad * rendimiento * 100

        if ced not in empleados:
            empleados[ced] = {
                "cedula": ced,
                "nombre": t.nombre_empleado,
                "turnos": 0,
                "oee_sum": 0.0,
                "disp_sum": 0.0,
                "rend_sum": 0.0,
                "total_produccion": 0,
            }

        empleados[ced]["turnos"] += 1
        empleados[ced]["oee_sum"] += oee
        empleados[ced]["disp_sum"] += disponibilidad * 100
        empleados[ced]["rend_sum"] += rendimiento * 100
        empleados[ced]["total_produccion"] += contador

    resultado = []
    for emp in empleados.values():
        n = emp["turnos"]
        oee_prom = emp["oee_sum"] / n if n > 0 else 0
        resultado.append({
            "cedula": emp["cedula"],
            "nombre": emp["nombre"],
            "turnos": n,
            "oee_promedio": round(oee_prom, 2),
            "disponibilidad_promedio": round(emp["disp_sum"] / n, 2) if n > 0 else 0,
            "rendimiento_promedio": round(emp["rend_sum"] / n, 2) if n > 0 else 0,
            "total_produccion": emp["total_produccion"],
            "bono": oee_prom >= 94.0,
        })

    return sorted(resultado, key=lambda x: x["oee_promedio"], reverse=True)
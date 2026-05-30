"""
reporte_pptx.py
Genera el reporte mensual PowerPoint al estilo Inverfarma,
usando el template original (fondo, logo, diseño).
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import date
import calendar
from io import BytesIO
import os
import uuid
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor


from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from ..database import get_db
from ..models import Turno, Orden, Parada, Desperdicio, RegistroProduccion

from ..oee_calc import calcular_oee_turno
from .excel_export import _calcular_datos_mes, KW_MAQUINA

router = APIRouter(tags=["reporte-pptx"])

# ── Store de trabajos PPTX en background ─────────────────────────────────────
_pptx_jobs: dict = {}
_executor = ThreadPoolExecutor(max_workers=2)

def _generar_pptx_background(job_id: str, mes: int, anio: int, datos: dict, datos_anuales: dict, tarifa: float, filename: str):
    """Corre en un thread separado — no bloquea el servidor."""
    try:
        _pptx_jobs[job_id]["estado"] = "generando"
        output = _build_pptx(mes, anio, datos, datos_anuales, tarifa)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
        tmp.write(output.getvalue())
        tmp.close()
        _pptx_jobs[job_id]["estado"]  = "listo"
        _pptx_jobs[job_id]["archivo"] = tmp.name
    except Exception as e:
        _pptx_jobs[job_id]["estado"] = "error"
        _pptx_jobs[job_id]["error"]  = str(e)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR    = os.path.normpath(os.path.join(BASE_DIR, "..", "assets"))
TEMPLATE_PATH = os.path.join(ASSETS_DIR, "template_inverfarma.pptx")
LOGO_PATH     = os.path.join(ASSETS_DIR, "logo_inverfarma.png")

MESES_ES = [
    '', 'ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO',
    'JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'
]

TIPO_LABEL = {
    'inyeccion': 'Inyección', 'soplado': 'Soplado',
    'linea_copro': 'L. Copro', 'linea_orina': 'L. Orina',
    'acondicionamiento': 'Acondicionamiento',
}
TIPO_COLOR_HEX = {
    'inyeccion': '#4472C4', 'soplado': '#70AD47',
    'linea_copro': '#FF8C00', 'linea_orina': '#7030A0',
    'acondicionamiento': '#1D9E75',
}
TIPO_KEYS = ['inyeccion', 'soplado', 'linea_copro', 'linea_orina', 'acondicionamiento']
TIPOS_COSTO = ['inyeccion', 'soplado']

TARIFA_DEFAULT = 800  # COP/kWh — tarifa industrial Colombia 2026 aprox


# ── Datos históricos anuales (para gráficas de tendencia por tipo) ─────────────
def _datos_anuales(anio: int, mes_actual: int, db: Session) -> dict:
    """Calcula OEE y PTEE promedio por tipo para cada mes del año hasta mes_actual."""
    resultado = {tk: {} for tk in TIPO_KEYS}

    primer_dia = str(date(anio, 1, 1))
    ultimo_dia = str(date(anio, mes_actual, calendar.monthrange(anio, mes_actual)[1]))

    turnos = db.query(Turno).filter(
        Turno.fecha >= primer_dia,
        Turno.fecha <= ultimo_dia,
    ).all()

    orden_ids   = list({t.orden_id for t in turnos})
    ordenes_map = {o.id: o for o in db.query(Orden).filter(Orden.id.in_(orden_ids)).all()}

    acum: dict = {}
    for turno in turnos:
        orden = ordenes_map.get(turno.orden_id)
        if not orden:
            continue
        kpis = calcular_oee_turno(turno, orden)
        oee  = kpis["oee"]
        ptee = kpis.get("ptee", 0.0)
        tipo = orden.tipo_maquina
        num  = str(orden.numero_maquina)
        tk   = "linea_copro" if tipo == "linea" and num == "1" else \
               "linea_orina" if tipo == "linea" and num == "2" else tipo
        try:
            m = int(turno.fecha[5:7])
        except:
            continue
        if tk not in acum:
            acum[tk] = {}
        if m not in acum[tk]:
            acum[tk][m] = {"oees": [], "ptees": []}
        if oee > 0:
            acum[tk][m]["oees"].append(oee)
            acum[tk][m]["ptees"].append(ptee)

    mavg = lambda arr: round(sum(arr)/len(arr), 2) if arr else None
    for tk in TIPO_KEYS:
        resultado[tk] = {
            m: {
                "oee":  mavg(acum.get(tk, {}).get(m, {}).get("oees", [])),
                "ptee": mavg(acum.get(tk, {}).get(m, {}).get("ptees", [])),
            }
            for m in range(1, mes_actual + 1)
        }
    return resultado


# ── Gráficas matplotlib ───────────────────────────────────────────────────────
def _setup_ax(ax, fig):
    fig.patch.set_facecolor('#EBEBEB')
    ax.set_facecolor('#DCDCDC')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#aaa')
    ax.spines['bottom'].set_color('#aaa')
    ax.grid(True, axis='y', color='white', linewidth=0.9, alpha=0.9)


def _chart_oee_tipo(titulo: str, datos_anuales: dict, tipo_key: str, mes_actual: int) -> BytesIO:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    meses_corto = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    fig, ax = plt.subplots(figsize=(9.4, 5.0), dpi=120)
    _setup_ax(ax, fig)

    y_oee  = [datos_anuales.get(tipo_key, {}).get(m, {}).get("oee")  for m in range(1, 13)]
    y_ptee = [datos_anuales.get(tipo_key, {}).get(m, {}).get("ptee") for m in range(1, 13)]

    x_oee  = [i for i, v in enumerate(y_oee)  if v is not None]
    x_ptee = [i for i, v in enumerate(y_ptee) if v is not None]
    yv_oee  = [v for v in y_oee  if v is not None]
    yv_ptee = [v for v in y_ptee if v is not None]

    if x_oee:
        ax.plot(x_oee, yv_oee, 's-', color='#70AD47', linewidth=2.5,
                markersize=7, label='OEE', zorder=3)
        for xi, yi in zip(x_oee, yv_oee):
            ax.annotate(f'{yi:.1f}', (xi, yi),
                        textcoords='offset points', xytext=(0, 9),
                        ha='center', fontsize=8, fontweight='bold', color='#2e6b0e')
    if x_ptee:
        ax.plot(x_ptee, yv_ptee, 'o--', color='#4472C4', linewidth=1.8,
                markersize=5, label='PTEE', zorder=2, alpha=0.8)

    if yv_oee:
        prom = sum(yv_oee)/len(yv_oee)
        ax.axhline(prom, color='#C00000', linewidth=1.0, linestyle=':', alpha=0.7)
        ax.text(11.5, prom+0.5, f'Prom\n{prom:.1f}%', fontsize=7, color='#C00000', ha='right')

    ax.set_xticks(range(12))
    ax.set_xticklabels(meses_corto, fontsize=9)
    all_vals = yv_oee + yv_ptee
    if all_vals:
        margin = max(8, (max(all_vals)-min(all_vals))*0.3)
        ax.set_ylim(max(0, min(all_vals)-margin), min(120, max(all_vals)+margin))
    else:
        ax.set_ylim(0, 110)
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=10)
    if x_oee or x_ptee:
        ax.legend(loc='lower right', fontsize=9, framealpha=0.8)

    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_oee_resumen(oee_por_tipo: dict, mes_nombre: str, anio: int) -> BytesIO:
    """Gráfica de barras con OEE de todos los tipos en el mes."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.4, 5.0), dpi=120)
    _setup_ax(ax, fig)

    tipos  = [tk for tk in TIPO_KEYS if oee_por_tipo.get(tk) is not None]
    labels = [TIPO_LABEL.get(tk, tk) for tk in tipos]
    values = [oee_por_tipo[tk] for tk in tipos]
    colors = [TIPO_COLOR_HEX.get(tk, '#888') for tk in tipos]

    bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=0.5, width=0.5)
    for bar, val in zip(bars, values):
        color_txt = '#2e6b0e' if val >= 85 else '#a32d2d' if val < 65 else '#7a5c00'
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.8,
                f'{val:.1f}%', ha='center', fontsize=11, fontweight='bold', color=color_txt)

    ax.axhline(85, color='#70AD47', linewidth=1.2, linestyle='--', alpha=0.7, label='Meta 85%')
    ax.set_ylim(0, max(values + [90]) + 15 if values else 110)
    ax.set_ylabel('OEE (%)', fontsize=10)
    ax.legend(fontsize=9, framealpha=0.8)
    ax.set_title(f'RESUMEN OEE GENERAL — {mes_nombre} {anio}', fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_comparativa_mes(comparativa: dict, mes_nombre: str, mes_ant_nombre: str, anio: int) -> BytesIO:
    """Gráfica comparativa OEE mes actual vs mes anterior."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    tipos  = [tk for tk in TIPO_KEYS if comparativa.get(tk, {}).get('actual') is not None
              or comparativa.get(tk, {}).get('anterior') is not None]
    labels = [TIPO_LABEL.get(tk, tk) for tk in tipos]
    actual   = [comparativa[tk].get('actual')   or 0 for tk in tipos]
    anterior = [comparativa[tk].get('anterior') or 0 for tk in tipos]

    fig, ax = plt.subplots(figsize=(9.4, 5.0), dpi=120)
    _setup_ax(ax, fig)

    x     = np.arange(len(labels))
    width = 0.35
    b1 = ax.bar(x - width/2, anterior, width, label=mes_ant_nombre, color='#9DC3E6', edgecolor='white')
    b2 = ax.bar(x + width/2, actual,   width, label=mes_nombre,     color='#4472C4', edgecolor='white')

    for bar, val in zip(b1, anterior):
        if val: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, f'{val:.1f}%', ha='center', fontsize=8, color='#555')
    for bar, val, tk in zip(b2, actual, tipos):
        if val:
            delta = comparativa[tk].get('delta') or 0
            sign  = '+' if delta >= 0 else ''
            color = '#2e6b0e' if delta >= 0 else '#a32d2d'
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                    f'{val:.1f}%\n({sign}{delta:.1f}pp)', ha='center', fontsize=7.5, color=color, fontweight='bold')

    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, max(actual + anterior + [90]) + 20)
    ax.set_ylabel('OEE (%)', fontsize=10)
    ax.legend(fontsize=9, framealpha=0.8)
    ax.set_title(f'COMPARATIVA OEE — {mes_ant_nombre} vs {mes_nombre} {anio}', fontsize=12, fontweight='bold', pad=10)

    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_ptee(oee_por_tipo: dict, ptee_por_tipo: dict, mes_nombre: str, anio: int) -> BytesIO:
    """Gráfica PTEE vs OEE por tipo."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    tipos  = [tk for tk in TIPO_KEYS if oee_por_tipo.get(tk) is not None]
    labels = [TIPO_LABEL.get(tk, tk) for tk in tipos]
    oees   = [oee_por_tipo[tk]  or 0 for tk in tipos]
    ptees  = [ptee_por_tipo.get(tk) or 0 for tk in tipos]

    fig, ax = plt.subplots(figsize=(9.4, 5.0), dpi=120)
    _setup_ax(ax, fig)

    x     = np.arange(len(labels))
    width = 0.35
    ax.bar(x - width/2, oees,  width, label='OEE',  color='#4472C4', edgecolor='white')
    ax.bar(x + width/2, ptees, width, label='PTEE', color='#1D9E75', edgecolor='white')

    for xi, (o, p) in enumerate(zip(oees, ptees)):
        if o: ax.text(xi - width/2, o + 0.5, f'{o:.1f}%', ha='center', fontsize=8, color='#4472C4', fontweight='bold')
        if p: ax.text(xi + width/2, p + 0.5, f'{p:.1f}%', ha='center', fontsize=8, color='#1D9E75', fontweight='bold')

    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, max(oees + ptees + [90]) + 15)
    ax.set_ylabel('%', fontsize=10)
    ax.legend(fontsize=9, framealpha=0.8)
    ax.set_title(f'OEE vs PTEE — {mes_nombre} {anio}', fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_consumo(consumo: dict, mes_nombre: str, anio: int) -> BytesIO:
    """Gráfica de consumo energético kWh por máquina."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    datos = sorted(consumo.items(), key=lambda x: x[1]['kwh'], reverse=True)
    if not datos:
        fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=120)
        ax.text(0.5, 0.5, 'Sin datos de consumo', ha='center', va='center', fontsize=12, color='#888', transform=ax.transAxes)
        ax.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(9.4, 4.8), dpi=120)
        _setup_ax(ax, fig)
        color_map = {"inyeccion":"#4472C4","soplado":"#70AD47","linea":"#FF8C00","acondicionamiento":"#1D9E75"}
        labels = [d[1]['label'] for d in datos]
        values = [d[1]['kwh']   for d in datos]
        colors = [color_map.get(d[1]['tipo'], '#888') for d in datos]
        bars = ax.bar(labels, values, color=colors, edgecolor='white')
        mx = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+mx*0.01,
                    f'{val:,.0f}', ha='center', fontsize=9, fontweight='bold')
        ax.set_ylabel('kWh', fontsize=10)
        plt.xticks(rotation=20, ha='right', fontsize=8)

    ax.set_title(f'CONSUMO ENERGÉTICO (kWh) — {mes_nombre} {anio}', fontsize=12, fontweight='bold', pad=10)
    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_costo_kg(consumo: dict, kg_mes: dict, tarifa: float, mes_nombre: str, anio: int) -> BytesIO:
    """Gráfica de costo energético por kg — solo inyección y soplado."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    # Construir datos: solo tipos costo con kg > 0
    filas = []
    for key, d in consumo.items():
        if d['tipo'] not in TIPOS_COSTO:
            continue
        kg = kg_mes.get(f"{d['tipo']}_{d['num']}", 0)
        if kg <= 0:
            continue
        costo_total = d['kwh'] * tarifa
        costo_kg    = costo_total / kg
        filas.append({
            'label':       d['label'],
            'tipo':        d['tipo'],
            'kwh':         d['kwh'],
            'kg':          kg,
            'costo_total': costo_total,
            'costo_kg':    costo_kg,
        })

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.8), dpi=120)
    fig.patch.set_facecolor('#EBEBEB')
    fig.suptitle(
        f'COSTO ENERGÉTICO POR kg — {mes_nombre} {anio}  |  Tarifa: ${tarifa:,.0f} COP/kWh',
        fontsize=11, fontweight='bold'
    )

    color_map = {"inyeccion": "#4472C4", "soplado": "#70AD47"}

    if not filas:
        for ax in axes:
            ax.text(0.5, 0.5, 'Sin datos de kg procesados\npara Inyección/Soplado',
                    ha='center', va='center', fontsize=11, color='#888', transform=ax.transAxes)
            ax.axis('off')
    else:
        labels      = [f['label']     for f in filas]
        costo_total = [f['costo_total'] for f in filas]
        costo_kg    = [f['costo_kg']    for f in filas]
        colors      = [color_map.get(f['tipo'], '#888') for f in filas]

        # Izquierda: Costo total por máquina
        ax1 = axes[0]
        _setup_ax(ax1, fig)
        bars1 = ax1.bar(labels, costo_total, color=colors, edgecolor='white')
        mx1 = max(costo_total) if costo_total else 1
        for bar, val in zip(bars1, costo_total):
            ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+mx1*0.02,
                     f'${val:,.0f}', ha='center', fontsize=8, fontweight='bold')
        ax1.set_ylabel('COP', fontsize=9)
        ax1.set_title('Costo total energía', fontsize=10, fontweight='bold')
        plt.setp(ax1.get_xticklabels(), rotation=20, ha='right', fontsize=8)

        # Derecha: $/kg por máquina
        ax2 = axes[1]
        _setup_ax(ax2, fig)
        bars2 = ax2.bar(labels, costo_kg, color=colors, edgecolor='white')
        mx2 = max(costo_kg) if costo_kg else 1
        for bar, val in zip(bars2, costo_kg):
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+mx2*0.02,
                     f'${val:,.0f}/kg', ha='center', fontsize=8.5, fontweight='bold', color='#a32d2d')
        ax2.set_ylabel('COP/kg', fontsize=9)
        ax2.set_title('Costo por kg procesado', fontsize=10, fontweight='bold')
        plt.setp(ax2.get_xticklabels(), rotation=20, ha='right', fontsize=8)

        # Línea promedio en $/kg
        if len(costo_kg) > 1:
            prom_kg = sum(f['costo_total'] for f in filas) / sum(f['kg'] for f in filas)
            ax2.axhline(prom_kg, color='#C00000', linewidth=1.2, linestyle='--', alpha=0.8)
            ax2.text(len(labels)-0.5, prom_kg + mx2*0.03,
                     f'Prom ${prom_kg:,.0f}', fontsize=7.5, color='#C00000', ha='right')

    plt.tight_layout(pad=1.0)
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_kg(kg_mes: dict, mes_nombre: str, anio: int) -> BytesIO:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.4, 4.8), dpi=120)
    _setup_ax(ax, fig)

    if not kg_mes:
        ax.text(0.5, 0.5, 'Sin datos de peso pieza configurado', ha='center', va='center', fontsize=12, color='#888', transform=ax.transAxes)
        ax.axis('off')
    else:
        color_map = {"inyeccion":"#4472C4","soplado":"#70AD47","linea":"#FF8C00","acondicionamiento":"#1D9E75"}
        labels = list(kg_mes.keys())
        values = list(kg_mes.values())
        colors = [color_map.get(k.split("_")[0], "#888") for k in labels]
        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(values)*0.01,
                    f'{val:,.1f}kg', ha='center', fontsize=8.5, fontweight='bold')
        ax.set_ylabel('kg procesados', fontsize=9)
        plt.xticks(rotation=20, ha='right', fontsize=8)

    ax.set_title(f'RESINA TRANSFORMADA — {mes_nombre} {anio}', fontsize=12, fontweight='bold', pad=10)
    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_desperdicios(desp: dict, mes_nombre: str, anio: int) -> BytesIO:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.4, 4.8), dpi=120)
    _setup_ax(ax, fig)

    if not desp:
        ax.text(0.5, 0.5, 'Sin registros de desperdicio', ha='center', va='center', fontsize=12, color='#888', transform=ax.transAxes)
        ax.axis('off')
    else:
        sorted_d = sorted(desp.items(), key=lambda x: x[1], reverse=True)[:10]
        labels   = [d[0][:28] for d in sorted_d]
        values   = [d[1] for d in sorted_d]
        bars = ax.barh(labels, values, color='#4472C4', edgecolor='white')
        for bar, val in zip(bars, values):
            ax.text(val+max(values)*0.01, bar.get_y()+bar.get_height()/2, f'{val:,}', va='center', fontsize=8.5, fontweight='bold')
        ax.invert_yaxis()
        ax.set_xlabel('Unidades', fontsize=9)

    ax.set_title(f'DESPERDICIO — {mes_nombre} {anio}', fontsize=12, fontweight='bold', pad=10)
    plt.tight_layout(pad=0.8)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


def _chart_mttr(mttr_data: dict, mes_nombre: str, anio: int) -> BytesIO:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(9.4, 4.2), dpi=120)
    fig.patch.set_facecolor('#EBEBEB')
    fig.suptitle(f'MTTR · MTBF · DISPONIBILIDAD — {mes_nombre} {anio}', fontsize=10, fontweight='bold')

    label_map = {"inyeccion":"Inyección","soplado":"Soplado","linea_copro":"L.Copro","linea_orina":"L.Orina","acondicionamiento":"Acond."}

    if not mttr_data:
        for ax in axes:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=10, color='#888', transform=ax.transAxes)
            ax.axis('off')
    else:
        tipos  = list(mttr_data.keys())
        labels = [label_map.get(t, t) for t in tipos]
        configs = [
            (axes[0], [mttr_data[t]["mttr"] for t in tipos], '#E06C00', 'MTTR (min)', 'T. medio reparar'),
            (axes[1], [mttr_data[t]["mtbf"] for t in tipos], '#4472C4', 'MTBF (min)', 'T. medio entre fallas'),
            (axes[2], [mttr_data[t]["disp"] for t in tipos], '#70AD47', 'Disp. (%)',  'Disponibilidad'),
        ]
        for ax, vals, color, ylabel, subtitle in configs:
            _setup_ax(ax, fig)
            bars = ax.bar(range(len(labels)), vals, color=color, edgecolor='white')
            mx = max(vals) if vals else 1
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+mx*0.03,
                        f'{val:.1f}', ha='center', fontsize=7.5, fontweight='bold')
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, fontsize=7, rotation=20, ha='right')
            ax.set_ylabel(ylabel, fontsize=8)
            ax.set_title(subtitle, fontsize=8.5, fontweight='bold')

    plt.tight_layout(pad=1.0)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#EBEBEB')
    buf.seek(0); plt.close(); return buf


# ── Construcción PPTX ─────────────────────────────────────────────────────────
def _build_pptx(mes: int, anio: int, datos: dict, datos_anuales: dict, tarifa: float) -> BytesIO:
    mes_nombre  = MESES_ES[mes]
    mes_ant     = datos.get("mes_anterior", {})
    mes_ant_num = mes_ant.get("mes", mes-1 if mes > 1 else 12)
    mes_ant_nom = MESES_ES[mes_ant_num]

    prs = Presentation(TEMPLATE_PATH)

    NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    xml_slides = prs.slides._sldIdLst
    for sldId_el in list(xml_slides):
        rid = sldId_el.get(f'{{{NS}}}id') or sldId_el.get('r:id')
        xml_slides.remove(sldId_el)
        try:
            if rid in prs.part.rels:
                prs.part.drop_rel(rid)
        except Exception:
            pass

    layout = prs.slide_layouts[2]

    def new_slide():
        slide = prs.slides.add_slide(layout)
        for ph in list(slide.placeholders):
            ph._element.getparent().remove(ph._element)
        return slide

    def add_logo(slide):
        if os.path.exists(LOGO_PATH):
            slide.shapes.add_picture(LOGO_PATH, Inches(0.25), Inches(0.10), Inches(2.20), Inches(0.60))

    def add_title(slide, texto: str):
        tb = slide.shapes.add_textbox(Inches(0.25), Inches(0.75), Inches(12.80), Inches(0.55))
        tf = tb.text_frame; tf.word_wrap = False
        p  = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
        run = p.add_run(); run.text = texto
        run.font.size = Pt(15); run.font.bold = True
        run.font.color.rgb = RGBColor(0x21, 0x63, 0x63); run.font.name = "Arial"

    def add_chart(slide, buf: BytesIO, x=1.80, y=1.30, w=9.40, h=5.80):
        buf.seek(0)
        slide.shapes.add_picture(buf, Inches(x), Inches(y), Inches(w), Inches(h))

    # ── 1. Portada ────────────────────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    tb = s.shapes.add_textbox(Inches(1.5), Inches(2.8), Inches(10.0), Inches(2.0))
    tf = tb.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = f"{mes_nombre} {anio}"
    run.font.size = Pt(44); run.font.bold = True
    run.font.color.rgb = RGBColor(0x21, 0x63, 0x63); run.font.name = "Arial"

    # ── 2-6. OEE por tipo (con PTEE en la misma gráfica) ─────────────────────
    for tk, titulo_slide in [
        ("inyeccion",         f"INDICADORES INYECCION {mes_nombre} {anio}"),
        ("soplado",           f"INDICADORES SOPLADO {mes_nombre} {anio}"),
        ("linea_orina",       f"INDICADORES LINEA FRASCO ORINA {mes_nombre} {anio}"),
        ("linea_copro",       f"INDICADORES LINEA FRASCO COPROLOGICO {mes_nombre} {anio}"),
        ("acondicionamiento", f"INDICADORES ACONDICIONAMIENTO {mes_nombre} {anio}"),
    ]:
        s = new_slide(); add_logo(s); add_title(s, titulo_slide)
        add_chart(s, _chart_oee_tipo(TIPO_LABEL.get(tk, tk), datos_anuales, tk, mes))

    # ── 7. Resumen OEE General del mes ───────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"RESUMEN OEE GENERAL — {mes_nombre} {anio}")
    add_chart(s, _chart_oee_resumen(datos["oee_por_tipo"], mes_nombre, anio))

    # ── 8. Comparativa mes actual vs mes anterior ─────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"COMPARATIVA OEE — {mes_ant_nom} vs {mes_nombre} {anio}")
    add_chart(s, _chart_comparativa_mes(datos["comparativa_mes_anterior"], mes_nombre, mes_ant_nom, anio))

    # ── 9. PTEE vs OEE ────────────────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"OEE vs PTEE (Eficiencia Ponderada TC) — {mes_nombre} {anio}")
    add_chart(s, _chart_ptee(datos["oee_por_tipo"], datos["ptee_por_tipo"], mes_nombre, anio))

    # ── 10. Resina transformada ───────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"RESINA TRANSFORMADA (kg procesados) — {mes_nombre} {anio}")
    add_chart(s, _chart_kg(datos["kg_mes"], mes_nombre, anio))

    # ── 11. Consumo energético ────────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"CONSUMO ENERGÉTICO (kWh) — {mes_nombre} {anio}")
    add_chart(s, _chart_consumo(datos["consumo"], mes_nombre, anio))

    # ── 12. Costo energético por kg ───────────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"COSTO ENERGÉTICO POR kg PRODUCIDO — {mes_nombre} {anio}")
    add_chart(s, _chart_costo_kg(datos["consumo"], datos["kg_mes"], tarifa, mes_nombre, anio))

    # ── 13. Desperdicio ───────────────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"DESPERDICIO — {mes_nombre} {anio}")
    add_chart(s, _chart_desperdicios(datos["desperdicios"], mes_nombre, anio))

    # ── 14. MTTR / MTBF / Disponibilidad ─────────────────────────────────────
    s = new_slide(); add_logo(s)
    add_title(s, f"MTTR, MTBF, DISPONIBILIDAD — {mes_nombre} {anio}")
    add_chart(s, _chart_mttr(datos["mttr_mtbf"], mes_nombre, anio), y=1.35, h=5.70)

    # ── 15. Cierre ────────────────────────────────────────────────────────────
    s = new_slide(); add_logo(s)
    tb = s.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10.0), Inches(2.0))
    tf = tb.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = "GRACIAS"
    run.font.size = Pt(60); run.font.bold = True
    run.font.color.rgb = RGBColor(0x21, 0x63, 0x63); run.font.name = "Arial Black"

    output = BytesIO(); prs.save(output); output.seek(0)
    return output


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("/reporte-mensual/preview")
def preview_datos_mes(mes: int, anio: int, db: Session = Depends(get_db)):
    if not (1 <= mes <= 12):
        raise HTTPException(status_code=400, detail="Mes inválido (1-12)")

    datos = _calcular_datos_mes(mes, anio, db)

    # Comparativa mes anterior
    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    datos_ant = _calcular_datos_mes(mes_ant, anio_ant, db)

    comparativa = {}
    for tk in TIPO_KEYS:
        actual   = datos["oee_por_tipo"].get(tk)
        anterior = datos_ant["oee_por_tipo"].get(tk)
        comparativa[tk] = {
            "actual":   actual,
            "anterior": anterior,
            "delta":    round(actual - anterior, 2) if actual is not None and anterior is not None else None,
        }

    # Tendencia anual (mensual por tipo)
    datos_anuales = _datos_anuales(anio, mes, db)
    TIPO_LABELS_FULL = {
        "inyeccion":"Inyección","soplado":"Soplado",
        "linea_copro":"Línea Copro","linea_orina":"Línea Orina",
        "acondicionamiento":"Acondicionamiento",
    }
    tipos_preview = {}
    for tk in TIPO_KEYS:
        mensual = [{"mes": m, "oee": datos_anuales[tk].get(m, {}).get("oee"), "ptee": datos_anuales[tk].get(m, {}).get("ptee")} for m in range(1, 13)]
        tipos_preview[tk] = {
            "label":   TIPO_LABELS_FULL.get(tk, tk),
            "mensual": mensual,
            "oee_mes": datos["oee_por_tipo"].get(tk),
            "ptee_mes": datos["ptee_por_tipo"].get(tk),
        }

    return {
        "mes":                      mes,
        "anio":                     anio,
        "tipos":                    tipos_preview,
        "oee_por_tipo":             datos["oee_por_tipo"],
        "ptee_por_tipo":            datos["ptee_por_tipo"],
        "oee_por_turno":            datos["oee_por_turno"],
        "consumo":                  datos["consumo"],
        "mttr_mtbf":                datos["mttr_mtbf"],
        "desperdicios":             datos["desperdicios"],
        "kg_mes":                   datos["kg_mes"],
        "comparativa_mes_anterior": comparativa,
        "mes_anterior":             {"mes": mes_ant, "anio": anio_ant},
    }


@router.get("/reporte-mensual/pptx")
async def generar_pptx(background_tasks: BackgroundTasks, mes: int, anio: int, tarifa: float = TARIFA_DEFAULT, db: Session = Depends(get_db)):
    """
    Inicia la generación del PPTX en background y devuelve un job_id.
    El cliente hace polling a /reporte-mensual/pptx/estado/{job_id}
    y descarga desde /reporte-mensual/pptx/descargar/{job_id} cuando esté listo.
    """
    if not (1 <= mes <= 12):
        raise HTTPException(status_code=400, detail="Mes inválido (1-12)")
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=500, detail=f"Template no encontrado: {TEMPLATE_PATH}")
    if tarifa <= 0:
        raise HTTPException(status_code=400, detail="Tarifa debe ser mayor a 0")

    # Recopilar datos ANTES de lanzar el background (la sesión de DB no es thread-safe)
    datos         = preview_datos_mes(mes, anio, db)
    datos_anuales = _datos_anuales(anio, mes, db)
    filename      = f"Reporte_{MESES_ES[mes]}_{anio}_Inverfarma.pptx"

    # Crear el job
    job_id = str(uuid.uuid4())
    _pptx_jobs[job_id] = {"estado": "pendiente", "archivo": None, "filename": filename}

    # Lanzar en thread pool para no bloquear el event loop
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _generar_pptx_background,
        job_id, mes, anio, datos, datos_anuales, tarifa, filename
    )

    return JSONResponse({"job_id": job_id, "estado": "pendiente", "mensaje": "Generando reporte..."})


@router.get("/reporte-mensual/pptx/estado/{job_id}")
def estado_pptx(job_id: str):
    """Polling — el frontend consulta esto cada 2 segundos."""
    job = _pptx_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return {
        "job_id": job_id,
        "estado": job["estado"],   # pendiente | generando | listo | error
        "error":  job.get("error")
    }


@router.get("/reporte-mensual/pptx/descargar/{job_id}")
def descargar_pptx(job_id: str):
    """Descarga el PPTX una vez que el estado es 'listo'."""
    job = _pptx_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if job["estado"] != "listo":
        raise HTTPException(status_code=400, detail=f"El reporte aún no está listo. Estado: {job['estado']}")

    archivo = job["archivo"]
    if not archivo or not os.path.exists(archivo):
        raise HTTPException(status_code=500, detail="Archivo no encontrado")

    def iterfile():
        with open(archivo, 'rb') as f:
            yield from f
        # Limpiar archivo temporal y job después de la descarga
        try:
            os.unlink(archivo)
            del _pptx_jobs[job_id]
        except Exception:
            pass

    return StreamingResponse(
        iterfile(),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{job["filename"]}"'}
    )
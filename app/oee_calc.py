"""
oee_calc.py
Función central de cálculo OEE para Inverfarma.
Fórmulas verificadas contra los 5 Excels OEE de la empresa.

Importar en cualquier router así:
    from ..oee_calc import calcular_oee_turno

NO duplicar esta lógica en otros archivos.
"""

from typing import Optional
from datetime import datetime as _dt


def _parse_hora(h: str) -> float:
    """
    Convierte hora en cualquier formato a horas decimales.
    Soporta: 'HH:MM', 'H:MM am', 'HH:MM PM', 'HH:MM:SS',
             '3:07\u202fp.\xa0m.' (formato colombiano con Unicode), etc.
    Retorna -1.0 si falla.
    """
    if not h:
        return -1.0
    try:
        h = str(h).strip().lower()
        # Normalizar espacios Unicode especiales (formato colombiano)
        h = h.replace('\u202f', ' ').replace('\xa0', ' ')
        # Normalizar formato colombiano: "p. m." → "pm", "a. m." → "am"
        h = h.replace('p. m.', 'pm').replace('a. m.', 'am')
        h = h.replace('p.m.', 'pm').replace('a.m.', 'am')
        # Quitar segundos si existen: '06:00:00' → '06:00'
        partes_dos_puntos = h.split(':')
        if len(partes_dos_puntos) == 3:
            h = ':'.join(partes_dos_puntos[:2])

        ampm = None
        if h.endswith('am'):
            ampm = 'am'
            h = h[:-2].strip()
        elif h.endswith('pm'):
            ampm = 'pm'
            h = h[:-2].strip()

        partes = h.split(':')
        hh = int(partes[0])
        mm = int(partes[1]) if len(partes) > 1 else 0

        if ampm == 'pm' and hh != 12:
            hh += 12
        if ampm == 'am' and hh == 12:
            hh = 0

        return hh + mm / 60.0
    except Exception:
        return -1.0


def calcular_oee_turno(turno, orden) -> dict:
    """
    Calcula OEE de un turno con las fórmulas exactas de los 5 Excels OEE
    de Inverfarma. Cubre inyección, soplado, líneas copro/orina y
    acondicionamiento.

    Fórmulas:
    ──────────────────────────────────────────────────────────────────────
    INYECCIÓN · SOPLADO · LÍNEA COPRO · LÍNEA ORINA
      TC              = 12h fijo (inyección/soplado) o variable (líneas)
      T_trabajado     = TC − paradas_PROG_h
      T_real          = T_trabajado − paradas_NP_h
      DISPONIBILIDAD  = T_real / T_trabajado
      PROD_PLANEADA   = T_real × 60 × ciclos_min × cavidades
      EFICIENCIA      = contador / prod_planeada
      CALIDAD         = prod_real / contador
      OEE             = D × E × C × 100

    ACONDICIONAMIENTO
      TC              = variable (hora_fin − hora_inicio del turno)
      T_trabajado     = TC − paradas_PROG_h
      T_real          = T_trabajado − paradas_NP_h
      DISPONIBILIDAD  = T_real / T_trabajado
      PROD_PLANEADA   = (ciclos × cavidades) × T_real
        ciclos        = uds/hora por operario
        cavidades     = número de operarios
      EFICIENCIA      = contador / prod_planeada
      CALIDAD         = prod_real / contador
      OEE             = D × E × C × 100
    ──────────────────────────────────────────────────────────────────────

    Parámetros:
        turno: objeto Turno de SQLAlchemy (con relaciones cargadas)
        orden: objeto Orden de SQLAlchemy

    Retorna dict con:
        oee, disponibilidad, eficiencia, calidad (todos en %)
        contador, prod_planeada, prod_real, rechazadas
        paradas_np_min, paradas_prog_min
        t_trabajado_h, t_real_h
        n_paradas_np (número de eventos, para MTTR/MTBF)
    """

    tipo = (orden.tipo_maquina or '').lower()

    # ── Producción y desperdicios ─────────────────────────────────────────────
    contador   = sum(r.cantidad for r in turno.registros_produccion)
    rechazadas = sum(d.cantidad for d in turno.desperdicios)
    prod_real  = max(contador - rechazadas, 0)

    # ── Paradas separadas ─────────────────────────────────────────────────────
    paradas_np   = [p for p in turno.paradas if not p.programada]
    paradas_prog = [p for p in turno.paradas if p.programada]

    paradas_np_min   = sum(p.minutos for p in paradas_np)
    paradas_prog_min = sum(p.minutos for p in paradas_prog)
    paradas_np_h     = paradas_np_min / 60.0
    paradas_prog_h   = paradas_prog_min / 60.0
    n_paradas_np     = len(paradas_np)

    # ── TC: tiempo programado del turno ───────────────────────────────────────
    if tipo in ('inyeccion', 'soplado'):
        TC = 12.0
    else:
        # Líneas y acondicionamiento — TC variable = hora_fin − hora_inicio
        inicio_h = _parse_hora(turno.hora_inicio)
        if inicio_h < 0:
            TC = 12.0
        else:
            if turno.hora_fin:
                fin_h = _parse_hora(turno.hora_fin)
            else:
                now   = _dt.now()
                fin_h = now.hour + now.minute / 60.0
            if fin_h < 0:
                TC = 12.0
            else:
                diff = fin_h - inicio_h
                if diff < 0:
                    diff += 24.0   # turno que cruza medianoche
                TC = diff

    # ── Tiempos ───────────────────────────────────────────────────────────────
    t_trabajado_h = max(TC - paradas_prog_h, 0.0)
    t_real_h      = max(t_trabajado_h - paradas_np_h, 0.0)

    # ── Disponibilidad ────────────────────────────────────────────────────────
    disponibilidad = (t_real_h / t_trabajado_h * 100.0) if t_trabajado_h > 0 else 0.0

    # ── Producción planeada ───────────────────────────────────────────────────
    ciclo_min = float(orden.ciclos or 0)
    cavidades = int(orden.cavidades or 1)

    if tipo == 'acondicionamiento':
        prod_hora     = ciclo_min * cavidades
        prod_planeada = prod_hora * t_real_h
    else:
        prod_planeada = (
            t_real_h * 60.0 * ciclo_min * cavidades
        ) if (ciclo_min > 0 and t_real_h > 0) else 0.0

    # ── Eficiencia ────────────────────────────────────────────────────────────
    eficiencia = (contador / prod_planeada * 100.0) if prod_planeada > 0 else 0.0

    # ── Calidad ───────────────────────────────────────────────────────────────
    calidad = (prod_real / contador * 100.0) if contador > 0 else 100.0

    # ── OEE ──────────────────────────────────────────────────────────────────
    oee = (disponibilidad / 100.0) * (eficiencia / 100.0) * (calidad / 100.0) * 100.0

    # ── PTEE = OEE × (T_real_h / TC) ─────────────────────────────────────────
    # Verificado contra los 5 Excels OEE de Inverfarma.
    # Mide cuánto del TC completo fue productivo efectivamente.
    # A diferencia del OEE (relativo a T_real), el PTEE es relativo al TC total.
    ptee = round((oee / 100.0) * (t_real_h / TC) * 100.0, 2) if TC > 0 else 0.0

    return {
        "oee":             round(min(oee, 200.0), 2),
        "disponibilidad":  round(min(disponibilidad, 150.0), 2),
        "eficiencia":      round(min(eficiencia, 200.0), 2),
        "rendimiento":     round(min(eficiencia, 200.0), 2),
        "calidad":         round(min(calidad, 100.0), 2),
        "contador":        contador,
        "prod_planeada":   round(prod_planeada, 2),
        "prod_real":       prod_real,
        "rechazadas":      rechazadas,
        "paradas_np_min":  paradas_np_min,
        "paradas_prog_min":paradas_prog_min,
        "n_paradas_np":    n_paradas_np,
        "t_trabajado_h":   round(t_trabajado_h, 4),
        "t_real_h":        round(t_real_h, 4),
        "ptee":            ptee,
    }
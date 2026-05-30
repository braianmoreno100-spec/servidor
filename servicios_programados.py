# -*- coding: utf-8 -*-
# servicios_programados.py
# Ubicacion: C:\Users\braia\servidor\servicios_programados.py
# Instalar: pip install apscheduler sqlalchemy psycopg2-binary
# Agregar al arrancar.bat: start "Servicios" python servicios_programados.py

import subprocess, os, glob, smtplib, time, gzip, shutil
from email.mime.text         import MIMEText
from email.mime.multipart    import MIMEMultipart
from datetime                import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy              import create_engine, text

# -- Configuracion -------------------------------------------------------------
DATABASE_URL  = "postgresql://postgres:inverfarma2026@localhost:5432/produccion_db"
BACKUP_DIR    = r"C:\Users\braia\servidor\backups"
PG_DUMP       = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
DB_NAME       = "produccion_db"
DB_USER       = "postgres"
DB_PASS       = "inverfarma2026"

# Politica de retencion
DIAS_COMPLETOS   = 7    # Guardar TODOS los backups de los últimos N días
SEMANAS_GUARDAR  = 4    # Guardar 1 backup por semana de las últimas N semanas
# Los backups mensuales (1 por mes) se guardan indefinidamente

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
EMAIL_FROM    = "sistema.inverfarma@gmail.com"
EMAIL_PASS    = "okzoiapydvptzuue"
EMAIL_TO      = ["Produccion@inverfarma.com.co"]
DASHBOARD_URL = "http://192.168.1.12:8000"
# -----------------------------------------------------------------------------

engine = create_engine(DATABASE_URL)


# =============================================================================
#  BACKUP DE BASE DE DATOS — Estrategia mixta + compresión gzip
# =============================================================================
def hacer_backup():
    """
    1. Ejecuta pg_dump y guarda el .sql
    2. Comprime a .sql.gz (ahorra 80-90% de espacio)
    3. Aplica política de retención:
       - Últimos 7 días  → se guardan TODOS
       - Últimas 4 semanas → se guarda 1 por semana
       - Meses anteriores → se guarda 1 por mes (indefinido)
    """
    ts      = datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # ── Paso 1: pg_dump a archivo temporal .sql ────────────────────────────
    sql_tmp = os.path.join(BACKUP_DIR, f"backup_{ts}.sql")
    gz_path = sql_tmp + ".gz"

    env = {**os.environ, "PGPASSWORD": DB_PASS}
    resultado = subprocess.run(
        [PG_DUMP, "-U", DB_USER, "-F", "p", "-f", sql_tmp, DB_NAME],
        env=env, capture_output=True, text=True
    )

    if resultado.returncode != 0:
        print(f"[BACKUP {ts}] ERROR pg_dump: {resultado.stderr[:300]}")
        return

    # ── Paso 2: comprimir con gzip ─────────────────────────────────────────
    try:
        with open(sql_tmp, 'rb') as f_in:
            with gzip.open(gz_path, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(sql_tmp)  # eliminar .sql sin comprimir
        size_kb = os.path.getsize(gz_path) // 1024
        print(f"[BACKUP {ts}] OK -> {os.path.basename(gz_path)} ({size_kb} KB)")
    except Exception as e:
        print(f"[BACKUP {ts}] ERROR comprimiendo: {e}")
        return

    # ── Paso 3: aplicar política de retención ─────────────────────────────
    aplicar_politica_retencion()


def aplicar_politica_retencion():
    """
    Clasifica cada backup en: DIARIO / SEMANAL / MENSUAL
    y elimina los que no entran en ninguna categoría activa.
    """
    ahora     = datetime.now()
    todos     = sorted(glob.glob(os.path.join(BACKUP_DIR, "backup_*.sql.gz")))

    conservar = set()

    # Agrupar por día, semana y mes
    por_dia    = {}   # "20260525"    -> [archivos]
    por_semana = {}   # "2026-W21"    -> [archivos]
    por_mes    = {}   # "202605"      -> [archivos]

    for archivo in todos:
        nombre = os.path.basename(archivo)
        try:
            # Extraer timestamp del nombre: backup_YYYYMMDD_HHMM.sql.gz
            parte = nombre.replace("backup_", "").replace(".sql.gz", "")
            dt    = datetime.strptime(parte, "%Y%m%d_%H%M")
        except ValueError:
            continue  # archivo con nombre inesperado, ignorar

        clave_dia     = dt.strftime("%Y%m%d")
        clave_semana  = dt.strftime("%G-W%V")   # ISO week
        clave_mes     = dt.strftime("%Y%m")

        por_dia.setdefault(clave_dia, []).append((dt, archivo))
        por_semana.setdefault(clave_semana, []).append((dt, archivo))
        por_mes.setdefault(clave_mes, []).append((dt, archivo))

    # Regla 1 — Últimos DIAS_COMPLETOS días: conservar TODOS
    limite_dias = ahora - timedelta(days=DIAS_COMPLETOS)
    for clave, archivos in por_dia.items():
        for dt, archivo in archivos:
            if dt >= limite_dias:
                conservar.add(archivo)

    # Regla 2 — Últimas SEMANAS_GUARDAR semanas: conservar el MÁS RECIENTE de cada semana
    limite_semanas = ahora - timedelta(weeks=SEMANAS_GUARDAR)
    for clave, archivos in por_semana.items():
        # Solo semanas fuera del rango de días completos pero dentro del rango semanal
        archivos_rango = [(dt, a) for dt, a in archivos
                         if limite_semanas <= dt < limite_dias]
        if archivos_rango:
            # El más reciente de esa semana
            conservar.add(max(archivos_rango, key=lambda x: x[0])[1])

    # Regla 3 — Meses anteriores: conservar el MÁS RECIENTE de cada mes (indefinido)
    limite_meses = ahora - timedelta(weeks=SEMANAS_GUARDAR)
    for clave, archivos in por_mes.items():
        archivos_viejos = [(dt, a) for dt, a in archivos if dt < limite_meses]
        if archivos_viejos:
            conservar.add(max(archivos_viejos, key=lambda x: x[0])[1])

    # Eliminar lo que no se conserva
    eliminados = 0
    for archivo in todos:
        if archivo not in conservar:
            try:
                os.remove(archivo)
                print(f"  [BACKUP] Eliminado (fuera de política): {os.path.basename(archivo)}")
                eliminados += 1
            except Exception as e:
                print(f"  [BACKUP] Error eliminando {archivo}: {e}")

    print(f"  [BACKUP] Política aplicada — conservados: {len(conservar)}, eliminados: {eliminados}")


def mostrar_resumen_backups():
    """Muestra cuántos backups hay y cuánto espacio ocupan."""
    archivos = glob.glob(os.path.join(BACKUP_DIR, "backup_*.sql.gz"))
    if not archivos:
        print("  [BACKUP] No hay backups aún.")
        return
    total_kb = sum(os.path.getsize(a) for a in archivos) // 1024
    print(f"  [BACKUP] {len(archivos)} backups almacenados — {total_kb} KB en disco")


# =============================================================================
#  EMAIL DIARIO
# =============================================================================
def obtener_resumen_24h():
    ayer = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d")
    try:
        with engine.connect() as conn:
            fila_turnos = conn.execute(text(
                "SELECT COUNT(*) FROM turnos WHERE fecha >= :f"
            ), {"f": ayer}).fetchone()

            fila_np = conn.execute(text("""
                SELECT COALESCE(SUM(p.minutos), 0), COUNT(p.id)
                FROM paradas p
                JOIN turnos t ON p.turno_id = t.id
                WHERE t.fecha >= :f AND p.programada = false
            """), {"f": ayer}).fetchone()

            fila_prod = conn.execute(text("""
                SELECT COALESCE(SUM(r.cantidad), 0)
                FROM registros_produccion r
                JOIN turnos t ON r.turno_id = t.id
                WHERE t.fecha >= :f
            """), {"f": ayer}).fetchone()

            fila_desp = conn.execute(text("""
                SELECT COALESCE(SUM(d.cantidad), 0)
                FROM desperdicios d
                JOIN turnos t ON d.turno_id = t.id
                WHERE t.fecha >= :f
            """), {"f": ayer}).fetchone()

        return {
            "turnos":       int(fila_turnos[0]) if fila_turnos else 0,
            "minutos_np":   float(fila_np[0])   if fila_np    else 0.0,
            "eventos_np":   int(fila_np[1])      if fila_np    else 0,
            "produccion":   int(fila_prod[0])    if fila_prod  else 0,
            "desperdicios": int(fila_desp[0])    if fila_desp  else 0,
        }
    except Exception as e:
        print(f"[EMAIL] Error consultando BD: {e}")
        return {"turnos": 0, "minutos_np": 0, "eventos_np": 0, "produccion": 0, "desperdicios": 0}


def enviar_email_resumen():
    datos = obtener_resumen_24h()
    fecha = datetime.now().strftime("%d/%m/%Y")
    hora  = datetime.now().strftime("%H:%M")
    color_np = "#e24b4a" if datos["eventos_np"] > 5 else \
               "#ef9f27" if datos["eventos_np"] > 2 else "#5A9E2F"

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px 0;">
  <tr><td align="center">
    <table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e0e0e0;">
      <tr><td style="background:#5A9E2F;padding:20px 24px;">
        <p style="margin:0;color:#fff;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Inverfarma - Control de Produccion</p>
        <h1 style="margin:4px 0 0;color:#fff;font-size:20px;font-weight:700;">Resumen del dia</h1>
        <p style="margin:4px 0 0;color:#d4edba;font-size:13px;">{fecha} - Generado a las {hora}</p>
      </td></tr>
      <tr><td style="padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="48%" style="background:#f8fdf4;border-radius:8px;padding:16px;border:1px solid #d4edba;text-align:center;">
              <p style="margin:0;color:#5a7a4a;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Turnos registrados</p>
              <p style="margin:6px 0 0;color:#5A9E2F;font-size:32px;font-weight:700;">{datos['turnos']}</p>
            </td>
            <td width="4%"></td>
            <td width="48%" style="background:#f8fdf4;border-radius:8px;padding:16px;border:1px solid #d4edba;text-align:center;">
              <p style="margin:0;color:#5a7a4a;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Unidades producidas</p>
              <p style="margin:6px 0 0;color:#5A9E2F;font-size:32px;font-weight:700;">{datos['produccion']:,}</p>
            </td>
          </tr>
          <tr><td colspan="3" style="height:12px;"></td></tr>
          <tr>
            <td width="48%" style="background:#fff8f8;border-radius:8px;padding:16px;border:1px solid #fcc;text-align:center;">
              <p style="margin:0;color:#9a4a4a;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Paradas NP (eventos)</p>
              <p style="margin:6px 0 0;color:{color_np};font-size:32px;font-weight:700;">{datos['eventos_np']}</p>
              <p style="margin:2px 0 0;color:#9a4a4a;font-size:12px;">{datos['minutos_np']:.0f} minutos perdidos</p>
            </td>
            <td width="4%"></td>
            <td width="48%" style="background:#fff8f8;border-radius:8px;padding:16px;border:1px solid #fcc;text-align:center;">
              <p style="margin:0;color:#9a4a4a;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Desperdicios</p>
              <p style="margin:6px 0 0;color:#e24b4a;font-size:32px;font-weight:700;">{datos['desperdicios']:,}</p>
              <p style="margin:2px 0 0;color:#9a4a4a;font-size:12px;">unidades rechazadas</p>
            </td>
          </tr>
        </table>
      </td></tr>
      <tr><td style="padding:0 24px 24px;text-align:center;">
        <a href="{DASHBOARD_URL}" style="display:inline-block;background:#5A9E2F;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:700;">
          Ver dashboard completo
        </a>
        <p style="margin:16px 0 0;color:#aaa;font-size:11px;">
          Sistema de Control de Produccion - Inverfarma<br>
          Correo automatico generado cada dia a las 6:00 AM
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Inverfarma - Resumen produccion {fecha}"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(EMAIL_TO)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_FROM, EMAIL_PASS)
            s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"[EMAIL {fecha}] Enviado a {EMAIL_TO}")
    except Exception as e:
        print(f"[EMAIL {fecha}] Error: {e}")


# =============================================================================
#  MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 52)
    print("  Inverfarma - Servicios programados")
    print("=" * 52)

    if not os.path.exists(PG_DUMP):
        print(f"[WARN] pg_dump no encontrado en: {PG_DUMP}")
        print("       Ajusta la variable PG_DUMP en este script.")
    else:
        print(f"[OK]  pg_dump: {PG_DUMP}")

    print(f"\n[INFO] Política de backups:")
    print(f"       - Últimos {DIAS_COMPLETOS} días   -> se guardan TODOS")
    print(f"       - Últimas {SEMANAS_GUARDAR} semanas -> 1 por semana")
    print(f"       - Meses anteriores  -> 1 por mes (indefinido)")
    print(f"       - Formato           -> .sql.gz (comprimido)")
    mostrar_resumen_backups()

    print("\n[BACKUP] Ejecutando backup inicial...")
    hacer_backup()

    scheduler = BackgroundScheduler(timezone="America/Bogota")
    scheduler.add_job(hacer_backup,           'cron', hour=23, minute=0, id='backup_diario')
    # scheduler.add_job(enviar_email_resumen, 'cron', hour=6,  minute=0, id='email_diario')
    # NOTA: quita el # de la linea de arriba cuando hagas el despliegue en Inverfarma
    scheduler.start()

    print("\n[OK]  Scheduler activo:")
    print(f"      - Backup BD     -> 11:00 PM — carpeta: {BACKUP_DIR}")
    print(f"      - Email resumen -> PAUSADO hasta despliegue")
    print("\nCtrl+C para detener.\n")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("[OK] Scheduler detenido.")
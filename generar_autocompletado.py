"""
generar_autocompletado.py
Lee los productos y líderes de la BD y genera el archivo
constants/autocompletado.ts listo para copiar a la tablet.

Ejecutar con venv activo DESPUÉS de agregar_productos_acondicionamiento.py:
  python generar_autocompletado.py
"""

import sqlite3
import os

DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'produccion.db')
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autocompletado.ts')


def generar():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Líderes ──────────────────────────────────────────────────────────────
    cur.execute("SELECT cedula, nombre FROM lideres WHERE activo = 1 ORDER BY nombre")
    lideres = cur.fetchall()

    # ── Productos ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT codigo, descripcion, ciclos, cavidades, material
        FROM productos
        WHERE activo = 1
        ORDER BY descripcion
    """)
    productos = cur.fetchall()
    conn.close()

    lines = []
    lines.append("// autocompletado.ts")
    lines.append("// Generado automáticamente — NO editar a mano")
    lines.append(f"// {len(lideres)} líderes · {len(productos)} productos")
    lines.append("")

    # ── LIDERES ───────────────────────────────────────────────────────────────
    lines.append("export const LIDERES: Record<string, string> = {")
    for cedula, nombre in lideres:
        nombre_safe = nombre.replace("'", "\\'")
        lines.append(f"  '{cedula}': '{nombre_safe}',")
    lines.append("}")
    lines.append("")

    # ── PRODUCTOS ─────────────────────────────────────────────────────────────
    lines.append("export const PRODUCTOS: Record<string, {")
    lines.append("  descripcion: string")
    lines.append("  ciclos: number")
    lines.append("  cavidades: number")
    lines.append("  material: string")
    lines.append("}> = {")

    for codigo, descripcion, ciclos, cavidades, material in productos:
        desc_safe = descripcion.replace("'", "\\'") if descripcion else ''
        mat_safe  = (material or 'N/A').replace("'", "\\'")
        ciclos    = ciclos    or 0
        cavidades = cavidades or 1
        lines.append(f"  '{codigo}': {{")
        lines.append(f"    descripcion: '{desc_safe}',")
        lines.append(f"    ciclos: {ciclos},")
        lines.append(f"    cavidades: {cavidades},")
        lines.append(f"    material: '{mat_safe}',")
        lines.append(f"  }},")

    lines.append("}")
    lines.append("")

    content = "\n".join(lines)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"""
╔══════════════════════════════════════════════════════╗
║           autocompletado.ts GENERADO                 ║
╠══════════════════════════════════════════════════════╣
║  Líderes  : {len(lideres):3d}                                   ║
║  Productos: {len(productos):3d}                                   ║
║  Archivo  : {OUT_PATH}  ║
╚══════════════════════════════════════════════════════╝

Copia el archivo generado a:
  app-tablet2/constants/autocompletado.ts
    """)


if __name__ == "__main__":
    generar()
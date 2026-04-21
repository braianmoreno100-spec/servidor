"""
agregar_productos_acondicionamiento.py
Agrega los 149 productos de acondicionamiento extraídos del Excel Celta 2025.
NO borra los productos existentes — solo inserta los nuevos (ignora duplicados por código).

Ejecutar con venv activo:
  python agregar_productos_acondicionamiento.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'produccion.db')

# (codigo, descripcion, ciclo_seg, cavidades, material)
# ciclo_seg = 3600 / und_hora  →  segundos por unidad por operario
# cavidades = 1 siempre en acondicionamiento (1 operario = 1 unidad a la vez)
# material  = 'N/A' (acondicionamiento no usa material plástico)
PRODUCTOS_ACONDICIONAMIENTO = [
    ('4270330035',  'ZAPATON POLAINA PLASTICA INV PQ X 5 PARES',              40.4,  1, 'N/A'),
    ('4270330045SE','ZAPATON POLAINA AZUL X 100 UND',                          40.4,  1, 'N/A'),
    ('4270330006',  'ZAPATON POLAINA AZUL PAR INVERFARMA',                     6.0,   1, 'N/A'),
    ('4270330045',  'ZAPATON POLAINA AZUL INV X 100 UND',                      6.0,   1, 'N/A'),
    ('4340350004',  'VENDA DE YESO 6X5 YARDAS',                                32.4,  1, 'N/A'),
    ('4340350003',  'VENDA DE YESO 5X5 YARDAS',                                40.5,  1, 'N/A'),
    ('4340350002',  'VENDA DE YESO 4X5 YARDAS',                                32.4,  1, 'N/A'),
    ('4340350001',  'VENDA DE YESO 3X5 YARDAS',                                32.4,  1, 'N/A'),
    ('8340480004',  'VENDA ADHESIVA INV 5 X 5',                                40.4,  1, 'N/A'),
    ('8340480003',  'VENDA ADHESIVA INV 4X5',                                  32.4,  1, 'N/A'),
    ('8340480002',  'VENDA ADHESIVA INV 3 X 5',                                40.4,  1, 'N/A'),
    ('8340480001',  'VENDA ADHESIVA  INV 2 X 5',                               32.4,  1, 'N/A'),
    ('4270330020',  'TRAJE ENTERO BIOSEG. CON GORRO TALLA S-M',                300.0, 1, 'N/A'),
    ('4270330021',  'TRAJE ENTERO BIOSEG. CON GORRO TALLA L-XL',               240.0, 1, 'N/A'),
    ('4320280001',  'TERMOMETRO PEDIATRICO DIG PUNTA FLEXIBLE',                128.6, 1, 'N/A'),
    ('4320330001',  'TERMOMETRO INFRARROJO',                                   56.2,  1, 'N/A'),
    ('4310330004',  'TAPON HEPARINIZADO X UNIDAD',                             24.0,  1, 'N/A'),
    ('4300070003',  'TAPABOCAS X 50 EMPAQUE INDIVIDUAL AZUL',                  19.5,  1, 'N/A'),
    ('4300280043SC','TAPABOCAS PEDIATRICO INSTITUCIONAL',                       22.5,  1, 'N/A'),
    ('4300070041',  'TAPABOCAS NEGRO EMP IND FARMATODO',                       90.0,  1, 'N/A'),
    ('4300070041SE','TAPABOCAS NEGRO EMP IND FARMATODO SE',                    90.0,  1, 'N/A'),
    ('4300070026',  'TAPABOCAS KN95 X UNIDAD',                                 90.0,  1, 'N/A'),
    ('4300070029',  'TAPABOCAS KN95 X 10 UNID',                                90.0,  1, 'N/A'),
    ('4300070031',  'TAPABOCAS GRANEL AZUL X 12 UND',                          23.1,  1, 'N/A'),
    ('4300070049',  'TAPABOCAS EMP IND AZUL X 50 DON BOTIQUIN',                11.1,  1, 'N/A'),
    ('9300000001',  'TAPABOCAS DES INV AZUL X 5 X 10 PARA CODIFICAR',          32.4,  1, 'N/A'),
    ('4300070049SE','TAPABOCAS DES AZUL * 50 UND - EMP IND-DON BOTIQUIN.',     32.4,  1, 'N/A'),
    ('4300070001',  'TAPABOCAS AZUL X 12 UND',                                 171.4, 1, 'N/A'),
    ('4300070040',  'TAPABOCAS AZUL EMP IND FARMATODO',                        124.1, 1, 'N/A'),
    ('4300070040SE','TAPABOCAS AZUL EMP IND FARMATODO SE',                     13.8,  1, 'N/A'),
    ('4300070032',  'TAPABOCA R5-95 MEDIANO UNICOLOR X 10 UND',                15.0,  1, 'N/A'),
    ('4300070033',  'TAPABOCA R5-95 MEDIANO ESTAMPADO X 10 UND',               15.0,  1, 'N/A'),
    ('4300280009',  'TAPABOCA R5-95 KIDS UNICOLOR X 10 UND',                   15.0,  1, 'N/A'),
    ('4300280010',  'TAPABOCA R5-95 KIDS ESTAMPADO X 10 UND',                  15.0,  1, 'N/A'),
    ('4300070034',  'TAPABOCA R5-95 ADULTO UNICOLOR X 10 UND',                 15.0,  1, 'N/A'),
    ('4300070035',  'TAPABOCA R5-95 ADULTO ESTAMPADO X 10 UND',                14.1,  1, 'N/A'),
    ('4300280007',  'TAPABOCA PEDIATRICO INV VERDE X 25 UND',                  62.1,  1, 'N/A'),
    ('8300280003',  'TAPABOCA PEDIATRICO INV ROSADO X 50 UND',                 28.6,  1, 'N/A'),
    ('4300280003',  'TAPABOCA PEDIATRICO INV ROSADO X 12 UND',                 32.4,  1, 'N/A'),
    ('8300280001',  'TAPABOCA PEDIATRICO INV AZUL X 50 UND',                   21.6,  1, 'N/A'),
    ('4300280001',  'TAPABOCA PEDIATRICO INV AZUL X 12 UND',                   38.3,  1, 'N/A'),
    ('8300280009',  'TAPABOCA INV KF94 TALLA-S x UND',                         29.5,  1, 'N/A'),
    ('8300070013',  'TAPABOCA INV KF94 TALLA-M x UND',                         40.4,  1, 'N/A'),
    ('8300070014',  'TAPABOCA INV KF94 TALLA-L x UND',                         36.0,  1, 'N/A'),
    ('3300070020',  'TAPABOCA DES INV MULTICOLOR X 12 UND',                    36.0,  1, 'N/A'),
    ('4300070007',  'TAPABOCA DES INV BLANCO X 50 UND EMP IND',                7.2,   1, 'N/A'),
    ('4300070009',  'TAPABOCA DES INV BLANCO X 5 UND CAJA X 50',               20.2,  1, 'N/A'),
    ('4300070008',  'TAPABOCA DES INV BLANCO X 12 UND',                        20.2,  1, 'N/A'),
    ('4300070014',  'TAPABOCA DES INV BLANCO 12 UND EMP INDIVIDUAL',           20.2,  1, 'N/A'),
    ('8300070001',  'TAPABOCA DES INV AZUL X 50 UND EMP IND',                  20.2,  1, 'N/A'),
    ('4300070028',  'TAPABOCA DES INV AZUL X 5 UND CAJA X 50',                 20.0,  1, 'N/A'),
    ('4300070031F', 'TAPABOCA DES INV AZUL X 12 UND GRANEL CON ORIFICIO',      13.4,  1, 'N/A'),
    ('4300070013',  'TAPABOCA DES INV AZUL X 12 UND GRANEL',                   13.4,  1, 'N/A'),
    ('4300070012',  'TAPABOCA DES INV AZUL 12 UND EMP INDIVIDUAL',             13.4,  1, 'N/A'),
    ('4300070012C', 'TAPABOCA DES INV AZUL 12 UND EMP INDIVIDUAL C',           13.4,  1, 'N/A'),
    ('8280250010',  'SONDA NELATON USO INSTITUCIONAL',                          13.4,  1, 'N/A'),
    ('8280250002',  'SONDA NELATON INV #8 UND',                                 13.4,  1, 'N/A'),
    ('8280250005',  'SONDA NELATON INV #14 UND',                                13.4,  1, 'N/A'),
    ('8280250004',  'SONDA NELATON INV #12 UND',                                13.4,  1, 'N/A'),
    ('8280250003',  'SONDA NELATON INV # 10 UNIDAD',                            19.5,  1, 'N/A'),
    ('8280250001',  'SONDA NELATON INV # 6',                                    15.3,  1, 'N/A'),
    ('8280250006',  'SONDA NELATON INV # 16 UNIDAD',                            13.4,  1, 'N/A'),
    ('4280250004',  'SONDA NELATON # 8 UNIDAD',                                 20.2,  1, 'N/A'),
    ('4280250002',  'SONDA NELATON # 6 UNIDAD',                                 20.2,  1, 'N/A'),
    ('4280250016',  'SONDA NELATON # 20 UNIDAD',                                20.2,  1, 'N/A'),
    ('4280250014',  'SONDA NELATON # 18 UNIDAD',                                20.2,  1, 'N/A'),
    ('8280250007',  'SONDA NELATON # 18',                                       72.0,  1, 'N/A'),
    ('4280250012',  'SONDA NELATON # 16 UNIDAD',                                5.1,   1, 'N/A'),
    ('4280250010',  'SONDA NELATON # 14 UNIDAD',                                21.6,  1, 'N/A'),
    ('4280250008',  'SONDA NELATON # 12 UNIDAD',                                21.6,  1, 'N/A'),
    ('4280250006',  'SONDA NELATON # 10 UNIDAD',                                21.6,  1, 'N/A'),
    ('8280190006',  'SONDA FOLEY INVE 2 VIAS BALON # 18 IF UND',               21.6,  1, 'N/A'),
    ('8280190005',  'SONDA FOLEY INV 2 VIAS BALON #16 IF',                     37.5,  1, 'N/A'),
    ('8280190004',  'SONDA FOLEY INV 2 VIAS BALON # 14 IF UNIDAD',             102.9, 1, 'N/A'),
    ('8280190003',  'SONDA FOLEY INV 2 VIAS BALON # 12 IF UNIDAD',             72.0,  1, 'N/A'),
    ('4280190012',  'SONDA FOLEY 2 VIAS BALON # 18 IF UNIDAD',                 40.0,  1, 'N/A'),
    ('4280190010',  'SONDA FOLEY 2 VIAS BALON # 16 IF UNIDAD',                 9.0,   1, 'N/A'),
    ('4280190008',  'SONDA FOLEY 2 VIAS BALON # 14 IF UNIDAD',                 21.3,  1, 'N/A'),
    ('4280190006',  'SONDA FOLEY 2 VIAS BALON # 12 IF UNIDAD',                 16.9,  1, 'N/A'),
    ('4270330005',  'SABANA TIRA INV X 5 UND',                                  21.3,  1, 'N/A'),
    ('4270330044',  'SABANA RESORTADA INV X 5 UND CON PERCHA',                  16.0,  1, 'N/A'),
    ('4270330004',  'SABANA RESORTADA INV X 5 UND',                             22.5,  1, 'N/A'),
    ('4270330043',  'SABANA PLANA INV X 5 UND CON PERCHA',                      10.1,  1, 'N/A'),
    ('4270330003',  'SABANA PLANA INV X 5 UND',                                 12.0,  1, 'N/A'),
    ('4350330005',  'SABANA IMPERMEABLE X UNIDAD',                              23.1,  1, 'N/A'),
    ('4270330031',  'ROLLO SABANA PARA CAMILLA INV 70X100CM',                   163.6, 1, 'N/A'),
    ('4300070039',  'RESPIRADOR DE ALTA EFICIENCIA R5-95',                      105.9, 1, 'N/A'),
    ('4300070036',  'RESPIRADOR ALTA EFICI FASCARE N95',                        23.1,  1, 'N/A'),
    ('4250330002',  'RECOLECTOR GUARDIAN INVERFARMA 0.3 LTS',                   300.0, 1, 'N/A'),
    ('4260330005',  'RECOLECTOR 24 HORAS INVERFARMA',                           72.0,  1, 'N/A'),
    ('4260330007',  'RECOLECTOR 24 HORAS AMBAR INVERFARMA',                     51.4,  1, 'N/A'),
    ('4260330011',  'RECOLECTOR 24 H AMBAR FEMENINO',                           18.0,  1, 'N/A'),
    ('4490330072',  'PULSIOXIMETRO DE DEDO CON PILAS',                          4.6,   1, 'N/A'),
    ('4490330072C', 'PULSIOXIMETRO DE DEDO CON PILAS C',                        22.1,  1, 'N/A'),
    ('4230100002',  'PRUEBA EMBARAZO INV LAPICERO 16 X 12',                     22.1,  1, 'N/A'),
    ('4230100001',  'PRUEBA EMBARAZO INV LAPICERO',                             30.0,  1, 'N/A'),
    ('4230120002',  'PRUEBA EMBARAZO INV CINTA 14 X 12',                        22.1,  1, 'N/A'),
    ('4230120001',  'PRUEBA EMBARAZO INV CINTA',                                53.7,  1, 'N/A'),
    ('4230110002',  'PRUEBA EMBARAZO INV CASSETTE 14 X 12',                     53.7,  1, 'N/A'),
    ('4230110001',  'PRUEBA EMBARAZO INV CASSETTE',                             18.9,  1, 'N/A'),
    ('3250330002',  'PREPACK INV 3 REC GUARDIAN 3 LITROS GTS SOP',              116.1, 1, 'N/A'),
    ('4260330003',  'PISCINGO ORINAL PLASTICO UND',                             120.0, 1, 'N/A'),
    ('4240330003',  'PATO DESECHABLE COPROLOGICO UND',                          116.1, 1, 'N/A'),
    ('4300070027C', 'MASCARILLA FACIAL 3D X UND',                               15.3,  1, 'N/A'),
    ('8220280004',  'KIT NEBULIZADOR PEDIATRICO ICOM',                          27.7,  1, 'N/A'),
    ('8220280005',  'KIT NEBULIZADOR ADULTO ICOM',                              60.0,  1, 'N/A'),
    ('8220070005',  'KIT NEBULIZADOR ADULTO FAST CARE',                         60.0,  1, 'N/A'),
    ('4220280001',  'KIT NEBULIZACION INV PEDIA PLUS ROSADO CON PERCHA',        28.1,  1, 'N/A'),
    ('4220280002',  'KIT NEBULIZACION INV PEDIA PLUS AZUL CON PERCHA',          11.6,  1, 'N/A'),
    ('8220280001',  'KIT DE NEBULIZACION PEDIATRICO INVERFARMA',                53.7,  1, 'N/A'),
    ('8220070001',  'KIT DE NEBULIZACION ADULTO',                               15.0,  1, 'N/A'),
    ('4190330001',  'KIT DE INYECTOLOGIA',                                      76.6,  1, 'N/A'),
    ('4270330007',  'KIT DE BIOSEGURIDAD INVER',                                128.6, 1, 'N/A'),
    ('4180050005',  'JERINGA INV 3P 5ML 21G X 1 1/2 X 50UND',                  14.6,  1, 'N/A'),
    ('4180050006',  'JERINGA INV 3P 5ML 21G X 1 1/2 X 25UND',                  6.7,   1, 'N/A'),
    ('4180050004',  'JERINGA INV 3P 3ML 21G X 1 1/2 X 50UND',                  6.7,   1, 'N/A'),
    ('4180050003',  'JERINGA INV 3P 3ML 21G X 1 1/2 X 25UND',                  6.7,   1, 'N/A'),
    ('31700280010', 'INHALOCAMARA PEDIATRICA ROSADA AIFARM',                    11.4,  1, 'N/A'),
    ('3170280013',  'INHALOCAMARA PEDIATRICA OXIS',                             8.2,   1, 'N/A'),
    ('3170280004',  'INHALOCAMARA PEDIATRICA INSTITUCIONAL BOLSA X 1 UND',      8.2,   1, 'N/A'),
    ('3170280005',  'INHALOCAMARA PEDIATRICA FARMATODO',                        8.2,   1, 'N/A'),
    ('3170280002',  'INHALOCAMARA INVERFARMA PEDIATRICA',                       8.2,   1, 'N/A'),
    ('3170280001',  'INHALOCAMARA ICOM PEDIATRICA',                             8.2,   1, 'N/A'),
    ('3170070003',  'INHALOCAMARA ICOM PEDIATRICA AZUL',                        8.2,   1, 'N/A'),
    ('3170070002',  'INHALOCAMARA ICOM ADULTO',                                 8.2,   1, 'N/A'),
    ('3170280011',  'INHALOCAMARA AIRFARM PLUS PEDIATRICA ROSADA',              8.2,   1, 'N/A'),
    ('3170280009',  'INHALOCAMARA AIRFARM PLUS PEDIATRICA AZUL',                23.1,  1, 'N/A'),
    ('3170070012',  'INHALOCAMARA AIRFARM PLUS ADULTO',                         12.9,  1, 'N/A'),
    ('3170280010',  'INHALOCAMARA AIRFARM PEDIATRICA ROSADA',                   72.0,  1, 'N/A'),
    ('3170280008',  'INHALOCAMARA AIRFARM PEDIATRICA AZUL',                     38.3,  1, 'N/A'),
    ('3170280012',  'INHALOCAMARA ADULTO OXIS',                                 257.1, 1, 'N/A'),
    ('3170070001',  'INHALOCAMARA ADULTO INSTITUCIONAL BOLSA X 1 UND',          38.3,  1, 'N/A'),
    ('3170280014',  'INHALOCAMARA ADULTO INSTITUCIONAL',                        38.3,  1, 'N/A'),
    ('3170070004',  'INHALOCAMARA ADULTO FARMATODO VERDE',                      12.0,  1, 'N/A'),
    ('4490330000',  'HUMIDIFICADOR DE OXIGENO',                                 257.1, 1, 'N/A'),
    ('4160340023',  'GUANTE VINILO TRANSPARENTE T-M GV 100 UND',               14.4,  1, 'N/A'),
    ('4160340025SC','GUANTE VINILO TALLA USO INSTITUCIONAL',                    17.6,  1, 'N/A'),
    ('4160170004',  'GUANTE QUIRURGICO ESTERIL PAR INV T 8 PAR',               17.6,  1, 'N/A'),
    ('8160170003',  'GUANTE QUIRURGICO ESTERIL PAR INV T 7.5 PAR',             17.6,  1, 'N/A'),
    ('8160170002',  'GUANTE QUIRURGICO ESTERIL PAR INV T 7 PAR',               17.6,  1, 'N/A'),
    ('8160170001',  'GUANTE QUIRURGICO ESTERIL PAR INV T 6.5 PAR',             12.0,  1, 'N/A'),
    ('4060270026',  'GUANTE NITRILO NEGRO X 50 UND',                            10.4,  1, 'N/A'),
    ('4160270025',  'GUANTE NITRILO NEGRO TALLA S X 50 UND',                   46.2,  1, 'N/A'),
    ('8160270015',  'GUANTE NITRILO NEGRO TALLA S X 100 UND',                  46.2,  1, 'N/A'),
    ('4160270026',  'GUANTE NITRILO NEGRO TALLA M X 50 UND',                   51.4,  1, 'N/A'),
    ('8160270014',  'GUANTE NITRILO NEGRO TALLA M X 100 UND',                  17.6,  1, 'N/A'),
    ('8160270013',  'GUANTE NITRILO NEGRO TALLA L X 100 UND',                  17.6,  1, 'N/A'),
    ('4160270027',  'GUANTE NITRILO NEGRO TALLA L X 50 UND',                   7.2,   1, 'N/A'),
]


def agregar():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Obtener códigos ya existentes para no duplicar
    cur.execute("SELECT codigo FROM productos")
    existentes = {r[0] for r in cur.fetchall()}

    nuevos     = 0
    omitidos   = 0
    for codigo, descripcion, ciclo, cavidades, material in PRODUCTOS_ACONDICIONAMIENTO:
        if codigo in existentes:
            omitidos += 1
            continue
        cur.execute("""
            INSERT INTO productos (codigo, descripcion, ciclos, cavidades, material, activo)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (codigo, descripcion, ciclo, cavidades, material))
        existentes.add(codigo)
        nuevos += 1

    conn.commit()
    conn.close()

    print(f"""
╔══════════════════════════════════════════════════╗
║       PRODUCTOS ACONDICIONAMIENTO AGREGADOS      ║
╠══════════════════════════════════════════════════╣
║  Nuevos insertados : {nuevos:3d}                        ║
║  Ya existían       : {omitidos:3d}  (no se duplicaron)  ║
║  Total en lista    : {len(PRODUCTOS_ACONDICIONAMIENTO):3d}                        ║
╚══════════════════════════════════════════════════╝

Ahora actualiza autocompletado.ts en la tablet con:
  python generar_autocompletado.py
    """)


if __name__ == "__main__":
    agregar()
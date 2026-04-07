import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.models import Lider, Empleado, Producto

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ─────────────────────────────────────────────
# LÍDERES
# ─────────────────────────────────────────────

lideres = [
    {"cedula": "1016036365", "nombre": "Guzman Moscoso Jennifer Natalia"},
    {"cedula": "80762492",   "nombre": "Herran Rodriguez Jimmy Abraham"},
    {"cedula": "1143266639", "nombre": "Blanco Candanoza Yulaines Andrea"},
    {"cedula": "1073512622", "nombre": "Sanchez Soler Diana Carolina"},
    {"cedula": "1005852755", "nombre": "Cadena Tovar Jhon Jaiver"},
]

# ─────────────────────────────────────────────
# EMPLEADOS
# ─────────────────────────────────────────────

empleados = [
    {"cedula": "1005280752",   "nombre": "Villalba Parra Miguel Andres"},
    {"cedula": "1073522898",   "nombre": "Cruz Valencia Angie Vanessa"},
    {"cedula": "1015398775",   "nombre": "Pinilla Gomez Yuly Esperanza"},
    {"cedula": "1073250868",   "nombre": "Garzon Hidalgo Juan Diego"},
    {"cedula": "1020721203",   "nombre": "Correa Hernandez Yulia Dayana"},
    {"cedula": "1001202459",   "nombre": "Lopez Murcia Lizeth Dayan"},
    {"cedula": "6121188",      "nombre": "Martinez Miquilena Mariana Teresa"},
    {"cedula": "1015455835",   "nombre": "Umbarila Perez Nathaly Geraldine"},
    {"cedula": "1111042316",   "nombre": "Quiñones Capera Andrea Milena"},
    {"cedula": "1002962256",   "nombre": "Almario Fernandez Karen Dayana"},
    {"cedula": "1003535288",   "nombre": "Hernandez Gonzalez Danna Valentina"},
    {"cedula": "1193546005",   "nombre": "Garcia Rayo Solanyi"},
    {"cedula": "53119259",     "nombre": "Andrade Leal Jenny Julieth"},
    {"cedula": "1070970308",   "nombre": "Ramos Ayala Diana Fernanda"},
    {"cedula": "1007646063",   "nombre": "Suarez Romero Leidy Viviana"},
    {"cedula": "1000331165",   "nombre": "Muñoz Castellanos Ximena"},
    {"cedula": "1073171504",   "nombre": "Velasco Gonzalez Karen Viviana"},
    {"cedula": "1073151069",   "nombre": "Hernandez Rodriguez Maria Esnid"},
    {"cedula": "1012342751",   "nombre": "Soto Castro Mayra Alejandra"},
    {"cedula": "1063787776",   "nombre": "Calle Negrete Jelen Karina"},
    {"cedula": "1006791000",   "nombre": "Robles Roys Liseth Tatiana"},
    {"cedula": "1140879014",   "nombre": "Villamizar Ramos Eliana Patricia"},
    {"cedula": "11367547",     "nombre": "Sanchez Sarmiento Yesid"},
]

# ─────────────────────────────────────────────
# PRODUCTOS
# ─────────────────────────────────────────────

productos = [
    {"codigo": "2330470005",    "descripcion": "ACOPLE FEMENINO 24 HORAS LILA",                              "ciclos": 18.0,  "cavidades": 4,  "material": "polietileno de alta densidad"},
    {"codigo": "2330470006",    "descripcion": "ACOPLE FEMENINO 24 HORAS AMBAR",                             "ciclos": 16.6,  "cavidades": 4,  "material": "polipropileno homopolimero"},
    {"codigo": "2430470002",    "descripcion": "TAPA RECOLECTOR ORINA 24H",                                  "ciclos": 15.4,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "2430470003",    "descripcion": "TAPA RECOLECTOR ORINA 24H",                                  "ciclos": 15.4,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "2430470004",    "descripcion": "TAPA RECOLECTOR 24 HORAS LILA",                              "ciclos": 19.0,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "2430470005",    "descripcion": "TAPA RECOLECTOR 24 HORAS AZUL SIN MARCA",                    "ciclos": 15.4,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "2430470007",    "descripcion": "TAPA RECOLECTOR 24 HORAS AZUL",                              "ciclos": 15.4,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "2430470008",    "descripcion": "ACOPLE FEMENINO 24 HORAS AZUL (ICOM)",                       "ciclos": 16.6,  "cavidades": 4,  "material": "polipropileno homopolimero"},
    {"codigo": "2440330001",    "descripcion": "VALVULA TUBO NATURAL PUNTA DE FLECHA",                       "ciclos": 28.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "2440330002",    "descripcion": "VALVULA TUBO NATURAL PUNTA DE FLECHA",                       "ciclos": 22.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3030300001",    "descripcion": "BAJA LENGUAS INV PLAST ADU COLOR",                           "ciclos": 17.4,  "cavidades": 8,  "material": "poliestireno"},
    {"codigo": "3030300003",    "descripcion": "BAJA LENGUAS INV PLAST ADU TRANS X 20 UND",                  "ciclos": 20.0,  "cavidades": 8,  "material": "poliestireno"},
    {"codigo": "3030300004AM",  "descripcion": "BAJA LENGUAS INV PLAST PED COLORE X 20 AMARILLO",            "ciclos": 14.0,  "cavidades": 4,  "material": "poliestireno"},
    {"codigo": "3030300004LI",  "descripcion": "BAJA LENGUAS INV PLAST PED COLORE X 20 LILA",               "ciclos": 14.0,  "cavidades": 4,  "material": "poliestireno"},
    {"codigo": "3130070002",    "descripcion": "ESPECULO VAGINAL TALLA M",                                   "ciclos": 28.0,  "cavidades": 1,  "material": "policarbonato"},
    {"codigo": "3130280002",    "descripcion": "ESPECULO VAGINAL TALLA S",                                   "ciclos": 35.3,  "cavidades": 1,  "material": "policarbonato"},
    {"codigo": "3170070001MA",  "descripcion": "MASCARA INHALOCAMARA INST ADULT",                            "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070001TB",  "descripcion": "TUBO INHALOCAMARA INST ADULT",                               "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070001TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA INST ADULTO",                     "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070002MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070002TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070002TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070002VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170070003MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070003TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070003TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070003VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170070004MA",  "descripcion": "MASCARA INHALOCAMARA FORMATODO",                             "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070004TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070004TP",  "descripcion": "TAPA INFERIOR VERDE FORMATODO",                              "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070012",    "descripcion": "INHALOCAMARA AIRFARM PLUS ADULTO VERDE",                     "ciclos": 48.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070012MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070012TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170070012TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170070012VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280001MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280001TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280001TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280001VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280002MA",  "descripcion": "MASCARA PEDIATRICA INV",                                     "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280002TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280002TP",  "descripcion": "MASCARA PEDIATRICA",                                         "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280004MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280004TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280004TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 34.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280004VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280005MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280005TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280005TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280005VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280008MA",  "descripcion": "MASCARA INHALOCAMARA AIRFARM PEDIATRICA AZUL",               "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280008TB",  "descripcion": "TUBO INHALOCAMARA AIRFARM PEDIATRICA AZUL",                  "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280008TP",  "descripcion": "TAPA INF INHALOCAMARA AIRFARM PEDIATRICA AZUL",              "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280009MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280009TB",  "descripcion": "TUBO INHALOCAMARA",                                          "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280009TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280009VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280010MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280010TB",  "descripcion": "TUBO PED SERIGRAFIA ROSADO",                                 "ciclos": 26.7,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280010TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280010VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280011MA",  "descripcion": "MASCARA INHALOCAMARA",                                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280011TB",  "descripcion": "TUBO INHALOCAMARA POLICARBONATO",                            "ciclos": 30.0,  "cavidades": 1,  "material": "policarbonato"},
    {"codigo": "3170280011TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA",                                 "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280011VL",  "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3170280012MA",  "descripcion": "MASCARA INHALOCAMARA OXIS ADULTO",                           "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280012TB",  "descripcion": "TUBO INHALOCAMARA OXIS ADULTO",                              "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280012TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA OXIS ADULTO",                     "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280013MA",  "descripcion": "MASCARA INHALOCAMARA OXIS PEDIATRICA",                       "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280013TB",  "descripcion": "TUBO INHALOCAMARA OXIS PEDIATRICA",                          "ciclos": 25.0,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280013TP",  "descripcion": "TAPA INFERIOR INHALOCAMARA OXIS PEDIATRICA",                 "ciclos": 35.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280014MA",  "descripcion": "MASCARA INHALOCAMARA INVERFARMA USO INTITUCIONAL ADULTO",    "ciclos": 45.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "3170280014TB",  "descripcion": "INHALOCAMARA INVERFARMA USO INTITUCIONAL ADULTO",            "ciclos": 21.5,  "cavidades": 4,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3170280014TP",  "descripcion": "TAPA INFERIOR INVERFARMA USO INTITUCIONAL ADULTO",           "ciclos": 42.0,  "cavidades": 4,  "material": "pvc"},
    {"codigo": "317028001VL",   "descripcion": "VALVULA INHALOCAMARA",                                       "ciclos": 25.0,  "cavidades": 8,  "material": "pvc"},
    {"codigo": "3240330001",    "descripcion": "FRASCO COPROLOGICO INV X 50 UND",                            "ciclos": 11.5,  "cavidades": 4,  "material": "polietileno de alta densidad"},
    {"codigo": "3240330004",    "descripcion": "FRASCO COPROLOGICO INV X 25 UND",                            "ciclos": 11.0,  "cavidades": 4,  "material": "polietileno de alta densidad"},
    {"codigo": "3240330005",    "descripcion": "FRASCO COPROLOGICO",                                         "ciclos": 11.0,  "cavidades": 4,  "material": "polietileno de alta densidad"},
    {"codigo": "3240330018FR",  "descripcion": "FRASCO COPROLOGICO DON BOTIQUIN",                            "ciclos": 9.0,   "cavidades": 8,  "material": "polietileno de alta densidad"},
    {"codigo": "3240330018TP",  "descripcion": "TAPA COPROLOGICO DON BOTIQUIN",                              "ciclos": 19.0,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "3250330003",    "descripcion": "RECOLECTOR GUARDIAN INV 1,5 L",                              "ciclos": 23.8,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3250330003TP",  "descripcion": "TAPA RECOLECTOR GUARDIAN 1,5LT",                             "ciclos": 21.3,  "cavidades": 2,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3250330005FR",  "descripcion": "RECOLECTOR GUARDIAN INV 3 L",                                "ciclos": 27.8,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3250330005TP",  "descripcion": "TAPA GUARDIAN 3LT",                                          "ciclos": 19.6,  "cavidades": 2,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330003",    "descripcion": "FRASCO RECOLECTOR ORINA INVER X 50",                         "ciclos": 27.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330003FR",  "descripcion": "FRASCO ORINA INVERFARMA",                                    "ciclos": 12.0,  "cavidades": 12, "material": "polipropileno homopolimero"},
    {"codigo": "3260330003TP",  "descripcion": "TAPA FRASCO ORINA INVERFARMA",                               "ciclos": 11.5,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330005",    "descripcion": "FRASCO RECOLECTOR ORINA INVER X 25",                         "ciclos": 25.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330005FR",  "descripcion": "FRASCO ORINA X 25 UND",                                      "ciclos": 12.0,  "cavidades": 12, "material": "polipropileno homopolimero"},
    {"codigo": "3260330005TP",  "descripcion": "TAPA FRASCO ORINA X 25 IND",                                 "ciclos": 11.5,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330007",    "descripcion": "FRASCO RECOLECTOR ORINA ICOM",                               "ciclos": 24.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330007COP", "descripcion": "FRASCO RECOLECTOR ORINA ICOM",                               "ciclos": 40.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330007FR",  "descripcion": "FRASCO ORINA FAST CARE",                                     "ciclos": 12.5,  "cavidades": 9,  "material": "polipropeno homopolimero"},
    {"codigo": "3260330007TP",  "descripcion": "TAPA FRASCO ORINA FAST CARE",                                "ciclos": 11.5,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330010FR",  "descripcion": "FRASCO COPROLOGICO HOSPITALARY",                             "ciclos": 9.0,   "cavidades": 8,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330010TP",  "descripcion": "TAPA COPROLOGICO HOSPITALARY",                               "ciclos": 19.0,  "cavidades": 6,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330011",    "descripcion": "FRASCO RECOLECTOR ORINA HOSPITALARY",                        "ciclos": 22.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330011FR",  "descripcion": "FRASCO ORINA HOSPITALARY",                                   "ciclos": 12.0,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330011TP",  "descripcion": "TAPA FRASCO ORINA HOSPITALARY X 50 UND",                     "ciclos": 11.5,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330012",    "descripcion": "RECOLECTOR 24 HORAS HOSPITALARY",                            "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330013",    "descripcion": "RECOLECTOR 24 HORAS LILA FEMENINO HOSPITALARY",              "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330014",    "descripcion": "RECOLECTOR 24 HORAS FAST CARE (ICOM)",                       "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330016",    "descripcion": "RECOLECTOR 24 HORAS NATURAL P Y S",                          "ciclos": 24.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330017",    "descripcion": "RECOLECTOR 24 HORAS AMBAR P Y S",                            "ciclos": 24.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3260330018",    "descripcion": "FRASCO RECOLECTOR ORINA DON BOTIQUIN",                       "ciclos": 25.0,  "cavidades": 0,  "material": "polipropileno homopolimero"},
    {"codigo": "3260330018FR",  "descripcion": "FRASCO ORINA DON BOTIQUIN",                                  "ciclos": 12.0,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330018TP",  "descripcion": "TAPA FRASCO ORINA DON BOTIQUIN",                             "ciclos": 11.5,  "cavidades": 12, "material": "polietileno de alta densidad"},
    {"codigo": "3260330020",    "descripcion": "RECOLECTOR 24 HORAS DON BOTIQUIN",                           "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "3480360001",    "descripcion": "PASTILLERO INV AM/PM",                                       "ciclos": 17.0,  "cavidades": 1,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "3490330032",    "descripcion": "TEE DE GOLF LARGO AMARILLO",                                 "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330033",    "descripcion": "TEE DE GOLF CORTO AMARILLO",                                 "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330035",    "descripcion": "TEE DE GOLF LARGO BLANCO",                                   "ciclos": 20.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330036",    "descripcion": "TEE DE GOLF CORTO BLANCO",                                   "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330038",    "descripcion": "TEE DE GOLF LARGO ROSADO",                                   "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330039",    "descripcion": "TEE DE GOLF CORTO ROSADO",                                   "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330042",    "descripcion": "TEE DE GOLF LARGO NARANJA",                                  "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490330043",    "descripcion": "TEE DE GOLF CORTO NARANJA",                                  "ciclos": 25.0,  "cavidades": 3,  "material": "abs"},
    {"codigo": "3490360005",    "descripcion": "PASTILLERO SEMANAL NATURAL",                                 "ciclos": 25.0,  "cavidades": 1,  "material": "polipropileno copolimero ramdon"},
    {"codigo": "4260330005",    "descripcion": "INVERFARMARMA RECOLECTOR 24 HORAS",                          "ciclos": 12.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "4260330007",    "descripcion": "RECOLECTOR 24 HORAS AMBAR INVERFARMA",                       "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "4260330011",    "descripcion": "RECOLECTOR 24 HORAS AMBAR FEMENINO",                         "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
    {"codigo": "4260330012",    "descripcion": "RECOLECTOR 24 HORAS FEMENINO",                               "ciclos": 18.0,  "cavidades": 1,  "material": "polietileno de alta densidad"},
]


# ─────────────────────────────────────────────
# INSERTAR EN BD (sin duplicar)
# ─────────────────────────────────────────────

def poblar():
    insertados = {"lideres": 0, "empleados": 0, "productos": 0}
    omitidos   = {"lideres": 0, "empleados": 0, "productos": 0}

    print("\n── Poblando LÍDERES ──")
    for l in lideres:
        existe = db.query(Lider).filter(Lider.cedula == l["cedula"]).first()
        if not existe:
            db.add(Lider(cedula=l["cedula"], nombre=l["nombre"], activo=True))
            insertados["lideres"] += 1
            print(f"  ✓ {l['nombre']}")
        else:
            omitidos["lideres"] += 1
            print(f"  - Ya existe: {l['nombre']}")

    print("\n── Poblando EMPLEADOS ──")
    for e in empleados:
        existe = db.query(Empleado).filter(Empleado.cedula == e["cedula"]).first()
        if not existe:
            db.add(Empleado(cedula=e["cedula"], nombre=e["nombre"], activo=True))
            insertados["empleados"] += 1
            print(f"  ✓ {e['nombre']}")
        else:
            omitidos["empleados"] += 1
            print(f"  - Ya existe: {e['nombre']}")

    print("\n── Poblando PRODUCTOS ──")
    for p in productos:
        existe = db.query(Producto).filter(Producto.codigo == p["codigo"]).first()
        if not existe:
            db.add(Producto(
                codigo=p["codigo"],
                descripcion=p["descripcion"],
                ciclos=p["ciclos"],
                cavidades=p["cavidades"],
                material=p["material"],
                activo=True
            ))
            insertados["productos"] += 1
            print(f"  ✓ {p['codigo']} — {p['descripcion']}")
        else:
            omitidos["productos"] += 1
            print(f"  - Ya existe: {p['codigo']}")

    db.commit()
    db.close()

    print("\n══════════════════════════════")
    print(f"  Líderes:   {insertados['lideres']} insertados, {omitidos['lideres']} omitidos")
    print(f"  Empleados: {insertados['empleados']} insertados, {omitidos['empleados']} omitidos")
    print(f"  Productos: {insertados['productos']} insertados, {omitidos['productos']} omitidos")
    print("  ✅ Base de datos poblada correctamente")
    print("══════════════════════════════\n")

if __name__ == "__main__":
    poblar()

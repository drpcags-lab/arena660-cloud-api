from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
import sqlite3 # O puedes usar psycopg2 / SQLAlchemy para PostgreSQL en producción

app = FastAPI(title="ARENA 6-60 Cloud ERP API", version="1.0")

# En producción, cambia esto por tu conexión a PostgreSQL (ej. Supabase o Neon)
DB_CLOUD = "gimnasio_cloud.db"

def init_cloud_db():
    with sqlite3.connect(DB_CLOUD) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS socios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                huella_id INTEGER UNIQUE,
                fecha_vencimiento DATE NOT NULL,
                telefono TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                dias_vigencia INTEGER DEFAULT 0,
                tipo TEXT DEFAULT 'MEMBRESIA'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accesos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                socio_id INTEGER,
                nombre_cliente TEXT,
                fecha_hora DATETIME,
                tipo_acceso TEXT,
                monto_pagado REAL DEFAULT 0.0,
                concepto TEXT DEFAULT 'ACCESO'
            )
        ''')
        conn.commit()

init_cloud_db()

# Modelos de validación con Pydantic
class SocioModel(BaseModel):
    nombre: str
    huella_id: int
    telefono: Optional[str] = None

class ProductoModel(BaseModel):
    nombre: str
    precio: float
    dias_vigencia: int
    tipo: str = "MEMBRESIA"

class AccesoModel(BaseModel):
    socio_id: Optional[int] = None
    nombre_cliente: str
    fecha_hora: str
    tipo_acceso: str
    monto_pagado: float
    concepto: str

# -------------------------------------------------------------------------
# ENDPOINTS: ACCESOS Y VENTAS (Recibidos desde el gimnasio)
# -------------------------------------------------------------------------
@app.post("/api/accesos")
def registrar_acceso_cloud(acceso: AccesoModel):
    with sqlite3.connect(DB_CLOUD) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accesos (socio_id, nombre_cliente, fecha_hora, tipo_acceso, monto_pagado, concepto)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (acceso.socio_id, acceso.nombre_cliente, acceso.fecha_hora, acceso.tipo_acceso, acceso.monto_pagado, acceso.concepto))
        conn.commit()
    return {"status": "success", "message": "Acceso/Venta sincronizado en la nube."}

# -------------------------------------------------------------------------
# ENDPOINTS: SOCIOS (Control remoto desde la app del admin)
# -------------------------------------------------------------------------
@app.get("/api/socios")
def obtener_socios():
    with sqlite3.connect(DB_CLOUD) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, huella_id, fecha_vencimiento, telefono FROM socios ORDER BY id DESC")
        socios = [{"id": r[0], "nombre": r[1], "huella_id": r[2], "fecha_vencimiento": r[3], "telefono": r[4]} for r in cursor.fetchall()]
    return {"status": "success", "data": socios}

@app.post("/api/socios")
def crear_socio_cloud(socio: SocioModel):
    hoy_str = date.today().strftime("%Y-%m-%d")
    try:
        with sqlite3.connect(DB_CLOUD) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO socios (nombre, huella_id, fecha_vencimiento, telefono) VALUES (?, ?, ?, ?)",
                           (socio.nombre, socio.huella_id, hoy_str, socio.telefono))
            conn.commit()
        return {"status": "success", "message": f"Socio '{socio.nombre}' creado en la nube."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -------------------------------------------------------------------------
# ENDPOINTS: PRODUCTOS Y PRECIOS
# -------------------------------------------------------------------------
@app.get("/api/productos")
def obtener_productos():
    with sqlite3.connect(DB_CLOUD) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, precio, dias_vigencia, tipo FROM productos")
        prods = [{"id": r[0], "nombre": r[1], "precio": r[2], "dias_vigencia": r[3], "tipo": r[4]} for r in cursor.fetchall()]
    return {"status": "success", "data": prods}

@app.post("/api/productos")
def crear_producto_cloud(prod: ProductoModel):
    with sqlite3.connect(DB_CLOUD) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, precio, dias_vigencia, tipo) VALUES (?, ?, ?, ?)",
                       (prod.nombre, prod.precio, prod.dias_vigencia, prod.tipo))
        conn.commit()
    return {"status": "success", "message": f"Producto '{prod.nombre}' actualizado."}
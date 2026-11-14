from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import os
from datetime import datetime

app = FastAPI(title="ARENA 6-60 Cloud ERP API", version="1.0")

DB_NAME = "gimnasio_cloud.db"

def init_cloud_db():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
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
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                tipo_acceso TEXT,
                monto_pagado REAL DEFAULT 0.0,
                concepto TEXT DEFAULT 'ACCESO'
            )
        ''')
        
        # Datos de prueba iniciales si está vacía
        cursor.execute("SELECT COUNT(*) FROM productos")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO productos (nombre, precio, dias_vigencia, tipo) VALUES (?, ?, ?, ?)", ("Mensualidad Individual", 450.0, 30, "MEMBRESIA"))
            cursor.execute("INSERT INTO productos (nombre, precio, dias_vigencia, tipo) VALUES (?, ?, ?, ?)", ("Visita Diaria", 50.0, 0, "PRODUCTO"))
            conn.commit()

init_cloud_db()

# Modelos Pydantic
class AccesoModel(BaseModel):
    socio_id: int = None
    nombre_cliente: str
    fecha_hora: str = None
    tipo_acceso: str
    monto_pagado: float = 0.0
    concepto: str = "ACCESO"

class SocioModel(BaseModel):
    id: int
    nombre: str
    huella_id: int
    fecha_vencimiento: str
    telefono: str = None

class ProductoModel(BaseModel):
    nombre: str
    precio: float
    dias_vigencia: int = 0
    tipo: str = "MEMBRESIA"

# =============================================================================
# DASHBOARD MÓVIL (VISTA WEB PARA CELULAR)
# =============================================================================
@app.get("/", response_class=HTMLResponse)
def dashboard_movil():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        
        # Estadísticas del día
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*), SUM(monto_pagado) FROM accesos WHERE DATE(fecha_hora) = ?", (hoy_str,))
        res_hoy = cursor.fetchone()
        total_accesos_hoy = res_hoy[0] if res_hoy[0] else 0
        ingresos_hoy = res_hoy[1] if res_hoy[1] else 0.0
        
        # Total socios activos
        cursor.execute("SELECT COUNT(*) FROM socios WHERE fecha_vencimiento >= DATE('now')")
        socios_activos = cursor.fetchone()[0]
        
        # Últimos accesos
        cursor.execute("SELECT nombre_cliente, tipo_acceso, monto_pagado, fecha_hora, concepto FROM accesos ORDER BY id DESC LIMIT 10")
        ultimos = cursor.fetchall()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ARENA 6-60 - Mobile ERP</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Montserrat:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{ background-color: #000000; color: #FFFFFF; font-family: 'Montserrat', sans-serif; }}
            .font-orbitron {{ font-family: 'Orbitron', sans-serif; }}
            .card-bg {{ background-color: #121212; border: 1px solid #1a1a1a; }}
            .btn-primary {{ background-color: #157ADA; }}
            .btn-primary:hover {{ background-color: #0F5A9A; }}
        </style>
    </head>
    <body class="p-4 max-w-md mx-auto">
        <!-- Encabezado -->
        <header class="text-center my-6">
            <h1 class="font-orbitron text-3xl font-black tracking-wider text-[#157ADA]">ARENA <span class="text-white">6-60</span></h1>
            <p class="text-xs text-gray-400 mt-1 tracking-widest uppercase">Panel de Control en la Nube</p>
        </header>

        <!-- Tarjetas de Resumen -->
        <div class="grid grid-cols-2 gap-3 mb-6">
            <div class="card-bg p-4 rounded-xl text-center">
                <p class="text-xs text-gray-400 font-semibold uppercase">Ingresos Hoy</p>
                <p class="font-orbitron text-xl font-bold text-emerald-400 mt-1">${ingresos_hoy:.2f}</p>
            </div>
            <div class="card-bg p-4 rounded-xl text-center">
                <p class="text-xs text-gray-400 font-semibold uppercase">Accesos Hoy</p>
                <p class="font-orbitron text-xl font-bold text-[#157ADA] mt-1">{total_accesos_hoy}</p>
            </div>
        </div>

        <div class="card-bg p-4 rounded-xl mb-6 text-center">
            <p class="text-xs text-gray-400 font-semibold uppercase">Socios con Membresía Vigente</p>
            <p class="font-orbitron text-2xl font-bold text-white mt-1">{socios_activos}</p>
        </div>

        <!-- Enlaces Rápidos -->
        <div class="flex gap-2 mb-6">
            <a href="/docs" target="_blank" class="flex-1 text-center py-3 rounded-xl btn-primary font-bold text-sm tracking-wide shadow-lg shadow-blue-900/30">⚙️ Ver API / Docs</a>
            <a href="/api/socios" target="_blank" class="flex-1 text-center py-3 rounded-xl bg-[#222222] text-gray-300 font-bold text-sm tracking-wide border border-gray-800">👤 Ver Socios JSON</a>
        </div>

        <!-- Bitácora Reciente -->
        <div class="card-bg p-4 rounded-xl">
            <h2 class="font-orbitron text-sm font-bold text-[#157ADA] mb-3 uppercase tracking-wider">Últimos Movimientos</h2>
            <div class="space-y-3">
    """
    
    if not ultimos:
        html_content += '<p class="text-xs text-gray-500 text-center py-4">No hay accesos registrados todavía.</p>'
    else:
        for nombre, tipo, monto, fecha, concepto in ultimos:
            color_badge = "text-emerald-400 bg-emerald-950/40 border-emerald-900/50" if "VIGENTE" in tipo or "VENTA" in tipo else "text-amber-400 bg-amber-950/40 border-amber-900/50"
            html_content += f"""
                <div class="bg-black/40 p-3 rounded-lg border border-gray-800/60 text-xs">
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-bold text-white uppercase text-sm">{nombre}</span>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold border {color_badge}">{tipo}</span>
                    </div>
                    <div class="text-gray-400 flex justify-between mt-1">
                        <span>{concepto}</span>
                        <span class="text-emerald-400 font-bold">${monto:.2f}</span>
                    </div>
                    <div class="text-[10px] text-gray-500 mt-1">{fecha}</div>
                </div>
            """

    html_content += f"""
            </div>
        </div>

        <!-- Footer -->
        <footer class="text-center text-[10px] text-gray-600 mt-8 mb-4">
            ARENA 6-60 Cloud ERP &bull; Sincronizado en tiempo real
        </footer>
    </body>
    </html>
    """
    return html_content

# =============================================================================
# ENDPOINTS DE LA API
# =============================================================================
@app.post("/api/accesos")
def registrar_acceso(acc: AccesoModel):
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accesos (socio_id, nombre_cliente, fecha_hora, tipo_acceso, monto_pagado, concepto) 
            VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?)
        """, (acc.socio_id, acc.nombre_cliente, acc.fecha_hora, acc.tipo_acceso, acc.monto_pagado, acc.concepto))
        conn.commit()
    return {"status": "success", "message": "Acceso/Venta sincronizado correctamente"}

@app.get("/api/socios")
def obtener_socios():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, huella_id, fecha_vencimiento, telefono FROM socios")
        rows = cursor.fetchall()
        data = [{"id": r[0], "nombre": r[1], "huella_id": r[2], "fecha_vencimiento": r[3], "telefono": r[4]} for r in rows]
    return {"status": "success", "data": data}

@app.post("/api/socios")
def crear_socio_cloud(socio: SocioModel):
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO socios (id, nombre, huella_id, fecha_vencimiento, telefono) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
            nombre=excluded.nombre, 
            fecha_vencimiento=excluded.fecha_vencimiento, 
            telefono=excluded.telefono
        """, (socio.id, socio.nombre, socio.huella_id, socio.fecha_vencimiento, socio.telefono))
        conn.commit()
    return {"status": "success", "message": "Socio sincronizado en la nube"}

@app.get("/api/productos")
def obtener_productos():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, precio, dias_vigencia, tipo FROM productos")
        rows = cursor.fetchall()
        data = [{"id": r[0], "nombre": r[1], "precio": r[2], "dias_vigencia": r[3], "tipo": r[4]} for r in rows]
    return {"status": "success", "data": data}

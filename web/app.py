"""
Servidor web Flask para BuscaElectro Colombia.
"""

import sys
import os
import json
import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Cargar .env si existe
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k.replace("_", "").isalnum():
            os.environ.setdefault(k, v)

# Ruta de la BD: usar variable de entorno en producción o ruta local
DB_DIR = os.environ.get("DB_DIR", str(Path(__file__).parent.parent))
os.environ.setdefault("DB_PATH", str(Path(DB_DIR) / "productos.db"))

sys.path.insert(0, str(Path(__file__).parent.parent / "scraper"))
from db import buscar_productos, obtener_estadisticas, get_conexion
from ia import interpretar_consulta, generar_resumen

app = Flask(__name__)


@app.route("/")
def index():
    stats = obtener_estadisticas()
    return render_template("index.html", stats=stats)


@app.route("/api/destacados")
def api_destacados():
    """Retorna productos con mayor descuento por categoría para la pantalla de inicio."""
    conn = get_conexion()
    resultados = []

    categorias = ["neveras", "televisores", "lavadoras", "aires acondicionados",
                  "microondas", "estufas"]

    for cat in categorias:
        # Buscar por categoría con LIKE para cubrir variantes (neveras, nevera, etc.)
        filas = conn.execute("""
            SELECT * FROM productos
            WHERE categoria LIKE ?
              AND precio_original IS NOT NULL
              AND precio_original > precio * 1.05
              AND imagen != ''
              AND precio > 100000
            ORDER BY (precio_original - precio) / precio_original DESC
            LIMIT 4
        """, (f"%{cat.rstrip('s')}%",)).fetchall()

        # Si no hay descuentos, tomar los más baratos con imagen
        if not filas:
            filas = conn.execute("""
                SELECT * FROM productos
                WHERE categoria LIKE ? AND imagen != '' AND precio > 100000
                ORDER BY precio ASC
                LIMIT 4
            """, (f"%{cat.rstrip('s')}%",)).fetchall()

        for f in filas:
            resultados.append(dict(f))

    conn.close()
    grupos = _agrupar_por_nombre(resultados)
    # Limitar a 16 productos destacados totales
    return jsonify({"productos": grupos[:16]})


@app.route("/api/buscar")
def api_buscar():
    consulta_original = request.args.get("q", "").strip()
    limite = int(request.args.get("limite", 60))
    precio_min = request.args.get("precio_min", type=float)
    precio_max = request.args.get("precio_max", type=float)
    tiendas_filtro = request.args.getlist("tienda")

    if not consulta_original:
        return jsonify({"productos": [], "total": 0})

    tiene_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    usa_ia = _es_lenguaje_natural(consulta_original) and tiene_api_key
    interpretacion = None
    resumen_ia = None

    if usa_ia:
        interpretacion = interpretar_consulta(consulta_original)
        termino = interpretacion.get("termino", consulta_original)
        categoria = interpretacion.get("categoria")
    else:
        termino = consulta_original
        categoria = request.args.get("categoria") or None

    productos_raw = buscar_productos(termino, categoria=categoria, limite=limite)

    # Aplicar filtros de precio y tienda
    if precio_min is not None:
        productos_raw = [p for p in productos_raw if p["precio"] >= precio_min]
    if precio_max is not None:
        productos_raw = [p for p in productos_raw if p["precio"] <= precio_max]
    if tiendas_filtro:
        productos_raw = [p for p in productos_raw if p["tienda"] in tiendas_filtro]

    grupos = _agrupar_por_nombre(productos_raw)

    if usa_ia and grupos and not interpretacion.get("error"):
        resumen_ia = generar_resumen(consulta_original, grupos)

    respuesta = {
        "productos": grupos,
        "total": len(grupos),
        "termino": termino,
        "consulta_original": consulta_original,
        "usa_ia": usa_ia,
    }
    if interpretacion:
        respuesta["interpretacion"] = {
            "explicacion": interpretacion.get("explicacion"),
            "categoria": interpretacion.get("categoria"),
        }
    if resumen_ia:
        respuesta["resumen_ia"] = resumen_ia

    return jsonify(respuesta)


@app.route("/api/stats")
def api_stats():
    return jsonify(obtener_estadisticas())


# ── helpers ──────────────────────────────────────────────────────────────────

def _es_lenguaje_natural(texto: str) -> bool:
    palabras = texto.split()
    if len(palabras) >= 4:
        return True
    funcionales = {"para","con","de","mi","una","un","que","sin","más","mas",
                   "muy","grande","pequeño","barata","barato","económica","económico"}
    return bool(set(w.lower() for w in palabras) & funcionales)


def _agrupar_por_nombre(productos: list) -> list:
    grupos = {}
    for p in productos:
        clave = " ".join(p["nombre"].lower().split()[:4])
        if clave not in grupos:
            grupos[clave] = {"nombre": p["nombre"], "categoria": p["categoria"], "tiendas": []}
        grupos[clave]["tiendas"].append({
            "tienda": p["tienda"],
            "precio": p["precio"],
            "precio_original": p.get("precio_original"),
            "url": p["url"],
            "imagen": p["imagen"],
            "actualizado": p.get("actualizado", ""),
        })

    for g in grupos.values():
        g["tiendas"].sort(key=lambda x: x["precio"])
        g["precio_min"] = g["tiendas"][0]["precio"]
        g["imagen"] = next((t["imagen"] for t in g["tiendas"] if t["imagen"]), "")
        mejor = g["tiendas"][0]
        if mejor.get("precio_original") and mejor["precio_original"] > mejor["precio"]:
            g["descuento_pct"] = round((1 - mejor["precio"] / mejor["precio_original"]) * 100)
        else:
            g["descuento_pct"] = 0

    return sorted(grupos.values(), key=lambda x: x["precio_min"])


if __name__ == "__main__":
    app.run(debug=True, port=5000)

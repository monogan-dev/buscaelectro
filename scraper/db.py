"""
Base de datos SQLite para guardar productos scrapeados.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Permite sobreescribir la ruta en producción (Railway, Render, etc.)
_default = Path(__file__).parent.parent / "productos.db"
DB_PATH = Path(os.environ.get("DB_PATH", str(_default)))


def get_conexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """Crea las tablas si no existen."""
    conn = get_conexion()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS productos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT NOT NULL,
            precio          REAL NOT NULL,
            precio_original REAL,
            url             TEXT,
            imagen          TEXT,
            tienda          TEXT NOT NULL,
            categoria       TEXT,
            actualizado     TEXT NOT NULL
        );

        -- Índice para búsqueda por texto
        CREATE VIRTUAL TABLE IF NOT EXISTS productos_fts
        USING fts5(nombre, categoria, content='productos', content_rowid='id');

        -- Trigger para mantener el índice FTS sincronizado
        CREATE TRIGGER IF NOT EXISTS productos_ai AFTER INSERT ON productos BEGIN
            INSERT INTO productos_fts(rowid, nombre, categoria)
            VALUES (new.id, new.nombre, new.categoria);
        END;

        CREATE TRIGGER IF NOT EXISTS productos_ad AFTER DELETE ON productos BEGIN
            INSERT INTO productos_fts(productos_fts, rowid, nombre, categoria)
            VALUES ('delete', old.id, old.nombre, old.categoria);
        END;
    """)
    conn.commit()
    conn.close()


def guardar_productos(productos: list[dict]):
    """
    Inserta o actualiza productos en la BD.
    Si ya existe un producto con el mismo nombre y tienda, actualiza el precio.
    """
    if not productos:
        return

    conn = get_conexion()
    ahora = datetime.now().isoformat()

    for p in productos:
        if not p.get("nombre") or not p.get("precio"):
            continue

        # Verificar si ya existe
        fila = conn.execute(
            "SELECT id FROM productos WHERE nombre = ? AND tienda = ?",
            (p["nombre"], p["tienda"])
        ).fetchone()

        precio_original = p.get("precio_original")

        if fila:
            conn.execute(
                "UPDATE productos SET precio=?, precio_original=?, url=?, imagen=?, categoria=?, actualizado=? WHERE id=?",
                (p["precio"], precio_original, p.get("url", ""), p.get("imagen", ""),
                 p.get("categoria", ""), ahora, fila["id"])
            )
        else:
            conn.execute(
                """INSERT INTO productos (nombre, precio, precio_original, url, imagen, tienda, categoria, actualizado)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (p["nombre"], p["precio"], precio_original, p.get("url", ""), p.get("imagen", ""),
                 p["tienda"], p.get("categoria", ""), ahora)
            )

    conn.commit()
    conn.close()


def buscar_productos(termino: str, categoria: str = None, limite: int = 20,
                     offset: int = 0) -> list[dict]:
    """
    Busca productos por texto usando FTS5.
    Retorna los resultados ordenados por precio ascendente.
    """
    conn = get_conexion()
    termino_fts = termino.replace('"', '').replace("'", "").strip()
    if not termino_fts:
        conn.close()
        return []

    if categoria:
        filas = conn.execute("""
            SELECT p.* FROM productos p
            JOIN productos_fts fts ON p.id = fts.rowid
            WHERE productos_fts MATCH ? AND p.categoria = ?
            ORDER BY p.precio ASC
            LIMIT ? OFFSET ?
        """, (termino_fts, categoria, limite, offset)).fetchall()
    else:
        filas = conn.execute("""
            SELECT p.* FROM productos p
            JOIN productos_fts fts ON p.id = fts.rowid
            WHERE productos_fts MATCH ?
            ORDER BY p.precio ASC
            LIMIT ? OFFSET ?
        """, (termino_fts, limite, offset)).fetchall()

    conn.close()
    return [dict(f) for f in filas]


def contar_productos_busqueda(termino: str, categoria: str = None) -> int:
    """Cuenta total de resultados para una búsqueda (para paginación)."""
    conn = get_conexion()
    termino_fts = termino.replace('"', '').replace("'", "").strip()
    if not termino_fts:
        conn.close()
        return 0

    if categoria:
        n = conn.execute("""
            SELECT COUNT(*) FROM productos p
            JOIN productos_fts fts ON p.id = fts.rowid
            WHERE productos_fts MATCH ? AND p.categoria = ?
        """, (termino_fts, categoria)).fetchone()[0]
    else:
        n = conn.execute("""
            SELECT COUNT(*) FROM productos p
            JOIN productos_fts fts ON p.id = fts.rowid
            WHERE productos_fts MATCH ?
        """, (termino_fts,)).fetchone()[0]

    conn.close()
    return n


def obtener_estadisticas() -> dict:
    """Retorna estadísticas básicas de la BD."""
    conn = get_conexion()
    stats = {
        "total_productos": conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0],
        "por_tienda": dict(conn.execute(
            "SELECT tienda, COUNT(*) FROM productos GROUP BY tienda"
        ).fetchall()),
        "por_categoria": dict(conn.execute(
            "SELECT categoria, COUNT(*) FROM productos GROUP BY categoria"
        ).fetchall()),
        "ultima_actualizacion": conn.execute(
            "SELECT MAX(actualizado) FROM productos"
        ).fetchone()[0],
    }
    conn.close()
    return stats


# Inicializar la BD al importar el módulo
inicializar_db()

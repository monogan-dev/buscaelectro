"""
Módulo de búsqueda con IA.
Convierte consultas en lenguaje natural a términos de búsqueda precisos
y genera una respuesta explicativa con los resultados.
"""

import os
import json
import anthropic

_cliente = None


def _get_cliente():
    global _cliente
    if _cliente is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Falta la variable de entorno ANTHROPIC_API_KEY")
        _cliente = anthropic.Anthropic(api_key=api_key)
    return _cliente


SISTEMA = """Eres un asistente de búsqueda de electrodomésticos para Colombia.
Tu trabajo es interpretar lo que el usuario quiere buscar y devolver un JSON con:
- "termino": el término de búsqueda más útil para la base de datos (1-3 palabras clave)
- "categoria": una de estas categorías si aplica: neveras, lavadoras, televisores, aires acondicionados, microondas, estufas, lavaplatos, secadoras. Si no aplica, usa null.
- "explicacion": una frase corta (max 15 palabras) explicando qué vas a buscar

Ejemplos:
- "nevera grande para familia de 5" → {"termino": "nevera no frost", "categoria": "neveras", "explicacion": "Neveras grandes No Frost, ideales para familias"}
- "tv para el cuarto de 32 pulgadas" → {"termino": "televisor 32", "categoria": "televisores", "explicacion": "Televisores de 32 pulgadas para habitación"}
- "algo para lavar la ropa sin gastar mucha agua" → {"termino": "lavadora inverter", "categoria": "lavadoras", "explicacion": "Lavadoras inverter, eficientes en consumo de agua"}
- "estufa de gas 4 puestos" → {"termino": "estufa gas 4", "categoria": "estufas", "explicacion": "Estufas a gas de 4 puestos"}

Responde SOLO con el JSON, sin texto adicional."""


def interpretar_consulta(consulta: str) -> dict:
    """
    Usa Claude Haiku para interpretar una consulta en lenguaje natural.
    Retorna dict con: termino, categoria, explicacion
    """
    try:
        cliente = _get_cliente()
        mensaje = cliente.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=SISTEMA,
            messages=[{"role": "user", "content": consulta}],
        )
        texto = mensaje.content[0].text.strip()
        return json.loads(texto)
    except (json.JSONDecodeError, KeyError, anthropic.APIError) as e:
        # Fallback: usar la consulta directamente sin IA
        return {
            "termino": consulta,
            "categoria": None,
            "explicacion": None,
            "error": str(e),
        }


def generar_resumen(consulta: str, productos: list[dict]) -> str:
    """
    Genera una respuesta conversacional breve sobre los resultados encontrados.
    Solo se llama si hay productos y la consulta parece lenguaje natural.
    """
    if not productos:
        return None

    # Preparar los 3 mejores resultados para el contexto
    top3 = []
    for p in productos[:3]:
        mejor = p["tiendas"][0]
        top3.append(
            f"- {p['nombre']} en {mejor['tienda']} por ${mejor['precio']:,.0f}"
        )
    contexto_productos = "\n".join(top3)

    try:
        cliente = _get_cliente()
        mensaje = cliente.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{
                "role": "user",
                "content": (
                    f"El usuario buscó: \"{consulta}\"\n"
                    f"Encontramos {len(productos)} productos. Los mejores:\n{contexto_productos}\n\n"
                    "Escribe UNA frase corta y amigable (máximo 20 palabras) resumiendo lo encontrado. "
                    "Menciona el precio más bajo si es relevante. Sin emojis."
                )
            }],
        )
        return mensaje.content[0].text.strip()
    except Exception:
        return None

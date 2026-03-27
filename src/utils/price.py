"""Utilidades para manejo de precios chilenos (CLP).

En Chile:
- El punto (.) es separador de miles: $149.990 = 149990 pesos
- Las comas (,) a veces se usan como alternativa al punto
- Los precios son siempre enteros (sin decimales)
- El simbolo de la moneda es $ o CLP
"""

import re

from src.schemas.product import ProductListing


def normalize_price(price_str: str) -> int | None:
    """Convierte un string de precio chileno a entero CLP.

    Maneja todos los formatos comunes en el mercado chileno:
    - "$149.990"       → 149990
    - "149990"         → 149990
    - "$149,990"       → 149990
    - "CLP 149.990"    → 149990
    - "149.990 CLP"    → 149990
    - "$ 149.990"      → 149990
    - "149.990,00"     → 149990  (formato europeo con decimales)

    Args:
        price_str: String de precio en cualquier formato chileno

    Returns:
        Precio como entero en CLP, o None si no se puede parsear.
    """
    if not price_str:
        return None

    # Remover simbolos de moneda y espacios
    clean = price_str.strip()
    clean = re.sub(r"[CLP$\s]", "", clean, flags=re.IGNORECASE)

    if not clean:
        return None

    # Caso: tiene tanto punto como coma → formato europeo (149.990,00)
    if "." in clean and "," in clean:
        # Eliminar el separador de miles (punto) y quitar los decimales (coma)
        clean = clean.replace(".", "").split(",")[0]
    elif "," in clean:
        # Solo coma: puede ser separador de miles (149,990) o decimal (149.990,50)
        # En Chile la coma como separador de miles es menos comun
        # Asumir que es separador de miles si hay 3 digitos despues
        parts = clean.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            # Separador de miles → 149,990
            clean = clean.replace(",", "")
        else:
            # Decimal → tomar parte entera
            clean = parts[0]
    elif "." in clean:
        # Solo punto: en Chile es separador de miles → eliminar
        # Verificar que no sea decimal (caso raro como "149.5")
        parts = clean.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Podria ser decimal (149.99) → tomar parte entera
            clean = parts[0]
        else:
            # Separador de miles → eliminar puntos
            clean = clean.replace(".", "")

    # Remover cualquier caracter que no sea digito
    clean = re.sub(r"\D", "", clean)

    if not clean:
        return None

    try:
        price = int(clean)
        return price if price > 0 else None
    except ValueError:
        return None


def calculate_discount(original: int, current: int) -> dict:
    """Calcula el descuento entre precio original y precio actual.

    Args:
        original: Precio original en CLP
        current: Precio actual en CLP

    Returns:
        Dict con: amount (ahorro en CLP), percentage (% descuento), is_deal (bool)
    """
    if original <= 0 or current <= 0 or original <= current:
        return {"amount": 0, "percentage": 0.0, "is_deal": False}

    amount = original - current
    percentage = round((amount / original) * 100, 1)
    is_deal = percentage >= 5.0  # Al menos 5% de descuento para considerarse oferta

    return {
        "amount": amount,
        "percentage": percentage,
        "is_deal": is_deal,
    }


def format_clp(price: int) -> str:
    """Formatea un precio entero como string de precio chileno.

    Args:
        price: Precio en CLP como entero (ej: 149990)

    Returns:
        String formateado con punto como separador de miles (ej: '$149.990')
    """
    if price <= 0:
        return "$0"
    # Formatear con punto como separador de miles
    formatted = f"{price:,}".replace(",", ".")
    return f"${formatted}"


def compare_prices(listings: list[ProductListing]) -> list[ProductListing]:
    """Ordena y deduplica una lista de ProductListing por precio.

    Elimina duplicados donde mismo producto en misma tienda aparece mas de una vez.
    El criterio de deduplicacion es: misma tienda y precio muy similar (+-1000 CLP).

    Args:
        listings: Lista de ProductListing a procesar

    Returns:
        Lista deduplicada y ordenada por precio ascendente.
    """
    if not listings:
        return []

    # Deduplicar: usar (store, price_bucket) como clave
    # price_bucket agrupa precios similares (redondeado a miles mas cercanos)
    seen: set[tuple[str, int]] = set()
    unique: list[ProductListing] = []

    for listing in listings:
        price_bucket = round(listing.price / 1000) * 1000  # Redondear a miles
        key = (listing.store.lower(), price_bucket)
        if key not in seen:
            seen.add(key)
            unique.append(listing)

    # Ordenar por precio ascendente
    return sorted(unique, key=lambda x: x.price)

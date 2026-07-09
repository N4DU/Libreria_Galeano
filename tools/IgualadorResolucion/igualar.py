# =============================================================
#  igualar.py  —  Igualador de resolución de imágenes
#  Coloca las imágenes en la carpeta "imagenes" que está junto
#  a este archivo y hacé doble clic para ejecutar.
#  Los resultados se sobreescriben y se genera un "log.txt".
# =============================================================

# ──────────────────────────────────────────────────────────────
#  CONFIGURACIÓN  ← editá estos valores antes de ejecutar
# ──────────────────────────────────────────────────────────────
ANCHO_OBJETIVO  = 683        # píxeles de ancho final
ALTO_OBJETIVO   = 1024        # píxeles de alto  final

METODO = "fill"
# "fit"  → la imagen entra completa; se agregan barras del COLOR_RELLENO
#          para completar el espacio sobrante (sin recorte, sin deformación)
# "fill" → la imagen llena todo el espacio; se recorta lo que sobra
#          del centro (sin barras, sin deformación)

COLOR_RELLENO = (255, 255, 255)
# Color de las barras cuando METODO = "fit"
# Blanco → (255, 255, 255)  |  Negro → (0, 0, 0)
# Gris   → (128, 128, 128)  |  Cualquier (R, G, B) entre 0 y 255

CALIDAD_JPEG = 90
# Calidad de recompresión para JPG/JPEG  (1 = mínima … 95 = máxima)
# No afecta PNG, BMP, TIFF ni WebP

PERMITIR_ESCALADO_HACIA_ARRIBA = True
# True  → también procesa imágenes más pequeñas que el objetivo
#         (puede verse pixelada si la diferencia es muy grande)
# False → omite las imágenes que sean más pequeñas que el objetivo
#         y las deja sin tocar
# ──────────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path
from datetime import datetime

EXTENSIONES_VALIDAS = {
    ".jpg", ".jpeg",   # JPEG
    ".png",            # PNG  (soporta transparencia)
    ".bmp",            # Bitmap
    ".tiff", ".tif",   # TIFF
    ".webp",           # WebP
    ".gif",            # GIF  (solo primer fotograma)
}


# ── Utilidades de log ──────────────────────────────────────────

def iniciar_log(ruta: Path) -> list:
    """Devuelve una lista vacía y escribe encabezado en el archivo."""
    lineas = []
    encabezado = (
        f"IgualadorResolucion — log de ejecución\n"
        f"Fecha  : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}\n"
        f"Destino: {ANCHO_OBJETIVO}x{ALTO_OBJETIVO}  |  Método: {METODO}  |  "
        f"Escalado ↑: {PERMITIR_ESCALADO_HACIA_ARRIBA}\n"
        f"{'─'*55}\n"
    )
    lineas.append(encabezado)
    return lineas


def guardar_log(lineas: list, ruta: Path):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


# ── Transformaciones de imagen ─────────────────────────────────

def aplicar_fit(img, ancho: int, alto: int, color: tuple):
    """Redimensiona manteniendo proporción y rellena con color."""
    from PIL import Image

    img_copia = img.copy()
    img_copia.thumbnail((ancho, alto), Image.LANCZOS)

    fondo = Image.new("RGBA", (ancho, alto), color + (255,))
    offset_x = (ancho - img_copia.width)  // 2
    offset_y = (alto  - img_copia.height) // 2

    if img_copia.mode == "RGBA":
        fondo.paste(img_copia, (offset_x, offset_y), img_copia)
    else:
        fondo.paste(img_copia.convert("RGBA"), (offset_x, offset_y))

    return fondo


def aplicar_fill(img, ancho: int, alto: int):
    """Redimensiona para llenar y recorta desde el centro."""
    from PIL import Image

    ratio_img = img.width  / img.height
    ratio_obj = ancho / alto

    if ratio_img > ratio_obj:
        nuevo_alto  = alto
        nuevo_ancho = round(ratio_img * alto)
    else:
        nuevo_ancho = ancho
        nuevo_alto  = round(ancho / ratio_img)

    img_r = img.convert("RGBA").resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    left  = (nuevo_ancho - ancho) // 2
    top   = (nuevo_alto  - alto)  // 2
    return img_r.crop((left, top, left + ancho, top + alto))


# ── Guardado respetando el formato original ────────────────────

def guardar_imagen(img_rgba, ruta: Path):
    """Convierte al modo adecuado y guarda sobreescribiendo el original."""
    from PIL import Image

    ext = ruta.suffix.lower()

    if ext in (".jpg", ".jpeg"):
        final = img_rgba.convert("RGB")
        final.save(ruta, quality=CALIDAD_JPEG, optimize=True)

    elif ext == ".png":
        # Preserva transparencia si la imagen original la tenía
        img_rgba.save(ruta, optimize=True)

    elif ext == ".gif":
        img_rgba.convert("RGB").save(ruta)

    elif ext in (".tiff", ".tif"):
        img_rgba.convert("RGB").save(ruta, compression="lzw")

    elif ext == ".webp":
        img_rgba.save(ruta, quality=CALIDAD_JPEG, method=6)

    elif ext == ".bmp":
        img_rgba.convert("RGB").save(ruta)

    else:
        img_rgba.convert("RGB").save(ruta)


# ── Flujo principal ────────────────────────────────────────────

def main():
    # Ruta base = carpeta donde está este .py
    base        = Path(__file__).parent.resolve()
    carpeta_img = base / "imagenes"
    ruta_log    = base / "log.txt"

    lineas = iniciar_log(ruta_log)

    # ── Verificar Pillow ───────────────────────────────────────
    try:
        from PIL import Image
    except ImportError:
        lineas.append(
            "ERROR CRÍTICO: Pillow no está instalado.\n"
            "Abrí una terminal y ejecutá:  pip install Pillow\n"
            "Luego volvé a ejecutar este script."
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    # ── Verificar carpeta "imagenes" ───────────────────────────
    if not carpeta_img.exists():
        carpeta_img.mkdir()
        lineas.append(
            "Se creó la carpeta 'imagenes' porque no existía.\n"
            "Copiá ahí las imágenes y volvé a ejecutar el script."
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    # ── Recopilar archivos válidos ─────────────────────────────
    archivos = sorted(
        f for f in carpeta_img.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONES_VALIDAS
    )

    if not archivos:
        lineas.append(
            "No se encontraron imágenes en la carpeta 'imagenes'.\n"
            f"Extensiones soportadas: {', '.join(sorted(EXTENSIONES_VALIDAS))}"
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    lineas.append(f"Imágenes encontradas: {len(archivos)}\n")

    ok = 0
    omitidas = 0
    errores  = 0

    for archivo in archivos:
        try:
            img = Image.open(archivo)
            w_orig, h_orig = img.size

            # ── ¿Ya tiene la resolución correcta? ─────────────
            if w_orig == ANCHO_OBJETIVO and h_orig == ALTO_OBJETIVO:
                lineas.append(f"[OMITIDA - ya es {ANCHO_OBJETIVO}x{ALTO_OBJETIVO}]  {archivo.name}")
                omitidas += 1
                continue

            # ── ¿Más pequeña que el objetivo y no se permite? ─
            if not PERMITIR_ESCALADO_HACIA_ARRIBA:
                if w_orig < ANCHO_OBJETIVO and h_orig < ALTO_OBJETIVO:
                    lineas.append(
                        f"[OMITIDA - imagen más pequeña que el objetivo "
                        f"({w_orig}x{h_orig}) y PERMITIR_ESCALADO_HACIA_ARRIBA=False]  "
                        f"{archivo.name}"
                    )
                    omitidas += 1
                    continue

            # ── Convertir a RGBA para procesamiento unificado ──
            img_rgba = img.convert("RGBA")

            if METODO == "fit":
                resultado = aplicar_fit(img_rgba, ANCHO_OBJETIVO, ALTO_OBJETIVO, COLOR_RELLENO)
            else:
                resultado = aplicar_fill(img_rgba, ANCHO_OBJETIVO, ALTO_OBJETIVO)

            guardar_imagen(resultado, archivo)

            lineas.append(
                f"[OK  {w_orig:5d}x{h_orig:<5d} → {ANCHO_OBJETIVO}x{ALTO_OBJETIVO}]  {archivo.name}"
            )
            ok += 1

        except Exception as e:
            lineas.append(f"[ERROR]  {archivo.name}  →  {e}")
            errores += 1

    # ── Resumen final ──────────────────────────────────────────
    lineas.append(
        f"\n{'─'*55}\n"
        f"Procesadas : {ok}\n"
        f"Omitidas   : {omitidas}\n"
        f"Errores    : {errores}\n"
        f"{'─'*55}\n"
        f"Log guardado en: {ruta_log}"
    )

    guardar_log(lineas, ruta_log)
    print("\n".join(lineas))   # visible si se ejecuta desde terminal
    _pausa()


def _pausa():
    """Evita que la ventana se cierre instantáneamente al hacer doble clic."""
    try:
        input("\nListo. Revisá el archivo log.txt para ver los detalles.\nPresioná Enter para cerrar...")
    except EOFError:
        pass   # ejecutado sin consola interactiva, no pasa nada


if __name__ == "__main__":
    main()

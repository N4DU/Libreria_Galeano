# =============================================================
#  convertir_a_webp.py  —  Conversor de imágenes a WebP
#  Coloca las imágenes en la carpeta "imagenes" que está junto
#  a este archivo y hacé doble clic para ejecutar.
#  Busca imágenes en subcarpetas sin importar la profundidad.
#  Los resultados se guardan junto a los originales y se genera
#  un "log.txt".
# =============================================================

# ──────────────────────────────────────────────────────────────
#  CONFIGURACIÓN  ← editá estos valores antes de ejecutar
# ──────────────────────────────────────────────────────────────
CALIDAD_WEBP = 90
# Calidad de compresión WebP  (1 = mínima … 95 = máxima recomendada)
# 80-90 es el rango ideal para web: muy buena calidad, tamaño reducido

ELIMINAR_ORIGINALES = True
# True  → borra el archivo original después de convertir a WebP
#          El .webp queda en la misma carpeta que el original
# False → conserva el original junto al nuevo .webp

OMITIR_SI_YA_EXISTE = True
# True  → si ya existe un .webp con el mismo nombre en la misma
#          carpeta, lo saltea (útil para reanudar conversiones)
# False → sobreescribe el .webp existente
# ──────────────────────────────────────────────────────────────

from pathlib import Path
from datetime import datetime

# ── Extensiones soportadas ─────────────────────────────────────
# Formatos comunes de imagen
EXTENSIONES_VALIDAS = {
    # JPEG y variantes
    ".jpg", ".jpeg", ".jpe", ".jfif",
    # PNG y variantes animadas
    ".png", ".apng",
    # Formatos modernos
    ".avif", ".avifs",  # AV1 Image Format — requiere Pillow 9.1.0+ con libavif
    # HEIC/HEIF — requiere: pip install pillow-heif  (ver advertencia al ejecutar)
    ".heic", ".heif",
    # Otros formatos web y de diseño
    ".webp",            # Se reconvierte (por si cambió la calidad objetivo)
    ".gif",             # Solo primer fotograma
    ".bmp", ".dib",     # Bitmap de Windows
    ".tiff", ".tif",    # TIFF
    ".tga",             # Targa (común en videojuegos)
    ".dds",             # DirectDraw Surface (texturas de juegos)
    ".psd",             # Photoshop (lee solo la capa aplanada)
    ".ico", ".icns",    # Íconos (Windows / macOS)
    ".pcx",             # PC Paintbrush (formato antiguo)
    ".qoi",             # Quite OK Image (formato moderno lossless)
    # Familia PPM (imágenes sin compresión)
    ".ppm", ".pbm", ".pgm", ".pnm", ".pfm",
    # Formatos SGI
    ".sgi", ".rgb", ".rgba", ".bw",
    # Otros
    ".xpm",             # X11 Pixmap
}


# ── Utilidades de log ──────────────────────────────────────────

def iniciar_log() -> list:
    encabezado = (
        f"ConvertirAWebP — log de ejecución\n"
        f"Fecha    : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}\n"
        f"Calidad  : {CALIDAD_WEBP}  |  "
        f"Eliminar originales: {ELIMINAR_ORIGINALES}  |  "
        f"Omitir existentes: {OMITIR_SI_YA_EXISTE}\n"
        f"{'─'*55}\n"
    )
    return [encabezado]


def guardar_log(lineas: list, ruta: Path):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


# ── Soporte HEIC/HEIF opcional ─────────────────────────────────

def intentar_cargar_heif() -> bool:
    """
    Intenta registrar el plugin pillow-heif.
    Devuelve True si está disponible, False si no.
    HEIC/HEIF requiere: pip install pillow-heif
    """
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        return True
    except ImportError:
        return False


# ── Soporte AVIF opcional ──────────────────────────────────────

def verificar_soporte_avif() -> bool:
    """
    Verifica si Pillow tiene soporte AVIF compilado.
    Requiere Pillow 9.1.0+ y que la librería libavif esté incluida
    en el build (en Windows puede no estarlo en versiones viejas).
    Devuelve True si está disponible, False si no.
    """
    try:
        from PIL import features
        return features.check("avif")
    except Exception:
        return False


# ── Conversión ─────────────────────────────────────────────────

def abrir_imagen(ruta: Path):
    """
    Abre una imagen con manejo especial según el formato.
    Fuerza la carga completa para detectar archivos corruptos/truncados
    antes de intentar procesar.
    """
    from PIL import Image

    ext = ruta.suffix.lower()

    img = Image.open(ruta)

    # Nota sobre ICO/ICNS: Pillow ya selecciona automáticamente la
    # resolución más grande disponible al abrir. No hace falta hacer
    # nada extra; asignar img.size no funciona (es de solo lectura).

    # Advertencia informativa para formatos con limitaciones conocidas
    # (se agrega a notas, no acá — ver convertir_a_webp)

    # Forzar lectura completa — detecta archivos truncados o corruptos
    # Image.open() es lazy: sin img.load(), un archivo dañado puede pasar
    # el open() sin error y fallar más tarde con un mensaje confuso
    img.load()

    return img


def convertir_a_webp(ruta_origen: Path) -> tuple[Path, list[str]]:
    """
    Convierte una imagen a WebP.
    Devuelve (ruta_destino, lista_de_notas).

    Usa escritura atómica (.tmp → rename) para evitar dejar WebP
    corruptos si el proceso se interrumpe a mitad.
    """
    from PIL import Image

    ext        = ruta_origen.suffix.lower()
    notas      = []
    ruta_destino = ruta_origen.with_suffix(".webp")
    ruta_tmp     = ruta_origen.with_suffix(".webp.tmp")

    # Advertencias informativas para formatos con limitaciones conocidas
    if ext == ".apng":
        notas.append("nota: APNG animado → se convirtió solo el primer fotograma")
    if ext == ".gif":
        notas.append("nota: GIF animado → se convirtió solo el primer fotograma")
    if ext == ".psd":
        notas.append("nota: PSD → se leyó solo la capa aplanada (requiere 'Maximize Compatibility' en Photoshop)")
    if ext in (".ico", ".icns"):
        notas.append("nota: ícono multi-resolución → Pillow seleccionó la resolución más grande disponible")

    img = abrir_imagen(ruta_origen)

    try:
        if img.mode in ("RGBA", "LA", "P"):
            img_final = img.convert("RGBA")
            img_final.save(ruta_tmp, format="WEBP", quality=CALIDAD_WEBP, method=6)
        else:
            img_final = img.convert("RGB")
            img_final.save(ruta_tmp, format="WEBP", quality=CALIDAD_WEBP, method=6)

        # Verificar que el archivo resultante no esté vacío
        # (ocurre si el disco se llena durante el guardado)
        if ruta_tmp.stat().st_size == 0:
            ruta_tmp.unlink(missing_ok=True)
            raise RuntimeError("El archivo WebP resultante está vacío (¿disco lleno?)")

        # Renombrar atómicamente: si ya existía un .webp, lo reemplaza
        ruta_tmp.replace(ruta_destino)

    except Exception:
        ruta_tmp.unlink(missing_ok=True)  # Limpiar .tmp si algo salió mal
        raise

    return ruta_destino, notas


# ── Flujo principal ────────────────────────────────────────────

def main():
    base        = Path(__file__).parent.resolve()
    carpeta_img = base / "imagenes"
    ruta_log    = base / "log.txt"

    lineas = iniciar_log()

    # ── Verificar Pillow ───────────────────────────────────────
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        lineas.append(
            "ERROR CRÍTICO: Pillow no está instalado.\n"
            "Abrí una terminal y ejecutá:  pip install Pillow\n"
            "Luego volvé a ejecutar este script."
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    # ── Soporte HEIC/HEIF (plugin opcional) ───────────────────
    heif_disponible = intentar_cargar_heif()
    extensiones_activas = set(EXTENSIONES_VALIDAS)

    if not heif_disponible:
        extensiones_activas -= {".heic", ".heif"}
        lineas.append(
            "AVISO: plugin 'pillow-heif' no encontrado.\n"
            "Los archivos .heic y .heif serán ignorados.\n"
            "Para activar soporte HEIC/HEIF ejecutá:  pip install pillow-heif\n"
        )
    else:
        lineas.append("Soporte HEIC/HEIF activo (pillow-heif detectado).\n")

    # ── Soporte AVIF (depende del build de Pillow) ─────────────
    # AVIF requiere que Pillow esté compilado con libavif.
    # En Windows puede no estar disponible en versiones viejas.
    # Si falta: pip install --upgrade Pillow  (requiere Pillow 9.1.0+)
    avif_disponible = verificar_soporte_avif()

    if not avif_disponible:
        extensiones_activas -= {".avif", ".avifs"}
        lineas.append(
            "AVISO: soporte AVIF no disponible en esta instalación de Pillow.\n"
            "Los archivos .avif y .avifs serán ignorados.\n"
            "Para activarlo: actualizá Pillow con  pip install --upgrade Pillow\n"
            "(requiere Pillow 9.1.0+ compilado con soporte libavif)\n"
        )
    else:
        lineas.append("Soporte AVIF activo.\n")

    # ── Verificar carpeta "imagenes" ───────────────────────────
    if not carpeta_img.exists():
        carpeta_img.mkdir()
        lineas.append(
            "Se creó la carpeta 'imagenes' porque no existía.\n"
            "Copiá ahí las imágenes (en subcarpetas si querés) y volvé a ejecutar."
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    # ── Recopilar archivos válidos (recursivo) ─────────────────
    # rglob("*") devuelve archivos Y directorios; filtramos solo archivos
    archivos = sorted(
        f for f in carpeta_img.rglob("*")
        if f.is_file() and f.suffix.lower() in extensiones_activas
    )

    if not archivos:
        lineas.append(
            "No se encontraron imágenes para convertir en 'imagenes/' ni en sus subcarpetas.\n"
            f"Extensiones activas: {', '.join(sorted(extensiones_activas))}"
        )
        guardar_log(lineas, ruta_log)
        _pausa()
        return

    lineas.append(f"Imágenes encontradas: {len(archivos)}\n")

    ok       = 0
    omitidas = 0
    errores  = 0

    for archivo in archivos:
        rel       = archivo.relative_to(base)
        ruta_webp = archivo.with_suffix(".webp")

        try:
            # ── ¿Ya existe el .webp y se configuró omitir? ─────
            if OMITIR_SI_YA_EXISTE and ruta_webp.exists():
                # No omitir si el archivo origen ya ES un .webp
                # (en ese caso querría reconvertirlo con la nueva calidad)
                if archivo.suffix.lower() != ".webp":
                    lineas.append(f"[OMITIDA - ya existe]  {rel.with_suffix('.webp')}")
                    omitidas += 1
                    continue

            # ── Convertir ──────────────────────────────────────
            tam_orig = archivo.stat().st_size
            _, notas = convertir_a_webp(archivo)
            tam_webp = ruta_webp.stat().st_size

            reduccion = (1 - tam_webp / tam_orig) * 100 if tam_orig > 0 else 0
            signo     = "-" if reduccion >= 0 else "+"

            entrada_log = f"[OK  {signo}{abs(reduccion):4.1f}%]  {rel}  →  .webp"
            for nota in notas:
                entrada_log += f"\n           ↳ {nota}"
            lineas.append(entrada_log)

            # ── Eliminar original si se configuró así ──────────
            # Nunca borrar si el original ya era .webp (sería el mismo archivo)
            if ELIMINAR_ORIGINALES and archivo.suffix.lower() != ".webp":
                archivo.unlink()

            ok += 1

        except Exception as e:
            lineas.append(f"[ERROR]  {rel}  →  {e}")
            errores += 1

    # ── Resumen final ──────────────────────────────────────────
    lineas.append(
        f"\n{'─'*55}\n"
        f"Convertidas: {ok}\n"
        f"Omitidas   : {omitidas}\n"
        f"Errores    : {errores}\n"
        f"{'─'*55}\n"
        f"Log guardado en: {ruta_log}"
    )

    guardar_log(lineas, ruta_log)
    print("\n".join(lineas))
    _pausa()


def _pausa():
    """Evita que la ventana se cierre instantáneamente al hacer doble clic."""
    try:
        input("\nListo. Revisá el archivo log.txt para ver los detalles.\nPresioná Enter para cerrar...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
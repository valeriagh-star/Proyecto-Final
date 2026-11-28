"""Interfaz de línea de comandos (CLI) del trazador de rayos.

Este archivo constituye el punto de entrada ejecutable del proyecto. Sus
responsabilidades son:
1. Analizar y validar los argumentos recibidos desde la terminal (`escena`,
   `salida` y la bandera opcional `--trabajadores`).
2. Cargar y validar la estructura del archivo JSON mediante `cargar_escena`,
   capturando errores de formato o de dominio (`SceneError`) para informar
   al usuario sin mostrar trazas internas innecesarias.
3. Invocar el motor de renderizado con el nivel de paralelismo solicitado
   y capturar posibles errores de escritura o validación al generar la imagen.
"""

import argparse
import sys
from typing import Optional, Sequence

from src.scene import SceneError, cargar_escena


def _entero_positivo(valor: str) -> int:
    """Valida que un argumento de línea de comandos sea un número entero positivo (>= 1).

    Args:
        valor (str): Cadena textual recibida en el argumento `--trabajadores`.

    Returns:
        int: Número entero validado estrictamente mayor o igual a `1`.

    Raises:
        argparse.ArgumentTypeError: Si `valor` no representa un entero o es `< 1`.
    """
    try:
        numero = int(valor)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"El número de trabajadores debe ser un entero positivo, se recibió '{valor}'."
        ) from exc
    if numero < 1:
        raise argparse.ArgumentTypeError(
            "El número de trabajadores debe ser mayor o igual a 1."
        )
    return numero


def construir_parser() -> argparse.ArgumentParser:
    """Construye y configura el analizador de argumentos de línea de comandos.

    Returns:
        argparse.ArgumentParser: Analizador configurado con los parámetros
        posicionales `escena` y `salida`, y el parámetro opcional `--trabajadores`.
    """
    parser = argparse.ArgumentParser(
        prog="raytracer.py",
        description="Ray tracer en Python 3 estándar que genera imágenes PPM a partir de una escena JSON.",
    )
    parser.add_argument(
        "escena",
        help="Ruta al archivo JSON con la descripción de la escena.",
    )
    parser.add_argument(
        "salida",
        help="Ruta del archivo de imagen de salida en formato PPM (ej. salida.ppm).",
    )
    parser.add_argument(
        "--trabajadores",
        type=_entero_positivo,
        default=1,
        help="Número de procesos trabajadores a usar (por defecto: 1, modo secuencial).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ejecuta el flujo completo de lectura de argumentos, carga y renderizado.

    Args:
        argv (Optional[Sequence[str]], optional): Secuencia de argumentos CLI.
            Si es `None`, `argparse` lee automáticamente `sys.argv[1:]`.

    Returns:
        int: Código de estado POSIX (`0` si la ejecución fue exitosa, `1` si
        ocurrió un error controlado al cargar la escena o escribir la imagen).
    """
    parser = construir_parser()
    args = parser.parse_args(argv)

    try:
        escena = cargar_escena(args.escena)
    except SceneError as exc:
        print(f"Error al cargar la escena: {exc}", file=sys.stderr)
        return 1

    print(
        f"Escena cargada correctamente: {escena.imagen.ancho}x{escena.imagen.alto}, "
        f"{len(escena.objetos)} objeto(s), {len(escena.luces)} luz(ces), "
        f"{args.trabajadores} trabajador(es)."
    )
    print(f"Archivo de salida configurado: {args.salida}")

    # Importación diferida para evitar sobrecarga si el archivo JSON falló al validarse
    from src.renderer import renderizar

    try:
        renderizar(escena, args.salida, trabajadores=args.trabajadores)
    except (OSError, ValueError) as exc:
        print(f"Error al generar la imagen: {exc}", file=sys.stderr)
        return 1

    print(f"Imagen generada correctamente: {args.salida}")
    return 0


# Protección estándar de punto de entrada: indispensable cuando se usa `multiprocessing`
if __name__ == "__main__":
    sys.exit(main())
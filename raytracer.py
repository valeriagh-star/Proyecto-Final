
import argparse
import sys
from typing import Optional, Sequence

from src.scene import SceneError, cargar_escena
from src.renderer import renderizar


def _entero_positivo(valor: str) -> int:
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
    parser = argparse.ArgumentParser(
        prog="raytracer.py",
        description=(
            "Ray tracer en Python 3 estándar que genera imágenes "
            "PPM a partir de una escena JSON."
        ),
    )

    parser.add_argument(
        "escena",
        help="Ruta al archivo JSON con la descripción de la escena.",
    )

    parser.add_argument(
        "salida",
        help="Ruta del archivo de imagen de salida en formato PPM.",
    )

    parser.add_argument(
        "--trabajadores",
        type=_entero_positivo,
        default=1,
        help=(
            "Número de procesos trabajadores a usar "
            "(por defecto: 1, modo secuencial)."
        ),
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    # Cargar y validar la escena JSON.
    try:
        escena = cargar_escena(args.escena)

    except SceneError as exc:
        print(
            f"Error al cargar la escena: {exc}",
            file=sys.stderr
        )
        return 1

    print(
        f"Escena cargada correctamente: "
        f"{escena.imagen.ancho}x{escena.imagen.alto}, "
        f"{len(escena.objetos)} objeto(s), "
        f"{len(escena.luces)} luz(ces), "
        f"{args.trabajadores} trabajador(es)."
    )

    # Generar la imagen utilizando el renderer secuencial.
    try:
        renderizar(escena, args.salida)

    except (OSError, ValueError) as exc:
        print(
            f"Error al generar la imagen: {exc}",
            file=sys.stderr
        )
        return 1

    print(f"Imagen generada correctamente: {args.salida}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

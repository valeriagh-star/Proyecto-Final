"""Interfaz de línea de comandos (CLI) del trazador de rayos.

¿Qué es este módulo?
Es el punto de entrada ejecutable del programa desde la terminal.

¿En qué se usa?
Permite al usuario ejecutar comandos como:
`python3 raytracer.py scenes/escena1_basica.json salida.ppm --trabajadores 4`

¿Por qué está organizado en funciones (`_entero_positivo`, `construir_parser`, `main`)?
Separar el parser y la función `main(argv)` del bloque `if __name__ == "__main__":`
permite que `tests/test_scene.py` pruebe la CLI directamente llamando a `main([...])`
en memoria sin tener que abrir subprocesos externos.
"""

import argparse
import sys
from typing import Optional, Sequence

from src.scene import SceneError, cargar_escena


def _entero_positivo(valor: str) -> int:
    """Validador de tipo para `argparse` que exige un número entero >= 1.

    ¿Para qué se usa?
    Valida el valor pasado a `--trabajadores` antes de iniciar el programa.

    ¿Por qué se creó en lugar de usar `type=int`?
    `type=int` aceptaría `0` o `-3` procesos trabajadores. Este validador
    lanza `argparse.ArgumentTypeError`, haciendo que `argparse` detenga la
    ejecución y muestre un mensaje de error claro al usuario.
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
    """Crea y configura el analizador de argumentos de la terminal (`argparse`).

    Define dos argumentos posicionales obligatorios (`escena` y `salida`) y una
    bandera opcional (`--trabajadores`, por defecto `1`).
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
    """Coordina la lectura de argumentos, validación de escena y renderizado.

    ¿Por qué retorna `0` o `1`?
    En sistemas Unix/Linux (como Fedora), los programas de terminal devuelven
    `0` cuando terminan correctamente y un código distinto de cero (`1`) cuando
    ocurre un error controlado (como un JSON mal formado o falta de permisos de
    escritura), evitando mostrar trazas de excepción crudas al usuario final.
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

    # Importación diferida: evita cargar el motor de renderizado y `multiprocessing`
    # si la escena JSON falló al validarse en el paso anterior.
    from src.renderer import renderizar

    try:
        renderizar(escena, args.salida, trabajadores=args.trabajadores)
    except (OSError, ValueError) as exc:
        print(f"Error al generar la imagen: {exc}", file=sys.stderr)
        return 1

    print(f"Imagen generada correctamente: {args.salida}")
    return 0


# Protección de punto de entrada: en Python es obligatoria al usar `multiprocessing`
# para evitar que los procesos hijos vuelvan a ejecutar `main()` al importarse.
if __name__ == "__main__":
    sys.exit(main())
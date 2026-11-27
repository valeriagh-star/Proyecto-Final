"""Suite de pruebas unitarias para el renderizado paralelo (`src/renderer.py`).

Valida tres propiedades fundamentales del sistema multiproceso:
1. **Determinismo y equivalencia:** El resultado numérico generado con 2 y 4
   procesos trabajadores debe ser bit a bit idéntico al modo secuencial (1 trabajador).
2. **Integración completa en disco:** La función `renderizar` con múltiples
   trabajadores debe producir un archivo PPM válido con cabecera `P3` y dimensiones
   exactas.
3. **Programación defensiva:** Solicitar un número inválido de trabajadores (`<= 0`)
   debe lanzar una excepción `ValueError` controlada.
"""

import pytest

from src.renderer import renderizar, renderizar_escena
from src.scene import (
    ConfigCamara,
    ConfigImagen,
    DatosEsfera,
    DatosPlano,
    Escena,
    Luz,
)
from src.vector import Vector3D


def _escena_prueba() -> Escena:
    """Construye una escena sintética ligera de 40x25 píxeles para pruebas rápidas.

    ¿Por qué se usa una resolución de 40x25 en lugar de 400x225?
    Permite ejercitar toda la tubería matemática (cámara, esfera, plano, luz,
    sombras y creación de `multiprocessing.Pool`) en milisegundos, manteniendo
    la suite de `pytest` ágil sin sacrificar cobertura funcional.

    Returns:
        Escena: Escena de prueba con una esfera roja, un plano de suelo gris,
        iluminación ambiental y una fuente de luz puntual.
    """
    return Escena(
        imagen=ConfigImagen(ancho=40, alto=25),
        camara=ConfigCamara(
            posicion=Vector3D(0, 1, 3),
            mira_a=Vector3D(0, 0, -3),
            fov=60.0,
        ),
        fondo=Vector3D(0.6, 0.8, 1.0),
        luz_ambiental=0.1,
        luces=[Luz(posicion=Vector3D(5, 5, 0), intensidad=1.0)],
        objetos=[
            DatosEsfera(
                tipo="esfera",
                centro=Vector3D(0, 0, -3),
                radio=1.0,
                color=Vector3D(0.9, 0.3, 0.2),
            ),
            DatosPlano(
                tipo="plano",
                punto=Vector3D(0, -1, 0),
                normal=Vector3D(0, 1, 0),
                color=Vector3D(0.8, 0.8, 0.8),
            ),
        ],
    )


def test_render_paralelo_igual_a_secuencial() -> None:
    """Verifica que el renderizado con 1, 2 y 4 trabajadores produzca matrices idénticas.

    Comprueba tanto las dimensiones de salida (`25` filas x `40` columnas) como
    la igualdad exacta de cada vector RGB, asegurando que `Pool.map` no desordena
    filas ni introduce diferencias numéricas.
    """
    escena = _escena_prueba()
    img_1 = renderizar_escena(escena, trabajadores=1)
    img_2 = renderizar_escena(escena, trabajadores=2)
    img_4 = renderizar_escena(escena, trabajadores=4)

    assert len(img_1) == 25
    assert len(img_1[0]) == 40
    assert img_1 == img_2
    assert img_1 == img_4


def test_renderizar_archivo_ppm(tmp_path) -> None:
    """Comprueba que `renderizar` genere un archivo PPM válido en modo paralelo.

    Utiliza el fixture `tmp_path` de `pytest` para crear un directorio temporal
    aislado, evitando dejar archivos residuales en el repositorio.
    """
    escena = _escena_prueba()
    salida = tmp_path / "test_paralelo.ppm"
    renderizar(escena, str(salida), trabajadores=2)

    assert salida.exists()
    lineas = salida.read_text(encoding="utf-8").splitlines()
    # Verificamos el número mágico P3 y las dimensiones (ancho alto) en la cabecera
    assert lineas[0] == "P3"
    assert lineas[1] == "40 25"


def test_trabajadores_invalidos() -> None:
    """Asegura que `renderizar_escena` rechace `trabajadores < 1` con `ValueError`."""
    escena = _escena_prueba()
    with pytest.raises(ValueError):
        renderizar_escena(escena, trabajadores=0)
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


def test_render_paralelo_igual_a_secuencial():
    escena = _escena_prueba()
    img_1 = renderizar_escena(escena, trabajadores=1)
    img_2 = renderizar_escena(escena, trabajadores=2)
    img_4 = renderizar_escena(escena, trabajadores=4)

    assert len(img_1) == 25
    assert len(img_1[0]) == 40
    assert img_1 == img_2
    assert img_1 == img_4


def test_renderizar_archivo_ppm(tmp_path):
    escena = _escena_prueba()
    salida = tmp_path / "test_paralelo.ppm"
    renderizar(escena, str(salida), trabajadores=2)

    assert salida.exists()
    lineas = salida.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "P3"
    assert lineas[1] == "40 25"


def test_trabajadores_invalidos():
    escena = _escena_prueba()
    with pytest.raises(ValueError):
        renderizar_escena(escena, trabajadores=0)
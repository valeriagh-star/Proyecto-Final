
import pytest

from src.camera import Camera
from src.vector import Vector3D
from src.ray import Ray


@pytest.fixture
def camara():
    return Camera(
        posicion=Vector3D(0, 0, 0),
        mira_a=Vector3D(0, 0, -1),
        fov=90,
        ancho=100,
        alto=100
    )


def test_crear_camara(camara):
    assert camara.ancho == 100
    assert camara.alto == 100
    assert camara.fov == 90


def test_direccion_central(camara):
    rayo = camara.generate_ray(49, 49)

    assert isinstance(rayo, Ray)
    assert rayo.origin == Vector3D(0, 0, 0)
    assert rayo.direction.z < 0


def test_rayo_derecha(camara):
    rayo = camara.generate_ray(99, 49)

    assert rayo.direction.x > 0


def test_rayo_izquierda(camara):
    rayo = camara.generate_ray(0, 49)

    assert rayo.direction.x < 0


def test_rayo_arriba(camara):
    rayo = camara.generate_ray(49, 0)

    assert rayo.direction.y > 0


def test_rayo_abajo(camara):
    rayo = camara.generate_ray(49, 99)

    assert rayo.direction.y < 0


def test_coordenadas_fuera_de_imagen(camara):
    with pytest.raises(ValueError):
        camara.generate_ray(100, 50)


def test_ancho_invalido():
    with pytest.raises(ValueError):
        Camera(Vector3D(0, 0, 0), Vector3D(0, 0, -1), 90, 0, 100)


def test_fov_invalido():
    with pytest.raises(ValueError):
        Camera(Vector3D(0, 0, 0), Vector3D(0, 0, -1), 180, 100, 100)


def test_posicion_y_mira_iguales():
    with pytest.raises(ValueError):
        Camera(Vector3D(0, 0, 0), Vector3D(0, 0, 0), 90, 100, 100)

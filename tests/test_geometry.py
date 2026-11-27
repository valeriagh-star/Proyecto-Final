from src.geometry import Plane, Sphere
from src.ray import Ray
from src.vector import Vector3D


def test_esfera_interseccion_devuelve_t_mas_cercano():
    sphere = Sphere(Vector3D(0, 0, -5), 1)
    ray = Ray(Vector3D(0, 0, 0), Vector3D(0, 0, -1))

    assert sphere.intersect(ray) == 4.0


def test_esfera_sin_interseccion_devuelve_none():
    sphere = Sphere(Vector3D(0, 0, -5), 1)
    ray = Ray(Vector3D(0, 0, 0), Vector3D(0, 1, 0))

    assert sphere.intersect(ray) is None


def test_esfera_desde_dentro_devuelve_interseccion_hacia_adelante():
    sphere = Sphere(Vector3D(0, 0, 0), 2)
    ray = Ray(Vector3D(0, 0, 0), Vector3D(1, 0, 0))

    assert sphere.intersect(ray) == 2.0


def test_normal_de_esfera_es_unitaria_y_apunta_hacia_afuera():
    sphere = Sphere(Vector3D(0, 0, 0), 2)

    assert sphere.normal_at(Vector3D(0, 2, 0)) == Vector3D(0, 1, 0)


def test_plano_interseccion_devuelve_t():
    plane = Plane(Vector3D(0, 0, -2), Vector3D(0, 0, 1))
    ray = Ray(Vector3D(0, 0, 0), Vector3D(0, 0, -1))

    assert plane.intersect(ray) == 2.0


def test_plano_paralelo_no_tiene_interseccion():
    plane = Plane(Vector3D(0, 0, -2), Vector3D(0, 0, 1))
    ray = Ray(Vector3D(0, 0, 0), Vector3D(1, 0, 0))

    assert plane.intersect(ray) is None


def test_plano_detras_del_rayo_no_tiene_interseccion():
    plane = Plane(Vector3D(0, 0, 2), Vector3D(0, 0, 1))
    ray = Ray(Vector3D(0, 0, 0), Vector3D(0, 0, -1))

    assert plane.intersect(ray) is None


def test_normal_de_plano_es_constante_y_unitaria():
    plane = Plane(Vector3D(0, 0, -2), Vector3D(0, 0, 3))

    assert plane.normal_at(Vector3D(10, 5, -2)) == Vector3D(0, 0, 1)

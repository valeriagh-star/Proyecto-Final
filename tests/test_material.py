from src.material import Material
from src.vector import Vector3D


def test_color_con_luz_completa():
    material = Material(Vector3D(1, 0, 0), 0.1)

    luces = [(Vector3D(0, 0, 1), 0.5, True)]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(0.6, 0, 0)


def test_color_solo_con_luz_ambiental():
    material = Material(Vector3D(1, 0, 0), 0.1)

    luces = [(Vector3D(0, 0, -1), 0.5, True)]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(0.1, 0, 0)


def test_color_con_luz_perpendicular():
    material = Material(Vector3D(1, 0, 0), 0.1)

    luces = [(Vector3D(1, 0, 0), 0.5, True)]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(0.1, 0, 0)


def test_color_con_varias_luces():
    material = Material(Vector3D(1, 0, 0), 0.1)

    luces = [
        (Vector3D(0, 0, 1), 0.4, True),
        (Vector3D(0, 0, 1), 0.3, True)
    ]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(0.8, 0, 0)


def test_luz_bloqueada_por_sombra():
    material = Material(Vector3D(1, 0, 0), 0.1)

    luces = [(Vector3D(0, 0, 1), 0.8, False)]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(0.1, 0, 0)


def test_color_limitado():
    material = Material(Vector3D(1, 0, 0), 0.2)

    luces = [(Vector3D(0, 0, 1), 2.0, True)]

    resultado = material.calculate_lighting(
        Vector3D(0, 0, 1), luces
    )

    assert resultado == Vector3D(1, 0, 0)

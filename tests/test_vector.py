import math
from src.vector import Vector3D

def test_operaciones_basicas():
    v1 = Vector3D(1, 2, 3)
    v2 = Vector3D(4, 5, 6)
    
    assert v1 + v2 == Vector3D(5, 7, 9)
    assert v2 - v1 == Vector3D(3, 3, 3)
    assert v1 * 2 == Vector3D(2, 4, 6)
    assert 2 * v1 == Vector3D(2, 4, 6)
    assert v2 / 2 == Vector3D(2, 2.5, 3)

def test_producto_punto():
    v1 = Vector3D(1, 2, 3)
    v2 = Vector3D(4, -5, 6)
    assert v1.dot(v2) == 12.0

def test_norma_y_normalizacion():
    v = Vector3D(3, 4, 0)
    assert v.norm() == 5.0
    
    v_unitario = v.normalize()
    assert math.isclose(v_unitario.norm(), 1.0)
    assert v_unitario == Vector3D(0.6, 0.8, 0.0)

def test_clamp():
    col = Vector3D(1.5, -0.2, 0.5)
    assert col.clamp() == Vector3D(1.0, 0.0, 0.5)
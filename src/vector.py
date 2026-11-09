import math

class Vector3D:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"

    # Permite comparar Vector3D(1,0,0) == Vector3D(1,0,0) en pytest
    def __eq__(self, other):
        if not isinstance(other, Vector3D):
            return False
        return (math.isclose(self.x, other.x, abs_tol=1e-6) and
                math.isclose(self.y, other.y, abs_tol=1e-6) and
                math.isclose(self.z, other.z, abs_tol=1e-6))

    # Suma de vectores
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    # Resta de vectores
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    # Multiplicación de un vector por un escalar
    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
        return Vector3D(self.x * scalar.x, self.y * scalar.y, self.z * scalar.z)

    # Permite la multiplicación escalar desde el lado izquierdo
    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    # División de un vector por un escalar y división de un vector por otro vector componente a componente
    def __truediv__(self, scalar):
        if isinstance(scalar, (int, float)):
            return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)
        return Vector3D(self.x / scalar.x, self.y / scalar.y, self.z / scalar.z)

    # Producto punto
    def dot(self, other) -> float:
        """Producto punto N · L"""
        return self.x * other.x + self.y * other.y + self.z * other.z

    # Norma y normalización de vectores
    def norm(self) -> float:
        """Magnitud o norma del vector"""
        return math.sqrt(self.dot(self))

    def normalize(self):
        """Devuelve el vector unitario (longitud 1)"""
        n = self.norm()
        if n == 0:
            return Vector3D(0.0, 0.0, 0.0)
        return self / n

    # Limitar los valores de color al rango [0.0, 1.0]
    def clamp(self, min_val=0.0, max_val=1.0):
        """Limita cada componente al rango [0.0, 1.0]"""
        return Vector3D(
            max(min_val, min(max_val, self.x)),
            max(min_val, min(max_val, self.y)),
            max(min_val, min(max_val, self.z))
        )
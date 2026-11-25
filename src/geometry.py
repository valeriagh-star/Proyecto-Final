import math
from src.vector import Vector3D
from src.ray import Ray

class Sphere:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def intersect(self, ray):
        oc = ray.origin - self.center

        a = ray.direction.dot(ray.direction)
        b = 2.0 * oc.dot(ray.direction)
        c = oc.dot(oc) - self.radius * self.radius

        discriminant = b * b - 4.0 * a * c

        if discriminant < 0:
            return None

        sqrt_discriminant = math.sqrt(discriminant)
        t1 = (-b - sqrt_discriminant) / (2.0 * a)
        t2 = (-b + sqrt_discriminant) / (2.0 * a)

        positive_roots = [t for t in (t1, t2) if t > 0]

        if not positive_roots:
            return None

        return min(positive_roots)

    def normal_at(self, point):
        return (point - self.center).normalize()

class Plane:
    def __init__(self, point, normal):
        self.point = point
        self.normal = normal.normalize()

    def intersect(self, ray: Ray):
        denominator = ray.direction.dot(self.normal)

        if abs(denominator) < 1e-8: #Comprueba si el denominador es cero o tan pequeño que es mejor tomarlo como cero.
            return None #el rayo es paralelo o casi paralelo al plano.

        t = (self.point - ray.origin).dot(self.normal) / denominator

        if t <= 0: #Descarta el cruce si queda en el origen o detrás de él.
            return None

        return t

    def normal_at(self, point: Vector3D):
        return self.normal
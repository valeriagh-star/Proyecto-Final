import math
from src.vector import Vector3D

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
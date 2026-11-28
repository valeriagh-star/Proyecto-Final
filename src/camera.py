
import math

from src.vector import Vector3D
from src.ray import Ray


class Camera:
    def __init__(self, posicion, mira_a, fov, ancho, alto):
        if ancho <= 0 or alto <= 0:
            raise ValueError("El ancho y el alto deben ser positivos.")

        if fov <= 0 or fov >= 180:
            raise ValueError("El FOV debe estar entre 0 y 180 grados.")

        if posicion == mira_a:
            raise ValueError("La posición y el punto de mira no pueden ser iguales.")

        self.posicion = posicion
        self.mira_a = mira_a
        self.fov = fov
        self.ancho = ancho
        self.alto = alto

        # Calculamos la dirección hacia donde mira la cámara.
        self.forward = (mira_a - posicion).normalize()

        # Vector que representa la dirección vertical del mundo.
        world_up = Vector3D(0, 1, 0)

        # Calculamos la orientación horizontal de la cámara.
        self.right = self._cross(self.forward, world_up).normalize()

        # Si la cámara apunta verticalmente, usamos otro vector de referencia.
        if self.right.norm() == 0:
            world_up = Vector3D(0, 0, 1)
            self.right = self._cross(self.forward, world_up).normalize()

        self.up = self._cross(self.right, self.forward).normalize()

        # Calculamos el tamaño del plano de imagen.
        self.aspect_ratio = ancho / alto
        self.half_width = math.tan(math.radians(fov) / 2)
        self.half_height = self.half_width / self.aspect_ratio

    def _cross(self, a, b):
        """Calcula el producto cruz de dos vectores."""
        return Vector3D(
            a.y * b.z - a.z * b.y,
            a.z * b.x - a.x * b.z,
            a.x * b.y - a.y * b.x
        )

    def generate_ray(self, x, y):
        """Genera un rayo que atraviesa el centro del píxel (x, y)."""
        if not (0 <= x < self.ancho and 0 <= y < self.alto):
            raise ValueError("Las coordenadas del píxel están fuera de la imagen.")

        # Convertimos las coordenadas del píxel a valores entre -1 y 1.
        u = 2 * ((x + 0.5) / self.ancho) - 1
        v = 1 - 2 * ((y + 0.5) / self.alto)

        # Ajustamos las coordenadas al campo de visión.
        direccion = (
            self.forward
            + self.right * (u * self.half_width)
            + self.up * (v * self.half_height)
        ).normalize()

        return Ray(self.posicion, direccion)

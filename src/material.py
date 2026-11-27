from src.vector import Vector3D


class Material:
    """
    Representa el material de un objeto y calcula su iluminación.
    """

    def __init__(self, color, ambient=0.1):
        self.color = color
        self.ambient = ambient

    def calculate_lighting(self, normal, lights):
        """
        Calcula la iluminación ambiental y difusa
        mediante el modelo de Lambert.
        """

        normal = normal.normalize()

        # Iluminación ambiental.
        resultado = self.color * self.ambient

        # Contribución de cada luz.
        for direccion, intensidad, visible in lights:

            # Si la luz está bloqueada, no contribuye.
            if not visible:
                continue

            direccion = direccion.normalize()

            # Producto punto entre la normal y la dirección de luz.
            factor = max(normal.dot(direccion), 0.0)

            # Iluminación difusa.
            resultado += self.color * (intensidad * factor)

        # Limitamos los componentes entre 0 y 1.
        return resultado.clamp()

import math

from src.camera import Camera
from src.geometry import Sphere, Plane
from src.material import Material
from src.ray import Ray
from src.scene import DatosEsfera, DatosPlano
from src.vector import Vector3D

def _construir_objetos(escena):
    """
    Convierte los objetos de la escena en geometrías y les asigna sus materiales.
    """
    objetos = []

    for objeto in escena.objetos:
        if isinstance(objeto, DatosEsfera):
            geometria = Sphere(objeto.centro, objeto.radio)

        elif isinstance(objeto, DatosPlano):
            geometria = Plane(objeto.punto, objeto.normal)

        material = Material(
            objeto.color,
            escena.luz_ambiental
        )

        objetos.append((geometria, material))

    return objetos

def _hay_sombra(punto, normal, direccion_luz, distancia_luz, objetos):
    """
    Comprobar si algún objeto bloquea la luz desde un punto
    """
    epsilon = 1e-6

    desplazamiento = epsilon if normal.dot(direccion_luz) > 0 else -epsilon
    origen = punto + normal * desplazamiento

    rayo_sombra = Ray(origen, direccion_luz)

    for geometria, material in objetos:
        distancia = geometria.intersect(rayo_sombra)

        if distancia is not None and distancia < distancia_luz - epsilon:
            return True
        
    return False

def renderizar(escena, output_path):
    """
    Genera una imagen a partir de una escena y la guarda en formato PPM
    """
    ancho = escena.imagen.ancho
    alto = escena.imagen.alto

    #CAMARA
    camara = Camera(
        escena.camara.posicion,
        escena.camara.mira_a,
        escena.camara.fov,
        ancho,
        alto
    )

    objetos = _construir_objetos(escena)

    pixel_matrix = []

    for y in range(alto):
        fila = []

        for x in range(ancho):
            rayo = camara.generate_ray(x, y)

            distancia_cercana = float("inf")
            objeto_cercano = None
            for geometria, material in objetos:
                distancia = geometria.intersect(rayo)

                if distancia is not None and distancia < distancia_cercana:
                    distancia_cercana = distancia
                    objeto_cercano = (geometria, material)

            if objeto_cercano is None:
                fila.append(escena.fondo)
                continue
            geometria, material = objeto_cercano

            punto = rayo.at(distancia_cercana)
            normal = geometria.normal_at(punto)

            luces = []

            for luz in escena.luces:
                vector_luz = luz.posicion - punto
                distancia_luz = vector_luz.norm()
                direccion_luz = vector_luz.normalize()

                bloqueada = _hay_sombra(
                    punto,
                    normal,
                    direccion_luz,
                    distancia_luz,
                    objetos
                )

                luces.append((
                    direccion_luz,
                    luz.intensidad,
                    not bloqueada
                ))

            color = material.calculate_lighting(normal, luces)
            fila.append(color)

        pixel_matrix.append(fila)

    write_ppm(pixel_matrix, output_path)


def write_ppm(pixel_matrix, output_path):
    """
    Escribe una matriz de colores en un archivo PPM formato P3.
    """

    # Verificamos que la matriz no esté vacía.
    if not pixel_matrix:
        raise ValueError("La matriz de píxeles no puede estar vacía.")

    # Obtenemos las dimensiones de la imagen.
    height = len(pixel_matrix)
    width = len(pixel_matrix[0])

    # Verificamos que todas las filas tengan el mismo ancho.
    if width == 0 or any(len(fila) != width for fila in pixel_matrix):
        raise ValueError("La matriz de píxeles debe ser rectangular y no estar vacía.")

    # Abrimos el archivo para escribir la imagen.
    with open(output_path, "w", encoding="utf-8") as archivo:
        archivo.write("P3\n")
        archivo.write(f"{width} {height}\n")
        archivo.write("255\n")

        # Recorremos cada píxel de la imagen.
        for fila in pixel_matrix:
            for color in fila:
                color = color.clamp()

                rojo = round(color.x * 255)
                verde = round(color.y * 255)
                azul = round(color.z * 255)

                archivo.write(f"{rojo} {verde} {azul}\n")


        


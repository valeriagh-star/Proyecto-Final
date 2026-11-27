import math
from multiprocessing import Pool
from typing import List, Tuple

from src.geometry import Plane, Sphere
from src.material import Material
from src.ray import Ray
from src.scene import DatosEsfera, DatosPlano, Escena
from src.vector import Vector3D


def _construir_objetos(escena: Escena):
    """Convierte los datos de la escena en objetos geométricos y materiales."""
    objetos_render = []
    for obj in escena.objetos:
        material = Material(color=obj.color, ambient=escena.luz_ambiental)
        if isinstance(obj, DatosEsfera):
            geom = Sphere(center=obj.centro, radius=obj.radio)
        elif isinstance(obj, DatosPlano):
            geom = Plane(point=obj.punto, normal=obj.normal)
        else:
            continue
        objetos_render.append((geom, material))
    return objetos_render


def _interseccion_mas_cercana(ray: Ray, objetos_render):
    """Busca el primer objeto con el que choca el rayo."""
    t_min = float("inf")
    impacto = None
    for geom, material in objetos_render:
        t = geom.intersect(ray)
        if t is not None and 1e-4 < t < t_min:
            t_min = t
            impacto = (t, geom, material)
    return impacto


def _trazar_rayo(ray: Ray, escena: Escena, objetos_render) -> Vector3D:
    """Calcula el color de un rayo incluyendo sombras e iluminación de Lambert."""
    impacto = _interseccion_mas_cercana(ray, objetos_render)
    if impacto is None:
        return escena.fondo

    t, geom, material = impacto
    punto = ray.at(t)
    normal = geom.normal_at(punto)
    origen_sombra = punto + normal * 1e-4

    luces_info = []
    for luz in escena.luces:
        vector_luz = luz.posicion - punto
        distancia_luz = vector_luz.norm()
        direccion_luz = vector_luz.normalize()

        # Verificar si algún objeto bloquea la luz (sombras)
        rayo_sombra = Ray(origen_sombra, direccion_luz)
        bloqueo = _interseccion_mas_cercana(rayo_sombra, objetos_render)
        visible = bloqueo is None or bloqueo[0] >= distancia_luz

        luces_info.append((direccion_luz, luz.intensidad, visible))

    return material.calculate_lighting(normal, luces_info)


def _generar_rayo_camara(escena: Escena, x: int, y: int) -> Ray:
    """Genera el rayo desde la cámara hacia el píxel (x, y)."""
    ancho = escena.imagen.ancho
    alto = escena.imagen.alto
    aspect_ratio = ancho / alto
    fov_rad = math.radians(escena.camara.fov)
    escala = math.tan(fov_rad * 0.5)

    forward = (escena.camara.mira_a - escena.camara.posicion).normalize()
    world_up = Vector3D(0.0, 1.0, 0.0)
    right = Vector3D(
        forward.y * world_up.z - forward.z * world_up.y,
        forward.z * world_up.x - forward.x * world_up.z,
        forward.x * world_up.y - forward.y * world_up.x,
    ).normalize()
    up = Vector3D(
        right.y * forward.z - right.z * forward.y,
        right.z * forward.x - right.x * forward.z,
        right.x * forward.y - right.y * forward.x,
    ).normalize()

    ndc_x = (2.0 * (x + 0.5) / ancho - 1.0) * escala
    ndc_y = (1.0 - 2.0 * (y + 0.5) / alto) * (escala / aspect_ratio)

    direccion = (forward + right * ndc_x + up * ndc_y).normalize()
    return Ray(escena.camara.posicion, direccion)


def _renderizar_fila(args: Tuple[int, Escena]) -> List[Vector3D]:
    """Calcula todos los píxeles de una fila y de la imagen."""
    y, escena = args
    objetos_render = _construir_objetos(escena)
    fila = []
    for x in range(escena.imagen.ancho):
        ray = _generar_rayo_camara(escena, x, y)
        color = _trazar_rayo(ray, escena, objetos_render)
        fila.append(color)
    return fila


def renderizar_escena(escena: Escena, trabajadores: int = 1) -> List[List[Vector3D]]:
    """
    Calcula la matriz de píxeles de la escena.
    - Con trabajadores == 1: modo secuencial en un solo proceso.
    - Con trabajadores > 1: reparte las filas entre procesos con multiprocessing.Pool.
    """
    if trabajadores < 1:
        raise ValueError("El número de trabajadores debe ser mayor o igual a 1.")

    tareas = [(y, escena) for y in range(escena.imagen.alto)]

    if trabajadores == 1:
        return [_renderizar_fila(tarea) for tarea in tareas]

    with Pool(processes=trabajadores) as pool:
        return pool.map(_renderizar_fila, tareas)


def renderizar(escena: Escena, output_path: str, trabajadores: int = 1) -> None:
    """Renderiza la escena y guarda el resultado en un archivo PPM."""
    matriz_pixeles = renderizar_escena(escena, trabajadores=trabajadores)
    write_ppm(matriz_pixeles, output_path)


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
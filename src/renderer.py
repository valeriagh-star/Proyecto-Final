"""Módulo principal de renderizado del trazador de rayos (Ray Tracer).

Este módulo orquesta todo el proceso de síntesis de imagen 3D a 2D:
1. Traduce las definiciones declarativas de la escena (leídas desde JSON) en
   primitivas geométricas calculables (`Sphere`, `Plane`) y materiales (`Material`).
2. Utiliza la clase `Camera` (`src.camera`) para proyectar rayos primarios a
   través del centro de cada píxel de la cuadrícula de salida.
3. Resuelve intersecciones rayo-objeto, verifica oclusiones mediante rayos de
   sombra (`_hay_sombra`) y evalúa el modelo de reflexión difusa de Lambert.
4. Paraleliza el cálculo por filas horizontales usando `multiprocessing.Pool`
   para aprovechar múltiples núcleos de CPU sin condiciones de carrera.
5. Serializa la matriz resultante de vectores de color RGB al formato de texto
   plano PPM (P3).
"""

from multiprocessing import Pool
from typing import List, Optional, Tuple

from src.camera import Camera
from src.geometry import Plane, Sphere
from src.material import Material
from src.ray import Ray
from src.scene import DatosEsfera, DatosPlano, Escena
from src.vector import Vector3D


def _construir_objetos(escena: Escena) -> List[Tuple[object, Material]]:
    """Convierte los datos descriptivos de la escena en objetos geométricos y materiales.

    Al invocarse dentro de cada proceso trabajador, cada subproceso construye sus
    propias instancias geométricas de forma independiente y segura (*process-safe*).

    Args:
        escena (Escena): Instancia validada con la configuración global y la
            lista de objetos de la escena.

    Returns:
        List[Tuple[object, Material]]: Lista de pares `(geometria, material)`
        donde `geometria` implementa `.intersect(ray)` y `.normal_at(punto)`.
    """
    objetos = []
    for objeto in escena.objetos:
        if isinstance(objeto, DatosEsfera):
            geometria = Sphere(objeto.centro, objeto.radio)
        elif isinstance(objeto, DatosPlano):
            geometria = Plane(objeto.punto, objeto.normal)
        else:
            continue

        material = Material(objeto.color, escena.luz_ambiental)
        objetos.append((geometria, material))

    return objetos


def _hay_sombra(
    punto: Vector3D,
    normal: Vector3D,
    direccion_luz: Vector3D,
    distancia_luz: float,
    objetos: List[Tuple[object, Material]],
) -> bool:
    """Comprueba si algún objeto bloquea la luz directa hacia un punto de superficie.

    Desplaza ligeramente el origen del rayo de sombra (`epsilon = 1e-6`) en el
    sentido de la normal (o su opuesto si la luz incide por detrás) para evitar
    auto-intersecciones por errores de precisión en punto flotante (*shadow acne*).

    Args:
        punto (Vector3D): Coordenadas 3D del punto de impacto en la superficie.
        normal (Vector3D): Vector normal unitario de la superficie en `punto`.
        direccion_luz (Vector3D): Vector unitario desde `punto` hacia la luz.
        distancia_luz (float): Distancia euclidiana hasta la fuente de luz.
        objetos (List[Tuple[object, Material]]): Lista de `(geometria, material)`.

    Returns:
        bool: `True` si existe un objeto obstruyendo el camino antes de llegar a
        la fuente de luz; `False` si el punto recibe luz directamente.
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


def _interseccion_mas_cercana(
    ray: Ray, objetos_render: List[Tuple[object, Material]]
) -> Optional[Tuple[float, object, Material]]:
    r"""Determina el primer objeto con el que colisiona un rayo en su trayectoria.

    Recorre todos los objetos de la escena y conserva aquel con el parámetro
    escalar `t` positivo más pequeño en la ecuación paramétrica $P(t) = O + t \cdot D$.

    Args:
        ray (Ray): Rayo con origen y vector dirección normalizado.
        objetos_render (List[Tuple[object, Material]]): Lista de pares
            `(geometria, material)` presentes en la escena.

    Returns:
        Optional[Tuple[float, object, Material]]: Tupla `(t, geometria, material)`
        correspondiente al impacto más cercano, o `None` si el rayo no choca con
        ningún objeto.
    """
    t_min = float("inf")
    impacto = None

    for geom, material in objetos_render:
        t = geom.intersect(ray)
        if t is not None and 1e-6 < t < t_min:
            t_min = t
            impacto = (t, geom, material)

    return impacto


def _trazar_rayo(
    ray: Ray, escena: Escena, objetos_render: List[Tuple[object, Material]]
) -> Vector3D:
    """Calcula el color RGB final que percibe un rayo tras interactuar con la escena.

    Args:
        ray (Ray): Rayo primario lanzado desde la cámara.
        escena (Escena): Escena con fuentes de luz y color de fondo.
        objetos_render (List[Tuple[object, Material]]): Geometrías y materiales.

    Returns:
        Vector3D: Vector RGB resultante de la iluminación ambiental y difusa.
    """
    impacto = _interseccion_mas_cercana(ray, objetos_render)
    if impacto is None:
        return escena.fondo

    t, geom, material = impacto
    punto = ray.at(t)
    normal = geom.normal_at(punto)

    luces_info = []
    for luz in escena.luces:
        vector_luz = luz.posicion - punto
        distancia_luz = vector_luz.norm()
        direccion_luz = vector_luz.normalize()

        bloqueada = _hay_sombra(
            punto,
            normal,
            direccion_luz,
            distancia_luz,
            objetos_render,
        )

        luces_info.append((direccion_luz, luz.intensidad, not bloqueada))

    return material.calculate_lighting(normal, luces_info)


def _renderizar_fila(args: Tuple[int, Escena]) -> List[Vector3D]:
    """Calcula secuencialmente todos los píxeles de una única fila horizontal `y`.

    Esta función de nivel superior actúa como unidad de trabajo independiente
    para cada proceso de `multiprocessing.Pool.map`, instanciando la cámara
    (`Camera`) y los objetos de la escena localmente en el subproceso.

    Args:
        args (Tuple[int, Escena]): Par `(y, escena)` con el índice de fila a
            renderizar y la definición completa de la escena.

    Returns:
        List[Vector3D]: Lista ordenada de `ancho` colores RGB para la fila `y`.
    """
    y, escena = args
    ancho = escena.imagen.ancho
    alto = escena.imagen.alto

    camara = Camera(
        escena.camara.posicion,
        escena.camara.mira_a,
        escena.camara.fov,
        ancho,
        alto,
    )
    objetos_render = _construir_objetos(escena)

    fila = []
    for x in range(ancho):
        rayo = camara.generate_ray(x, y)
        color = _trazar_rayo(rayo, escena, objetos_render)
        fila.append(color)

    return fila


def renderizar_escena(escena: Escena, trabajadores: int = 1) -> List[List[Vector3D]]:
    """Genera la matriz bidimensional de píxeles en modo secuencial o paralelo.

    - Con `trabajadores == 1`: ejecuta el renderizado directamente en el proceso
      principal sin sobrecarga de creación de procesos.
    - Con `trabajadores > 1`: reparte las filas entre `trabajadores` procesos
      mediante `multiprocessing.Pool.map`, conservando el orden de las filas.

    Args:
        escena (Escena): Escena validada que se va a renderizar.
        trabajadores (int, optional): Cantidad de procesos trabajadores paralelos.
            Por defecto es `1` (ejecución secuencial).

    Returns:
        List[List[Vector3D]]: Matriz de colores de dimensiones `alto x ancho`.

    Raises:
        ValueError: Si `trabajadores` es menor que `1`.
    """
    if trabajadores < 1:
        raise ValueError("El número de trabajadores debe ser mayor o igual a 1.")

    tareas = [(y, escena) for y in range(escena.imagen.alto)]

    if trabajadores == 1:
        return [_renderizar_fila(tarea) for tarea in tareas]

    with Pool(processes=trabajadores) as pool:
        return pool.map(_renderizar_fila, tareas)


def renderizar(escena: Escena, output_path: str, trabajadores: int = 1) -> None:
    """Genera una imagen a partir de una escena y la guarda en formato PPM.

    Args:
        escena (Escena): Escena a renderizar.
        output_path (str): Ruta de destino donde se guardará la imagen `.ppm`.
        trabajadores (int, optional): Número de procesos paralelos. Por defecto `1`.
    """
    matriz_pixeles = renderizar_escena(escena, trabajadores=trabajadores)
    write_ppm(matriz_pixeles, output_path)


def write_ppm(pixel_matrix: List[List[Vector3D]], output_path: str) -> None:
    """Exporta una matriz de colores RGB a un archivo de imagen PPM en formato P3.

    Args:
        pixel_matrix (List[List[Vector3D]]): Matriz rectangular de vectores RGB.
        output_path (str): Ruta del archivo de salida `.ppm`.

    Raises:
        ValueError: Si la matriz está vacía o no es estrictamente rectangular.
    """
    if not pixel_matrix:
        raise ValueError("La matriz de píxeles no puede estar vacía.")

    height = len(pixel_matrix)
    width = len(pixel_matrix[0])

    if width == 0 or any(len(fila) != width for fila in pixel_matrix):
        raise ValueError("La matriz de píxeles debe ser rectangular y no estar vacía.")

    with open(output_path, "w", encoding="utf-8") as archivo:
        archivo.write("P3\n")
        archivo.write(f"{width} {height}\n")
        archivo.write("255\n")

        for fila in pixel_matrix:
            for color in fila:
                color = color.clamp()

                rojo = round(color.x * 255)
                verde = round(color.y * 255)
                azul = round(color.z * 255)

                archivo.write(f"{rojo} {verde} {azul}\n")
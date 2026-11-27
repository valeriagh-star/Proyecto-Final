"""Módulo principal de renderizado del trazador de rayos (Ray Tracer).

Este módulo orquesta todo el proceso de síntesis de imagen 3D a 2D:
1. Traduce las definiciones declarativas de la escena (leídas desde JSON) en
   primitivas geométricas calculables (`Sphere`, `Plane`) y materiales (`Material`).
2. Proyecta rayos primarios desde la cámara virtual a través de cada píxel de
   la cuadrícula de salida mediante coordenadas normalizadas de dispositivo (NDC).
3. Resuelve intersecciones rayo-objeto, lanza rayos secundarios de sombra hacia
   cada fuente de luz y evalúa el modelo de reflexión difusa de Lambert.
4. Paraleliza el cálculo por filas horizontales usando `multiprocessing.Pool`
   para aprovechar múltiples núcleos de CPU sin condiciones de carrera.
5. Serializa la matriz resultante de vectores de color RGB al formato de texto
   plano PPM (P3).
"""

import math
from multiprocessing import Pool
from typing import List, Optional, Tuple

from src.geometry import Plane, Sphere
from src.material import Material
from src.ray import Ray
from src.scene import DatosEsfera, DatosPlano, Escena
from src.vector import Vector3D


def _construir_objetos(escena: Escena) -> List[Tuple[object, Material]]:
    """Convierte los datos descriptivos de la escena en objetos geométricos y materiales.

    ¿Por qué existe esta separación?
    El módulo `scene.py` almacena estructuras de datos puras (`DatosEsfera`,
    `DatosPlano`) para mantener desacoplada la validación del JSON respecto al
    motor matemático. Esta función instancia los objetos de `geometry.py` y
    `material.py` listos para calcular intersecciones e iluminación.

    Además, al invocarse dentro de `_renderizar_fila`, cada proceso trabajador
    construye sus propias instancias localmente, garantizando seguridad entre
    procesos (*process-safety*) sin compartir estado mutable.

    Args:
        escena (Escena): Instancia validada con la configuración global y la
            lista de objetos de la escena.

    Returns:
        List[Tuple[object, Material]]: Lista de pares `(geometria, material)`
        donde `geometria` implementa `.intersect(ray)` y `.normal_at(punto)`.
    """
    objetos_render = []
    for obj in escena.objetos:
        # Cada objeto combina su color propio (albedo) con la luz ambiental global
        # definida en la escena para que las zonas en sombra no queden en negro puro.
        material = Material(color=obj.color, ambient=escena.luz_ambiental)

        # Despacho por tipo de dato hacia su clase geométrica correspondiente
        if isinstance(obj, DatosEsfera):
            geom = Sphere(center=obj.centro, radius=obj.radio)
        elif isinstance(obj, DatosPlano):
            geom = Plane(point=obj.punto, normal=obj.normal)
        else:
            # Si apareciera un tipo no soportado, se omite de forma segura
            continue

        objetos_render.append((geom, material))
    return objetos_render


def _interseccion_mas_cercana(
    ray: Ray, objetos_render: List[Tuple[object, Material]]
) -> Optional[Tuple[float, object, Material]]:
    """Determina el primer objeto con el que colisiona un rayo en su trayectoria.

    Recorre todos los objetos de la escena y conserva aquel con el parámetro
    escalar `t` positivo más pequeño (es decir, el más cercano al origen del rayo
    en la ecuación paramétrica $P(t) = O + t \cdot D$).

    ¿Por qué se usa `1e-4` como límite inferior (`1e-4 < t`)?
    Por precisión finita de punto flotante (*floating-point acne*), un rayo de
    sombra que nace sobre una superficie podría detectar una falsa intersección
    consigo misma en $t \approx 0$. El umbral `1e-4` (0.0001) descarta esos
    auto-impactos espurios.

    Args:
        ray (Ray): Rayo con origen y vector dirección normalizado.
        objetos_render (List[Tuple[object, Material]]): Lista de pares
            `(geometria, material)` presentes en la escena.

    Returns:
        Optional[Tuple[float, object, Material]]: Tupla `(t, geometria, material)`
        correspondiente al impacto más cercano, o `None` si el rayo no choca con
        ningún objeto (escapa hacia el fondo).
    """
    # Inicializamos la distancia mínima en infinito para que cualquier impacto
    # válido sea estrictamente menor en la primera comparación.
    t_min = float("inf")
    impacto = None

    for geom, material in objetos_render:
        t = geom.intersect(ray)
        # Verificamos que exista intersección (t is not None), que esté delante
        # del origen evitando auto-intersección (t > 1e-4) y más cerca que impactos previos.
        if t is not None and 1e-4 < t < t_min:
            t_min = t
            impacto = (t, geom, material)

    return impacto


def _trazar_rayo(
    ray: Ray, escena: Escena, objetos_render: List[Tuple[object, Material]]
) -> Vector3D:
    """Calcula el color RGB final que percibe un rayo tras interactuar con la escena.

    El algoritmo sigue tres etapas clásicas de Ray Tracing:
    1. **Intersección primaria:** Busca qué superficie ve el rayo. Si no golpea
       nada, retorna el color de fondo (`escena.fondo`).
    2. **Evaluación de sombras (Shadow Rays):** Desde el punto de impacto, lanza
       un rayo hacia cada fuente de luz. Si otro objeto intercepta ese rayo a
       una distancia menor que la distancia a la luz, el punto está en sombra.
    3. **Sombreado de Lambert:** Delega en `material.calculate_lighting` el
       cálculo de la contribución ambiental más la difusión de las luces visibles.

    Args:
        ray (Ray): Rayo primario lanzado desde la cámara.
        escena (Escena): Escena con fuentes de luz y color de fondo.
        objetos_render (List[Tuple[object, Material]]): Geometrías y materiales.

    Returns:
        Vector3D: Vector RGB con componentes en `[0.0, 1.0]` (o superiores antes
        del clamping final si hay múltiples luces intensas).
    """
    impacto = _interseccion_mas_cercana(ray, objetos_render)
    if impacto is None:
        # El rayo no chocó con ningún objeto: devolvemos el color del cielo/fondo
        return escena.fondo

    t, geom, material = impacto
    # Calculamos las coordenadas 3D exactas del punto de impacto: P = O + t*D
    punto = ray.at(t)
    # Obtenemos el vector normal unitario perpendicular a la superficie en ese punto
    normal = geom.normal_at(punto)

    # Desplazamos el origen del rayo de sombra 1e-4 unidades hacia afuera de la
    # superficie (siguiendo la normal) para evitar el efecto "shadow acne"
    # (que la propia superficie bloquee su rayo hacia la luz por redondeo decimal).
    origen_sombra = punto + normal * 1e-4

    luces_info = []
    for luz in escena.luces:
        # Vector que va desde el punto de impacto hacia la posición de la luz
        vector_luz = luz.posicion - punto
        # Distancia euclidiana exacta entre el punto y la fuente de luz
        distancia_luz = vector_luz.norm()
        # Vector unitario en dirección a la luz (necesario para producto punto)
        direccion_luz = vector_luz.normalize()

        # Lanzamos el rayo de sombra para comprobar visibilidad directa
        rayo_sombra = Ray(origen_sombra, direccion_luz)
        bloqueo = _interseccion_mas_cercana(rayo_sombra, objetos_render)

        # La luz es visible si no hubo ningún bloqueo en el camino, o si el objeto
        # bloqueador está más lejos que la propia fuente de luz (bloqueo[0] >= distancia_luz).
        visible = bloqueo is None or bloqueo[0] >= distancia_luz

        luces_info.append((direccion_luz, luz.intensidad, visible))

    return material.calculate_lighting(normal, luces_info)


def _generar_rayo_camara(escena: Escena, x: int, y: int) -> Ray:
    """Construye el rayo primario que sale de la cámara y pasa por el centro del píxel (x, y).

    ¿Cómo funciona la proyección de cámara Pinhole?
    1. Se construye una base ortonormal de 3 ejes locales de la cámara (`forward`,
       `right`, `up`) usando el producto cruz respecto a la vertical del mundo `(0, 1, 0)`.
    2. Se convierte el campo de visión (`fov`, en grados) a radianes y se obtiene
       su semitangente (`tan(fov / 2)`), que determina la apertura del plano de imagen.
    3. Se transforman las coordenadas discretas del píxel `(x, y)` a Coordenadas
       Normalizadas de Dispositivo (NDC) en el rango `[-1, 1]`, sumando `+ 0.5`
       para apuntar exactamente al centro geométrico del píxel y no a su esquina.
    4. Se corrige el eje vertical con `aspect_ratio = ancho / alto` para evitar
       que las esferas se vean estiradas en imágenes rectangulares (ej. 16:9).

    Args:
        escena (Escena): Escena con la resolución de imagen y parámetros de cámara.
        x (int): Índice de columna del píxel (`0 <= x < ancho`).
        y (int): Índice de fila del píxel (`0 <= y < alto`).

    Returns:
        Ray: Rayo con origen en `camara.posicion` y vector dirección unitario.
    """
    ancho = escena.imagen.ancho
    alto = escena.imagen.alto
    aspect_ratio = ancho / alto

    # Convertimos el ángulo FOV a radianes y calculamos el factor de escala del plano de visión
    fov_rad = math.radians(escena.camara.fov)
    escala = math.tan(fov_rad * 0.5)

    # 1. Vector `forward`: dirección unitaria hacia donde apunta la cámara
    forward = (escena.camara.mira_a - escena.camara.posicion).normalize()
    # Vector auxiliar vertical del mundo (eje Y positivo)
    world_up = Vector3D(0.0, 1.0, 0.0)

    # 2. Vector `right`: producto cruz (forward x world_up) para obtener el eje horizontal derecho
    right = Vector3D(
        forward.y * world_up.z - forward.z * world_up.y,
        forward.z * world_up.x - forward.x * world_up.z,
        forward.x * world_up.y - forward.y * world_up.x,
    ).normalize()

    # 3. Vector `up`: producto cruz (right x forward) para garantizar ortogonalidad perfecta
    up = Vector3D(
        right.y * forward.z - right.z * forward.y,
        right.z * forward.x - right.x * forward.z,
        right.x * forward.y - right.y * forward.x,
    ).normalize()

    # 4. Mapeo de píxel (x, y) a coordenadas NDC centradas en (0, 0).
    # En imagen, y=0 es arriba, pero en espacio 3D Y positivo es arriba; por eso (1.0 - ...).
    ndc_x = (2.0 * (x + 0.5) / ancho - 1.0) * escala
    ndc_y = (1.0 - 2.0 * (y + 0.5) / alto) * (escala / aspect_ratio)

    # Combinación lineal de los ejes de la cámara para obtener la dirección final del rayo
    direccion = (forward + right * ndc_x + up * ndc_y).normalize()
    return Ray(escena.camara.posicion, direccion)


def _renderizar_fila(args: Tuple[int, Escena]) -> List[Vector3D]:
    """Calcula secuencialmente todos los píxeles de una única fila horizontal `y`.

    ¿Por qué esta función recibe una sola tupla `args` y es de nivel superior?
    1. `multiprocessing.Pool.map` pasa un único argumento iterable a la función
       trabajadora, por lo que empaquetamos `(y, escena)` en una tupla.
    2. En Python, las funciones ejecutadas por `multiprocessing` deben estar
       definidas al nivel superior del módulo para poder ser serializadas
       mediante `pickle` hacia los procesos hijos.
    3. Granularidad por fila: dividir el trabajo por filas (en lugar de píxel
       por píxel) reduce drásticamente la sobrecarga de comunicación entre
       procesos (IPC) manteniendo un buen balanceo de carga.

    Args:
        args (Tuple[int, Escena]): Par `(y, escena)` con el número de fila a
            renderizar y la definición completa de la escena.

    Returns:
        List[Vector3D]: Lista ordenada de `ancho` colores RGB correspondientes
        a la fila `y`.
    """
    y, escena = args
    # Cada proceso trabajador construye su propia lista de geometrías una sola vez por fila
    objetos_render = _construir_objetos(escena)
    fila = []
    for x in range(escena.imagen.ancho):
        ray = _generar_rayo_camara(escena, x, y)
        color = _trazar_rayo(ray, escena, objetos_render)
        fila.append(color)
    return fila


def renderizar_escena(escena: Escena, trabajadores: int = 1) -> List[List[Vector3D]]:
    """Genera la matriz bidimensional de píxeles en modo secuencial o paralelo.

    ¿Cómo funciona la estrategia de paralelismo?
    Cada píxel de una escena de Ray Tracing es matemáticamente independiente de
    los demás (problema *embarrassingly parallel*).
    - Si `trabajadores == 1`, se evita el costo de crear procesos del sistema
      operativo y se ejecutan las filas directamente en el proceso principal.
    - Si `trabajadores > 1`, se abre un gestor de contexto `with Pool(...)` que
      crea `trabajadores` procesos hijos, distribuye las filas con `pool.map`
      (garantizando que los resultados regresen en el mismo orden `0..alto-1`)
      y cierra limpiamente los procesos al terminar.

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

    # Preparamos la lista de tareas: una tupla (índice_fila, escena) por cada fila y
    tareas = [(y, escena) for y in range(escena.imagen.alto)]

    # Ruta rápida secuencial: evita el overhead de fork/spawn y serialización pickle
    if trabajadores == 1:
        return [_renderizar_fila(tarea) for tarea in tareas]

    # Ruta paralela: reparte las filas entre `trabajadores` procesos independientes
    with Pool(processes=trabajadores) as pool:
        return pool.map(_renderizar_fila, tareas)


def renderizar(escena: Escena, output_path: str, trabajadores: int = 1) -> None:
    """Función fachada que ejecuta el renderizado completo y escribe el archivo PPM.

    Separa el cálculo numérico (`renderizar_escena`, fácil de probar en memoria)
    de la operación de entrada/salida en disco (`write_ppm`).

    Args:
        escena (Escena): Escena a renderizar.
        output_path (str): Ruta de destino donde se guardará la imagen `.ppm`.
        trabajadores (int, optional): Número de procesos paralelos. Por defecto `1`.
    """
    matriz_pixeles = renderizar_escena(escena, trabajadores=trabajadores)
    write_ppm(matriz_pixeles, output_path)


def write_ppm(pixel_matrix: List[List[Vector3D]], output_path: str) -> None:
    """Exporta una matriz de colores RGB a un archivo de imagen PPM en formato P3.

    El formato Netpbm PPM (Portable Pixmap) en variante `P3` almacena la imagen
    en texto plano ASCII con:
    - Línea 1: Número mágico `"P3"` (imagen RGB en texto).
    - Línea 2: Ancho y alto separados por espacio (`width height`).
    - Línea 3: Valor máximo de intensidad por canal (`255`).
    - Líneas siguientes: Tripletes `R G B` enteros en `[0, 255]` por cada píxel.

    Args:
        pixel_matrix (List[List[Vector3D]]): Matriz rectangular de vectores RGB.
        output_path (str): Ruta del archivo de salida `.ppm`.

    Raises:
        ValueError: Si la matriz está vacía o no es estrictamente rectangular.
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

    # Abrimos el archivo en modo escritura UTF-8 para volcar la cabecera y los píxeles.
    with open(output_path, "w", encoding="utf-8") as archivo:
        archivo.write("P3\n")
        archivo.write(f"{width} {height}\n")
        archivo.write("255\n")

        # Recorremos cada píxel de la imagen fila por fila (de arriba hacia abajo).
        for fila in pixel_matrix:
            for color in fila:
                # Limitamos (clamp) los valores al rango [0.0, 1.0] para evitar
                # desbordamientos (>255) cuando varias luces iluminan un mismo punto.
                color = color.clamp()

                # Escalamos del rango normalizado [0.0, 1.0] a enteros de 8 bits [0, 255]
                rojo = round(color.x * 255)
                verde = round(color.y * 255)
                azul = round(color.z * 255)

                archivo.write(f"{rojo} {verde} {azul}\n")
"""Módulo principal de renderizado del trazador de rayos (Ray Tracer).

¿Qué es este módulo?
Es el núcleo de síntesis de imagen del proyecto. Toma una escena 3D descrita
matemáticamente (cámara, luces, esferas y planos) y produce una imagen 2D en
formato PPM.

¿En qué se usa?
Es invocado desde la interfaz de línea de comandos (`raytracer.py`) y desde las
suites de pruebas (`tests/test_renderer.py` y `tests/test_parallelism.py`).

¿Por qué está estructurado así?
Se divide en funciones pequeñas y puras (sin estado global mutable) para lograr
tres objetivos:
1. Claridad matemática: separar intersecciones, sombras, iluminación y escritura
   en disco facilita estudiar y depurar cada etapa de forma aislada.
2. Seguridad en paralelo (*process-safety*): al no compartir variables globales
   modificables, cada proceso hijo de `multiprocessing.Pool` puede calcular su
   fila de píxeles sin bloqueos (*locks*) ni condiciones de carrera.
3. Compatibilidad con pruebas: expone `_hay_sombra`, `renderizar_escena`,
   `renderizar` y `write_ppm` con firmas limpias y predecibles.
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
    """Convierte los datos descriptivos del JSON en geometrías y materiales calculables.

    ¿Qué hace?
    Recorre `escena.objetos` (que contiene estructuras de datos puras como
    `DatosEsfera` y `DatosPlano`) y fabrica por cada uno una tupla
    `(geometria, material)`.

    ¿En qué se usa?
    Se llama al inicio de `_renderizar_fila` para preparar los objetos contra
    los cuales chocarán los rayos de esa fila.

    ¿Por qué se hace así?
    - Desacoplamiento: `scene.py` solo valida el JSON; `geometry.py` y `material.py`
      hacen las matemáticas. Esta función sirve de puente entre ambos mundos.
    - Seguridad entre procesos: al ejecutarse dentro de cada trabajador, cada
      proceso tiene su propia copia local en memoria, evitando problemas de
      serialización o memoria compartida.

    Args:
        escena (Escena): Escena validada con objetos y luz ambiental global.

    Returns:
        List[Tuple[object, Material]]: Lista de pares `(geometria, material)`.
    """
    objetos = []
    for objeto in escena.objetos:
        # Identificamos qué tipo de figura es para instanciar su clase matemática
        if isinstance(objeto, DatosEsfera):
            geometria = Sphere(objeto.centro, objeto.radio)
        elif isinstance(objeto, DatosPlano):
            geometria = Plane(objeto.punto, objeto.normal)
        else:
            # Ignoramos de forma segura cualquier tipo desconocido
            continue

        # Asociamos el color propio del objeto con la luz ambiental de la escena
        # para que las zonas sin luz directa conserven un tono base visible.
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
    """Determina si un punto de una superficie está en sombra respecto a una luz.

    ¿Qué hace?
    Lanza un rayo secundario (*shadow ray*) desde el punto de impacto hacia la
    fuente de luz y verifica si algún objeto se interpone en el camino.

    ¿En qué se usa?
    Se usa dentro de `_trazar_rayo` para decidir si cada luz aporta iluminación
    difusa (`visible = True`) o si está bloqueada (`visible = False`). También
    es probada directamente en `tests/test_renderer.py`.

    ¿Por qué se usa `epsilon = 1e-6` y se desplaza el origen?
    En aritmética de punto flotante, el punto de intersección `punto` nunca cae
    exactamente sobre la superficie matemática debido al redondeo decimal. Si el
    rayo de sombra saliera exactamente desde `punto`, podría volver a chocar con
    el mismo objeto en `distancia ≈ 0`, produciendo manchas negras falsas
    conocidas como *shadow acne*. Desplazar el origen `1e-6` unidades a lo largo
    de la normal evita ese auto-bloqueo.

    Args:
        punto (Vector3D): Coordenadas 3D donde impactó el rayo primario.
        normal (Vector3D): Vector unitario perpendicular a la superficie en `punto`.
        direccion_luz (Vector3D): Vector unitario que apunta de `punto` a la luz.
        distancia_luz (float): Distancia exacta entre `punto` y la luz.
        objetos (List[Tuple[object, Material]]): Objetos presentes en la escena.

    Returns:
        bool: `True` si un objeto bloquea la luz; `False` si el camino está libre.
    """
    epsilon = 1e-6

    # Si la luz está del mismo lado que la normal, desplazamos hacia afuera (+epsilon);
    # si incide por detrás (ej. un plano visto desde atrás), desplazamos hacia adentro (-epsilon).
    desplazamiento = epsilon if normal.dot(direccion_luz) > 0 else -epsilon
    origen = punto + normal * desplazamiento

    rayo_sombra = Ray(origen, direccion_luz)

    for geometria, material in objetos:
        distancia = geometria.intersect(rayo_sombra)

        # Solo hay sombra si el obstáculo está entre el punto y la fuente de luz
        # (si está detrás de la luz, distancia >= distancia_luz, no la tapa).
        if distancia is not None and distancia < distancia_luz - epsilon:
            return True

    return False


def _interseccion_mas_cercana(
    ray: Ray, objetos_render: List[Tuple[object, Material]]
) -> Optional[Tuple[float, object, Material]]:
    r"""Encuentra el primer objeto con el que choca un rayo primario.

    ¿Qué hace?
    Evalúa la ecuación paramétrica del rayo $P(t) = O + t \cdot D$ contra todos
    los objetos de la escena y selecciona el que tenga el menor valor positivo de $t$.

    ¿En qué se usa?
    Se usa en `_trazar_rayo` para saber qué superficie es visible desde la cámara
    en la dirección de un píxel (algoritmo de visibilidad por profundidad / *Z-sorting*
    implícito).

    ¿Por qué se exige `1e-6 < t < t_min`?
    - `t > 1e-6`: asegura que el objeto esté delante de la cámara (los valores
      negativos están detrás) y evita auto-intersecciones numéricas.
    - `t < t_min`: garantiza que si un objeto está delante de otro, el más
      cercano oculte al que está detrás.

    Args:
        ray (Ray): Rayo primario generado por la cámara.
        objetos_render (List[Tuple[object, Material]]): Lista de `(geometria, material)`.

    Returns:
        Optional[Tuple[float, object, Material]]: `(t, geometria, material)` del
        objeto más cercano, o `None` si el rayo no toca ningún objeto.
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
    """Calcula el color RGB final de un único rayo en la escena.

    ¿Qué hace?
    Integra visibilidad, geometría diferencial (normal en el punto), sombras y
    modelo de iluminación de Lambert para obtener el color de un píxel.

    ¿En qué se usa?
    Es el núcleo del bucle interno en `_renderizar_fila`: se ejecuta una vez
    por cada píxel `(x, y)` de la imagen.

    ¿Por qué sigue este orden?
    1. Si no hay impacto (`impacto is None`), no tiene sentido calcular luces ni
       normales: se devuelve `escena.fondo` de inmediato.
    2. Si hay impacto, se calcula `punto = ray.at(t)` y su `normal` una sola vez,
       y luego se reutilizan para evaluar todas las luces de `escena.luces`.

    Args:
        ray (Ray): Rayo que atraviesa el píxel actual.
        escena (Escena): Escena con luces y color de fondo.
        objetos_render (List[Tuple[object, Material]]): Objetos geométricos.

    Returns:
        Vector3D: Color RGB resultante (componentes en `[0.0, 1.0]` o mayores
        antes de aplicar `clamp()` al escribir el archivo).
    """
    impacto = _interseccion_mas_cercana(ray, objetos_render)
    if impacto is None:
        return escena.fondo

    t, geom, material = impacto
    punto = ray.at(t)
    normal = geom.normal_at(punto)

    luces_info = []
    for luz in escena.luces:
        # Vector desde el punto de superficie hacia la posición de la luz
        vector_luz = luz.posicion - punto
        distancia_luz = vector_luz.norm()
        direccion_luz = vector_luz.normalize()

        # Comprobamos si algún objeto proyecta sombra sobre este punto
        bloqueada = _hay_sombra(
            punto,
            normal,
            direccion_luz,
            distancia_luz,
            objetos_render,
        )

        # Guardamos la dirección, intensidad y visibilidad (not bloqueada)
        luces_info.append((direccion_luz, luz.intensidad, not bloqueada))

    return material.calculate_lighting(normal, luces_info)


def _renderizar_fila(args: Tuple[int, Escena]) -> List[Vector3D]:
    """Renderiza todos los píxeles de una fila horizontal `y` de la imagen.

    ¿Qué hace?
    Construye la cámara (`Camera`) y los objetos de la escena, recorre todas
    las columnas `x` de `0` a `ancho - 1` en la fila `y`, genera cada rayo y
    calcula su color.

    ¿En qué se usa?
    Es la función trabajadora (*worker*) que ejecuta cada proceso del pool en
    `renderizar_escena`.

    ¿Por qué recibe una tupla `args` y está al nivel superior del módulo?
    1. `multiprocessing.Pool.map` solo admite funciones de un único argumento,
       por lo que empaquetamos `(y, escena)` en una tupla.
    2. En Python, `multiprocessing` usa `pickle` para enviar funciones a los
       subprocesos; solo las funciones definidas al nivel superior del archivo
       (no funciones anidadas ni `lambda`) son serializables con `pickle`.
    3. Dividir el trabajo por **filas** (en lugar de píxel por píxel) equilibra
       el costo de crear procesos y el tiempo de cálculo por tarea.

    Args:
        args (Tuple[int, Escena]): Tupla `(indice_fila_y, escena)`.

    Returns:
        List[Vector3D]: Lista de `ancho` colores RGB de la fila `y`.
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
    """Calcula la matriz completa de píxeles en modo secuencial o multiproceso.

    ¿Qué hace?
    Crea la lista de tareas `[(0, escena), (1, escena), ..., (alto - 1, escena)]`
    y las procesa usando 1 proceso o un `multiprocessing.Pool` con `N` trabajadores.

    ¿En qué se usa?
    Es llamada por `renderizar()` y directamente por `tests/test_parallelism.py`
    para verificar que 1, 2 y 4 trabajadores producen exactamente la misma matriz.

    ¿Por qué tiene dos caminos (`trabajadores == 1` vs `Pool`)?
    - Cuando `trabajadores == 1`, ejecutar una comprensión de listas evita el
      tiempo de creación de procesos del sistema operativo (*fork/spawn*).
    - Cuando `trabajadores > 1`, `with Pool(processes=trabajadores) as pool:`
      reparte las filas entre los núcleos de CPU disponibles, mantiene el orden
      original de las filas mediante `pool.map` y libera los procesos al salir
      del bloque `with`.

    Args:
        escena (Escena): Escena validada que se desea renderizar.
        trabajadores (int, optional): Número de procesos paralelos. Por defecto `1`.

    Returns:
        List[List[Vector3D]]: Matriz de colores de tamaño `alto x ancho`.

    Raises:
        ValueError: Si `trabajadores < 1`.
    """
    if trabajadores < 1:
        raise ValueError("El número de trabajadores debe ser mayor o igual a 1.")

    tareas = [(y, escena) for y in range(escena.imagen.alto)]

    if trabajadores == 1:
        return [_renderizar_fila(tarea) for tarea in tareas]

    with Pool(processes=trabajadores) as pool:
        return pool.map(_renderizar_fila, tareas)


def renderizar(escena: Escena, output_path: str, trabajadores: int = 1) -> None:
    """Orquesta el renderizado completo de una escena y su guardado en disco.

    ¿Qué hace?
    Obtiene la matriz de píxeles llamando a `renderizar_escena` y la escribe en
    `output_path` llamando a `write_ppm`.

    ¿En qué se usa?
    Es la función principal de alto nivel invocada por `raytracer.py` y las
    pruebas de integración.

    ¿Por qué tiene `trabajadores: int = 1` como valor por defecto?
    Permite que llamadas existentes como `renderizar(escena, archivo)` sigan
    funcionando sin cambios en modo secuencial, mientras que `raytracer.py`
    puede pasar `trabajadores=args.trabajadores` cuando se usa la bandera CLI.

    Args:
        escena (Escena): Escena a renderizar.
        output_path (str): Ruta del archivo `.ppm` de salida.
        trabajadores (int, optional): Número de procesos paralelos. Por defecto `1`.
    """
    matriz_pixeles = renderizar_escena(escena, trabajadores=trabajadores)
    write_ppm(matriz_pixeles, output_path)


def write_ppm(pixel_matrix: List[List[Vector3D]], output_path: str) -> None:
    """Escribe una matriz de colores RGB en un archivo de imagen PPM formato P3.

    ¿Qué hace?
    Valida que la matriz sea rectangular y no esté vacía, escribe la cabecera
    estándar Netpbm (`P3`, `ancho alto`, `255`) y convierte cada color de punto
    flotante `[0.0, 1.0]` a enteros de 8 bits `[0, 255]`.

    ¿En qué se usa?
    Se usa al final de `renderizar()` para producir la imagen final visible en
    cualquier visor de imágenes (GIMP, Feh, Eye of GNOME, etc.).

    ¿Por qué se usa PPM P3 y `color.clamp()`?
    - El formato `P3` es texto plano ASCII, por lo que no requiere librerías
      externas (como Pillow) y cumple con usar solo la biblioteca estándar de Python.
    - `color.clamp()` recorta valores fuera de `[0.0, 1.0]` (por ejemplo, si dos
      luces suman `1.4`), evitando valores mayores a `255` que corromperían el PPM.

    Args:
        pixel_matrix (List[List[Vector3D]]): Matriz rectangular de colores RGB.
        output_path (str): Ruta del archivo de salida `.ppm`.

    Raises:
        ValueError: Si la matriz está vacía o sus filas tienen anchos distintos.
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
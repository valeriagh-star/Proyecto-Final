from dataclasses import dataclass
import json
from pathlib import Path
from typing import List, Union

from src.vector import Vector3D


class SceneError(Exception):
    """Excepción controlada para errores al leer o validar un archivo de escena."""


@dataclass
class ConfigImagen:
    ancho: int
    alto: int


@dataclass
class ConfigCamara:
    posicion: Vector3D
    mira_a: Vector3D
    fov: float


@dataclass
class Luz:
    posicion: Vector3D
    intensidad: float


@dataclass
class DatosEsfera:
    tipo: str
    centro: Vector3D
    radio: float
    color: Vector3D


@dataclass
class DatosPlano:
    tipo: str
    punto: Vector3D
    normal: Vector3D
    color: Vector3D


ObjetoEscena = Union[DatosEsfera, DatosPlano]


@dataclass
class Escena:
    imagen: ConfigImagen
    camara: ConfigCamara
    fondo: Vector3D
    luz_ambiental: float
    luces: List[Luz]
    objetos: List[ObjetoEscena]


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _es_entero_positivo(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def _validar_vector3d(valor, nombre_campo: str) -> Vector3D:
    if not isinstance(valor, list) or len(valor) != 3:
        raise SceneError(
            f"El campo '{nombre_campo}' debe ser una lista de 3 números [x, y, z]."
        )
    if not all(_es_numero(c) for c in valor):
        raise SceneError(f"Todos los componentes de '{nombre_campo}' deben ser números.")
    return Vector3D(valor[0], valor[1], valor[2])


def _validar_color(valor, nombre_campo: str) -> Vector3D:
    color = _validar_vector3d(valor, nombre_campo)
    for comp in (color.x, color.y, color.z):
        if comp < 0.0 or comp > 1.0:
            raise SceneError(
                f"El color en '{nombre_campo}' debe tener valores en el intervalo [0, 1]."
            )
    return color


def _obtener_campo(diccionario: dict, clave: str, contexto: str):
    if clave not in diccionario:
        raise SceneError(f"Falta el campo obligatorio '{clave}' en {contexto}.")
    return diccionario[clave]


def _parsear_imagen(datos: dict) -> ConfigImagen:
    if not isinstance(datos, dict):
        raise SceneError("El campo 'imagen' debe ser un objeto JSON.")
    ancho = _obtener_campo(datos, "ancho", "imagen")
    alto = _obtener_campo(datos, "alto", "imagen")
    if not _es_entero_positivo(ancho) or not _es_entero_positivo(alto):
        raise SceneError("'imagen.ancho' e 'imagen.alto' deben ser enteros positivos.")
    return ConfigImagen(ancho=ancho, alto=alto)


def _parsear_camara(datos: dict) -> ConfigCamara:
    if not isinstance(datos, dict):
        raise SceneError("El campo 'camara' debe ser un objeto JSON.")
    posicion = _validar_vector3d(
        _obtener_campo(datos, "posicion", "camara"), "camara.posicion"
    )
    mira_a = _validar_vector3d(
        _obtener_campo(datos, "mira_a", "camara"), "camara.mira_a"
    )
    fov = _obtener_campo(datos, "fov", "camara")
    if not _es_numero(fov) or fov <= 0 or fov >= 180:
        raise SceneError("'camara.fov' debe ser un número en el rango (0, 180) grados.")
    if posicion == mira_a:
        raise SceneError("'camara.posicion' y 'camara.mira_a' no pueden ser el mismo punto.")
    return ConfigCamara(posicion=posicion, mira_a=mira_a, fov=float(fov))


def _parsear_luces(datos) -> List[Luz]:
    if not isinstance(datos, list) or len(datos) == 0:
        raise SceneError("El campo 'luces' debe ser una lista con al menos una luz puntual.")
    luces = []
    for i, item in enumerate(datos):
        ctx = f"luces[{i}]"
        if not isinstance(item, dict):
            raise SceneError(f"Cada elemento en 'luces' debe ser un objeto JSON ({ctx}).")
        posicion = _validar_vector3d(
            _obtener_campo(item, "posicion", ctx), f"{ctx}.posicion"
        )
        intensidad = _obtener_campo(item, "intensidad", ctx)
        if not _es_numero(intensidad) or intensidad < 0:
            raise SceneError(f"'{ctx}.intensidad' debe ser un número mayor o igual a 0.")
        luces.append(Luz(posicion=posicion, intensidad=float(intensidad)))
    return luces


def _parsear_objetos(datos) -> List[ObjetoEscena]:
    if not isinstance(datos, list):
        raise SceneError("El campo 'objetos' debe ser una lista.")
    objetos: List[ObjetoEscena] = []
    for i, item in enumerate(datos):
        ctx = f"objetos[{i}]"
        if not isinstance(item, dict):
            raise SceneError(f"Cada elemento en 'objetos' debe ser un objeto JSON ({ctx}).")
        tipo = _obtener_campo(item, "tipo", ctx)
        color = _validar_color(_obtener_campo(item, "color", ctx), f"{ctx}.color")

        if tipo == "esfera":
            centro = _validar_vector3d(
                _obtener_campo(item, "centro", ctx), f"{ctx}.centro"
            )
            radio = _obtener_campo(item, "radio", ctx)
            if not _es_numero(radio) or radio <= 0:
                raise SceneError(f"'{ctx}.radio' debe ser un número mayor a 0.")
            objetos.append(
                DatosEsfera(tipo="esfera", centro=centro, radio=float(radio), color=color)
            )
        elif tipo == "plano":
            punto = _validar_vector3d(
                _obtener_campo(item, "punto", ctx), f"{ctx}.punto"
            )
            normal = _validar_vector3d(
                _obtener_campo(item, "normal", ctx), f"{ctx}.normal"
            )
            if normal.norm() == 0:
                raise SceneError(f"'{ctx}.normal' no puede ser el vector cero.")
            objetos.append(
                DatosPlano(
                    tipo="plano", punto=punto, normal=normal.normalize(), color=color
                )
            )
        else:
            raise SceneError(
                f"Tipo de objeto no soportado en '{ctx}': '{tipo}'. Use 'esfera' o 'plano'."
            )
    return objetos


def cargar_escena(ruta_archivo: Union[str, Path]) -> Escena:
    """Lee y valida un archivo de escena JSON y devuelve una instancia de Escena."""
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise SceneError(f"No se encontró el archivo de escena: '{ruta}'.")
    if not ruta.is_file():
        raise SceneError(f"La ruta especificada no es un archivo válido: '{ruta}'.")

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise SceneError(
            f"El archivo '{ruta}' no es un JSON válido "
            f"(línea {exc.lineno}, columna {exc.colno}): {exc.msg}."
        ) from exc
    except OSError as exc:
        raise SceneError(f"No se pudo leer el archivo '{ruta}': {exc}.") from exc

    if not isinstance(datos, dict):
        raise SceneError("La raíz del archivo de escena debe ser un objeto JSON.")

    imagen = _parsear_imagen(_obtener_campo(datos, "imagen", "la raíz del JSON"))
    camara = _parsear_camara(_obtener_campo(datos, "camara", "la raíz del JSON"))
    fondo = _validar_color(_obtener_campo(datos, "fondo", "la raíz del JSON"), "fondo")

    luz_ambiental = _obtener_campo(datos, "luz_ambiental", "la raíz del JSON")
    if not _es_numero(luz_ambiental) or luz_ambiental < 0 or luz_ambiental > 1:
        raise SceneError("'luz_ambiental' debe ser un número en el intervalo [0, 1].")

    luces = _parsear_luces(_obtener_campo(datos, "luces", "la raíz del JSON"))
    objetos = _parsear_objetos(_obtener_campo(datos, "objetos", "la raíz del JSON"))

    return Escena(
        imagen=imagen,
        camara=camara,
        fondo=fondo,
        luz_ambiental=float(luz_ambiental),
        luces=luces,
        objetos=objetos,
    )
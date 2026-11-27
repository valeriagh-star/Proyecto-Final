import json
import pytest

from raytracer import main
from src.scene import DatosEsfera, DatosPlano, SceneError, cargar_escena
from src.vector import Vector3D


ESCENA_VALIDA = {
    "imagen": {"ancho": 400, "alto": 225},
    "camara": {"posicion": [0, 1, 3], "mira_a": [0, 0, -3], "fov": 60},
    "fondo": [0.6, 0.8, 1.0],
    "luz_ambiental": 0.1,
    "luces": [{"posicion": [5, 5, 0], "intensidad": 1.0}],
    "objetos": [
        {"tipo": "esfera", "centro": [0, 0, -3], "radio": 1, "color": [0.9, 0.3, 0.2]},
        {"tipo": "plano", "punto": [0, -1, 0], "normal": [0, 1, 0], "color": [0.8, 0.8, 0.8]},
    ],
}


def test_cargar_escena_valida(tmp_path):
    archivo = tmp_path / "escena.json"
    archivo.write_text(json.dumps(ESCENA_VALIDA), encoding="utf-8")

    escena = cargar_escena(archivo)

    assert escena.imagen.ancho == 400
    assert escena.imagen.alto == 225
    assert escena.camara.posicion == Vector3D(0, 1, 3)
    assert escena.camara.mira_a == Vector3D(0, 0, -3)
    assert escena.camara.fov == 60.0
    assert escena.fondo == Vector3D(0.6, 0.8, 1.0)
    assert escena.luz_ambiental == 0.1
    assert len(escena.luces) == 1
    assert escena.luces[0].posicion == Vector3D(5, 5, 0)
    assert escena.luces[0].intensidad == 1.0

    assert len(escena.objetos) == 2
    assert isinstance(escena.objetos[0], DatosEsfera)
    assert escena.objetos[0].centro == Vector3D(0, 0, -3)
    assert escena.objetos[0].radio == 1.0
    assert isinstance(escena.objetos[1], DatosPlano)
    assert escena.objetos[1].normal == Vector3D(0, 1, 0)


def test_archivo_inexistente():
    with pytest.raises(SceneError, match="No se encontró el archivo"):
        cargar_escena("no_existe_esta_escena.json")


def test_json_mal_formado(tmp_path):
    archivo = tmp_path / "rota.json"
    archivo.write_text('{"imagen": {"ancho": 400, }', encoding="utf-8")

    with pytest.raises(SceneError, match="no es un JSON válido"):
        cargar_escena(archivo)


def test_falta_campo_obligatorio(tmp_path):
    datos = dict(ESCENA_VALIDA)
    del datos["camara"]
    archivo = tmp_path / "sin_camara.json"
    archivo.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(SceneError, match="camara"):
        cargar_escena(archivo)


def test_color_fuera_de_rango(tmp_path):
    datos = json.loads(json.dumps(ESCENA_VALIDA))
    datos["fondo"] = [1.5, 0.0, 0.0]
    archivo = tmp_path / "color_malo.json"
    archivo.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(SceneError, match=r"\[0, 1\]"):
        cargar_escena(archivo)


def test_radio_invalido(tmp_path):
    datos = json.loads(json.dumps(ESCENA_VALIDA))
    datos["objetos"][0]["radio"] = -2
    archivo = tmp_path / "radio_negativo.json"
    archivo.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(SceneError, match="radio"):
        cargar_escena(archivo)


def test_tipo_objeto_desconocido(tmp_path):
    datos = json.loads(json.dumps(ESCENA_VALIDA))
    datos["objetos"].append({"tipo": "piramide", "color": [1, 1, 1]})
    archivo = tmp_path / "tipo_malo.json"
    archivo.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(SceneError, match="Tipo de objeto no soportado"):
        cargar_escena(archivo)


def test_cli_escena_valida(tmp_path):
    archivo = tmp_path / "escena.json"
    archivo.write_text(json.dumps(ESCENA_VALIDA), encoding="utf-8")

    codigo = main([str(archivo), str(tmp_path / "salida.ppm"), "--trabajadores", "4"])
    assert codigo == 0


def test_cli_archivo_inexistente_no_lanza_excepcion(capsys):
    codigo = main(["no_existe.json", "salida.ppm", "--trabajadores", "2"])
    captura = capsys.readouterr()

    assert codigo == 1
    assert "Error al cargar la escena" in captura.err
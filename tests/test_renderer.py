import pytest

from src.renderer import write_ppm,renderizar, _hay_sombra
from src.vector import Vector3D
from src.scene import Escena, ConfigImagen, ConfigCamara, Luz, DatosEsfera, DatosPlano
from src.geometry import Sphere 

def test_write_ppm_creates_file(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    assert output_path.exists()

def test_write_ppm_writes_correct_dimensions(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0), Vector3D(0, 1, 0)],
        [Vector3D(0, 0, 1), Vector3D(1, 1, 1)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    contenido = output_path.read_text(encoding="utf-8")
    lineas = contenido.splitlines()

    assert lineas[0] == "P3"
    assert lineas[1] == "2 2"
    assert lineas[2] == "255"

def test_write_ppm_writes_correct_colors(tmp_path):
    pixel_matrix = [
        [
            Vector3D(1, 0, 0),  
            Vector3D(0, 1, 0),
            Vector3D(0, 0, 1)     
        ]
    ]

    output_path = tmp_path / "imagen.ppm"
    write_ppm(pixel_matrix, output_path)

    contenido = output_path.read_text(encoding="utf-8")
    lineas = contenido.splitlines()

    assert lineas[3] == "255 0 0"
    assert lineas[4] == "0 255 0"
    assert lineas[5] == "0 0 255"

def test_write_ppm_writes_all_pixels(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0), Vector3D(0, 1, 0)],
        [Vector3D(0, 0, 1), Vector3D(1, 1, 1)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    contenido = output_path.read_text(encoding="utf-8")
    lineas = contenido.splitlines()

    assert len(lineas) == 7


def test_write_ppm_rejects_empty_matrix(tmp_path):
    output_path = tmp_path / "imagen-ppm"

    with pytest.raises(ValueError):
        write_ppm([], output_path)

def test_write_ppm_rejects_rows_with_different_widths(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0), Vector3D(0, 1, 0)],
        [Vector3D(0, 0, 1)]
    ]
    output_path = tmp_path / "imagen.ppm"

    with pytest.raises(ValueError):
        write_ppm(pixel_matrix, output_path)

def test_write_ppm_clamps_colors(tmp_path):
    pixel_matrix = [
        [Vector3D(-0.5, 0.5, 1.5)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    contenido = output_path.read_text(encoding="utf-8")
    lineas = contenido.splitlines()

    assert lineas[3] == "0 128 255"


def test_write_ppm_single_row(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0), Vector3D(0, 1, 0),
         Vector3D(0, 0, 1)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    lineas = output_path.read_text(encoding="utf-8").splitlines()

    assert lineas[1] == "3 1"


def test_write_ppm_single_column(tmp_path):
    pixel_matrix = [
        [Vector3D(1, 0, 0)],
        [Vector3D(0, 1, 0)],
        [Vector3D(0, 0, 1)]
    ]

    output_path = tmp_path / "imagen.ppm"

    write_ppm(pixel_matrix, output_path)

    lineas = output_path.read_text(encoding="utf-8").splitlines()

    assert lineas[1] == "1 3"

def test_renderizar_escena_sin_objetos(tmp_path):
    escena = Escena(
        imagen=ConfigImagen(ancho=2, alto=2),
        camara=ConfigCamara(
            posicion=Vector3D(0, 0, 0),
            mira_a=Vector3D(0, 0, -1),
            fov=90
        ),
        fondo=Vector3D(0.2, 0.4, 0.6),
        luz_ambiental=0.1,
        luces=[
            Luz(
                posicion=Vector3D(0, 5, 0),
                            intensidad=1.0
            )
        ],
        objetos=[]
    )

    archivo = tmp_path / "imagen.ppm"
    renderizar(escena, archivo)

    contenido = archivo.read_text(encoding="utf-8").splitlines()

    assert contenido[0] == "P3"
    assert contenido[1] == "2 2"
    assert contenido[2] == "255"

    colores = contenido[3:]

    assert len(colores) == 4

    for color in colores:
        assert color == "51 102 153"


def test_renderizar_esfera_con_color_ambiental(tmp_path):
    escena = Escena(
        imagen=ConfigImagen(ancho=3, alto=3),
        camara=ConfigCamara(
            posicion=Vector3D(0, 0, 0),
            mira_a=Vector3D(0, 0, -1),
            fov=90
        ),
        fondo=Vector3D(0, 0, 0),
        luz_ambiental=1.0,
        luces=[
            Luz(
                posicion=Vector3D(0, 5, 0),
                intensidad=0.0
            )
        ],
        objetos=[
            DatosEsfera(
                tipo="esfera",
                centro=Vector3D(0, 0, -3),
                radio=1,
                color=Vector3D(1, 0, 0)
            )
        ]
    )

    archivo = tmp_path / "esfera.ppm"

    renderizar(escena, archivo)

    contenido = archivo.read_text(encoding="utf-8").splitlines()

    assert contenido[0] == "P3"
    assert contenido[1] == "3 3"

    colores = contenido[3:]

    assert "255 0 0" in colores


def test_renderizar_esfera_con_iluminacion_difusa(tmp_path):
    escena = Escena(
        imagen=ConfigImagen(ancho=3, alto=3),
        camara=ConfigCamara(
            posicion=Vector3D(0, 0, 0),
            mira_a=Vector3D(0, 0, -1),
            fov=90
        ),
        fondo=Vector3D(0, 0, 0),
        luz_ambiental=0.0,
        luces=[
            Luz(
                posicion=Vector3D(0, 0, 0),
                intensidad=1.0
            )
        ],
        objetos=[
            DatosEsfera(
                tipo="esfera",
                centro=Vector3D(0, 0, -3),
                radio=1,
                color=Vector3D(1, 0, 0)
            )
        ]
    )

    archivo = tmp_path / "difusa.ppm"

    renderizar(escena, archivo)

    contenido = archivo.read_text(encoding="utf-8").splitlines()
    colores = contenido[3:]

    assert "255 0 0" in colores


def test_hay_sombra_cuando_un_objeto_bloquea_la_luz():
    punto = Vector3D(0, 0, 0)
    normal = Vector3D(0, 0, 1)
    direccion_luz = Vector3D(0, 0, 1)
    distancia_luz = 10

    esfera = Sphere(
        Vector3D(0, 0, 5),
        1
    )

    objetos = [(esfera, None)]

    resultado = _hay_sombra(
        punto,
        normal,
        direccion_luz,
        distancia_luz,
        objetos
    )

    assert resultado is True

def test_no_hay_sombra_cuando_no_hay_obstaculos():
    punto = Vector3D(0, 0, 0)
    normal = Vector3D(0, 0, 1)
    direccion_luz = Vector3D(0, 0, 1)
    distancia_luz = 10

    objetos = []

    resultado = _hay_sombra(
        punto,
        normal,
        direccion_luz,
        distancia_luz,
        objetos
    )

    assert resultado is False

def test_renderizar_plano_con_color_ambiental(tmp_path):
    escena = Escena(
        imagen=ConfigImagen(ancho=3, alto=3),
        camara=ConfigCamara(
            posicion=Vector3D(0, 0, 0),
            mira_a=Vector3D(0, 0, -1),
            fov=90
        ),
        fondo=Vector3D(0, 0, 0),
        luz_ambiental=1.0,
        luces=[
            Luz(
                posicion=Vector3D(0, 5, 0),
                intensidad=0.0
            )
        ],
        objetos=[
            DatosPlano(
                tipo="plano",
                punto=Vector3D(0, 0, -3),
                normal=Vector3D(0, 0, 1),
                color=Vector3D(0, 1, 0)
            )
        ]
    )

    archivo = tmp_path / "plano.ppm"

    renderizar(escena, archivo)

    contenido = archivo.read_text(encoding="utf-8").splitlines()
    colores = contenido[3:]

    assert contenido[0] == "P3"
    assert contenido[1] == "3 3"
    assert "0 255 0" in colores
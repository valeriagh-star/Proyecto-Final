import pytest

from src.renderer import write_ppm
from src.vector import Vector3D


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



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


        


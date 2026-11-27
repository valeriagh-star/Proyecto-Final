# Escenas de Prueba y Benchmark (`scenes/`)

Este directorio contiene las escenas en formato JSON diseñadas para validar la correcta proyección de cámara, el cálculo de sombras, la iluminación con múltiples fuentes de luz y el desempeño del renderizado paralelo, junto con sus imágenes de salida generadas en formato PPM (`P3`).

## Descripción de las escenas

| Archivo JSON | Salida PPM | Resolución | Objetos y Luces | Propósito de prueba |
| :--- | :--- | :---: | :--- | :--- |
| **`escena1_basica.json`** | `escena1_basica.ppm` | `400x225` | 1 esfera, 1 plano, 1 luz | Verifica la proyección básica de cámara, intersección primaria, iluminación difusa de Lambert y proyección de una sombra simple sobre el plano. |
| **`escena2_dos_luces.json`** | `escena2_dos_luces.ppm` | `400x225` | 3 esferas, 1 plano, 2 luces | Evalúa la acumulación de intensidad luminosa desde dos ángulos distintos, sombras múltiples superpuestas y oclusión entre objetos. |
| **`escena3_benchmark.json`** | `escena3_benchmark.ppm` | `400x225` | 5 esferas, 1 plano, 2 luces | Escena de mayor carga computacional utilizada para medir el *speedup* entre `1`, `2`, `4` y `8` trabajadores y analizar la Ley de Amdahl. |

## Comandos de ejecución

Desde la raíz del proyecto, cada escena puede renderizarse especificando el número de procesos trabajadores mediante `--trabajadores`:

```bash
python3 raytracer.py scenes/escena1_basica.json scenes/escena1_basica.ppm --trabajadores 4
python3 raytracer.py scenes/escena2_dos_luces.json scenes/escena2_dos_luces.ppm --trabajadores 4
python3 raytracer.py scenes/escena3_benchmark.json scenes/escena3_benchmark.ppm --trabajadores 4


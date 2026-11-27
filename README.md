## Pruebas y Rendimiento (Paralelismo y Ley de Amdahl)

Para evaluar el desempeño de la paralelización por filas mediante `multiprocessing.Pool`, se ejecutaron 3 corridas independientes para cada configuración de trabajadores sobre la escena `scenes/escena3_benchmark.json` (resolución `400x225`, 6 objetos y 2 fuentes de luz).

| Trabajadores ($n$) | Corrida 1 (s) | Corrida 2 (s) | Corrida 3 (s) | Promedio $T_n$ (s) | Speedup $S(n) = T_1 / T_n$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1 (Secuencial)** | `4.2579` | `5.0710` | `4.3721` | `4.5670` | `1.00x` |
| **2** | `3.3281` | `3.3836` | `3.2347` | `3.3155` | `1.38x` |
| **4** | `2.1749` | `2.1455` | `2.2086` | `2.1763` | `2.10x` |
| **8** | `1.4539` | `1.4723` | `1.5130` | `1.4797` | `3.09x` |

### Análisis con la Ley de Amdahl
De acuerdo con la **Ley de Amdahl**, la aceleración máxima teórica al paralelizar un programa en $n$ procesos está acotada por la fracción secuencial $s$ del código que no puede dividirse entre trabajadores:

$$S(n) = \frac{1}{s + \frac{1 - s}{n}}$$

En este trazador de rayos, el *speedup* observado ($1.38\text{x}$, $2.10\text{x}$ y $3.09\text{x}$) es menor al ideal lineal ($2\text{x}$, $4\text{x}$ y $8\text{x}$) debido a tres factores:
1. **Fracción secuencial obligatoria ($s$):** La lectura y validación del archivo JSON, la instanciación inicial de la escena y la escritura secuencial del archivo de salida `.ppm` se ejecutan en un único proceso principal.
2. **Sobrecarga de procesos e IPC (*overhead*):** Al usar `multiprocessing.Pool`, el sistema operativo debe crear los procesos hijos, serializar (*pickle*) los datos de la escena hacia cada trabajador y recolectar de vuelta las filas calculadas.
3. **Límite físico de núcleos de CPU:** Al aumentar a $n = 8$ trabajadores, la ganancia marginal se reduce respecto a duplicar procesos debido a la disponibilidad de núcleos físicos del procesador y al cambio de contexto entre procesos.
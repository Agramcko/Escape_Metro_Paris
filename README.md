# Escape Metro Paris

Proyecto de Modelación de Sistemas en Redes.

Implementación en Python (solo librería estándar) para calcular un plan de
escape sincronizado para Pierre y Amélie en el Metro de París, evitando
colisiones y respetando restricciones opcionales de líneas.

## Requisitos

- Python 3.10 o superior.
- No se usan librerías de terceros.

## Ejecución

```bash
python main.py
```

Por defecto lee `input.txt` y escribe `output.txt` en la carpeta del proyecto.
También se pueden indicar rutas explícitas:

```bash
python main.py ruta/input.txt ruta/output.txt
```

## Formato de `input.txt`

```text
# Número de estaciones, número de túneles
15 22

# Estación | Tiempo de transbordo
1 2
2 3
...

# Túneles: Origen | Destino | Tiempo de viaje | Línea
1 2 4 L1
2 3 3 L1
...

# Misión: Origen_Pierre | Origen_Amélie | Destino_Pierre | Destino_Amélie
1 12 7 8
```

Los comentarios con `#` pueden ocupar una línea completa o estar al final de
una línea de datos.

## Restricciones opcionales

Después de la línea de misión se pueden agregar restricciones:

```text
RESTRICCIONES
CERRADA L1 10 20
CERRADA L3
DUPLICA L4
DUPLICA L2 3
```

- `CERRADA <linea> [inicio fin]`: la línea no está disponible para viajar
  durante la ventana `[inicio, fin)`, medida en minutos desde el inicio de la
  operación. Si se omite la ventana, la línea está cerrada siempre.
- `DUPLICA <linea> [factor]`: multiplica el tiempo de viaje de esa línea. Si
  se omite el factor, se usa `2`.

La cabecera `RESTRICCIONES` es opcional; las instrucciones se reconocen
directamente. Si aparece una instrucción desconocida, el programa lanza un
error indicando la línea del archivo.

## Formato de `output.txt`

En caso de éxito:

```text
=== PLAN DE ESCAPE CONFIGURADO ===
Tiempo Total de la Operación: 20 minutos

[PROGRAMACIÓN DE SALIDAS]
* Pierre arranca en el minuto: 0
* Amélie arranca en el minuto: 8 (Debe esperar 8 minutos en su estación de origen)

[RUTA DE PIERRE (Tiempo total de viaje: 20 min)]
Minuto 0: Estación 1 (Origen)
Minuto 6: Estación 10 (Viaje L5)
Minuto 8: Estación 10 (Termina Transbordo a L2)
...
Minuto 20: Estación 7 (Destino Compuerta D1)

[RUTA DE AMÉLIE (Tiempo total de viaje: 12 min)]
Minuto 8: Estación 12 (Origen - Inicia Movimiento)
...
Minuto 20: Estación 8 (Destino Compuerta D2)

Resultado de Sincronización: ÉXITO. Llegada simultánea en el minuto 20.
```

Si no existe ruta o no se encuentra un plan sin colisiones, se escribe un
mensaje explicando el motivo.

## Algoritmo

1. El grafo se guarda como **lista de adyacencia** (`{estación: [aristas]}`).
   Es adecuada porque el metro es un grafo disperso: usa `O(V + E)` memoria y
   permite recorrer los vecinos de forma eficiente.
2. Se ejecuta **Dijkstra** con estado `(estación, línea)`. El estado incluye la
   línea de llegada porque el costo de un transbordo depende de la línea
   anterior. Los pesos son no negativos (tiempos en minutos).
3. Para cada personaje se generan hasta 200 rutas candidatas de bajo costo por
   escenario (con y sin líneas potencialmente cerradas). Esto permite buscar
   alternativas cuando la ruta más corta produce una colisión.
4. Para cada par de rutas se calcula el menor tiempo común `T`:
   `delay_P = T - costo_P`, `delay_A = T - costo_A`, con `T >= max(costo_P,
   costo_A)`.
5. Se construyen las agendas de ambos personajes y se verifican colisiones:
   - misma estación en el mismo instante (incluye tiempo de transbordo y
     espera en el origen);
   - mismo túnel (en cualquier sentido) con intervalos superpuestos;
   - excepción: si ambos destinos son la misma estación, se permite el
     acceso simultáneo final (dos compuertas del búnker).
6. Se elige el par de rutas con menor `T` que no tenga colisiones.

## Supuestos y limitaciones

- Los tiempos se manejan en minutos enteros.
- Las ventanas de cierre son absolutas desde el minuto 0 y semiabiertas:
  `[inicio, fin)`.
- Solo se permite retrasar la salida desde el origen; no se modela espera en
  estaciones intermedias para esperar la reapertura de una línea.
- Se consideran hasta 400 rutas candidatas (200 por escenario). El resultado
  es exacto entre esas candidatas; para los tamaños manejados en el proyecto
  es suficiente.
- Se prohíbe compartir un túnel en el mismo intervalo, sin importar el
  sentido, para ser conservadores con la restricción de no colisión espacial.
- Como ambos llegan en el mismo minuto, no se acumulan puntos de riesgo por
  desfase. El formato del enunciado no incluye una línea de puntos de riesgo,
  así que no se agrega al output.

## Pruebas

```bash
python -m unittest tests.test_project -v
```

Las pruebas cubren: caso del enunciado, formato de salida, colisiones
evitables e inevitables, túnel en sentido opuesto, excepción del búnker,
línea cerrada, ventana de cierre, línea duplicada, falta de ruta y validaciones
del parser.

## Estructura

- `main.py`: punto de entrada.
- `graph.py`: estaciones, aristas y grafo.
- `parser.py`: lectura y validación del input.
- `restrictions.py`: cierres y duplicación de líneas.
- `solver.py`: rutas, sincronización y verificación de colisiones.
- `reporter.py`: generación del output.
- `tests/`: pruebas automatizadas y datos de ejemplo.

from graph import MetroGraph
from restrictions import Restrictions


def _parse_ints(parts, count, line_no, what):
    if len(parts) != count:
        raise ValueError(
            f"Línea {line_no}: se esperaban {count} valores para {what}, "
            f"pero se encontraron {len(parts)}: {' '.join(parts)}"
        )
    try:
        return [int(value) for value in parts]
    except ValueError as exc:
        raise ValueError(f"Línea {line_no}: valor no entero en {what}: {' '.join(parts)}") from exc


def load_input(filepath: str):
    graph = MetroGraph()
    restrictions = Restrictions()

    lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            # Permite comentarios completos y comentarios al final de una línea.
            text = raw.split("#", 1)[0].strip()
            if text:
                lines.append((line_no, text))

    if not lines:
        raise ValueError("El archivo de entrada está vacío.")

    def get(index, description):
        if index >= len(lines):
            raise ValueError(f"El archivo termina antes de leer {description}.")
        return lines[index]

    line_no, text = get(0, "la cabecera")
    header = _parse_ints(text.split(), 2, line_no, "la cabecera (estaciones y túneles)")
    num_stations, num_tunnels = header
    if num_stations < 0 or num_tunnels < 0:
        raise ValueError("La cantidad de estaciones y túneles no puede ser negativa.")

    idx = 1
    for _ in range(num_stations):
        line_no, text = get(idx, "una estación")
        station_id, transfer_time = _parse_ints(
            text.split(), 2, line_no, "una estación (ID y tiempo de transbordo)"
        )
        if transfer_time < 0:
            raise ValueError(f"Línea {line_no}: el tiempo de transbordo no puede ser negativo.")
        graph.add_station(station_id, transfer_time)
        idx += 1

    for _ in range(num_tunnels):
        line_no, text = get(idx, "un túnel")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                f"Línea {line_no}: se esperaban 4 valores para un túnel "
                f"(origen, destino, tiempo, línea), pero hay {len(parts)}."
            )
        try:
            src, dest, travel_time = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise ValueError(
                f"Línea {line_no}: origen, destino y tiempo deben ser enteros."
            ) from exc
        line_code = parts[3].upper()
        if travel_time <= 0:
            raise ValueError(f"Línea {line_no}: el tiempo de viaje debe ser positivo.")
        if not line_code:
            raise ValueError(f"Línea {line_no}: el código de línea no puede estar vacío.")
        graph.add_tunnel(src, dest, travel_time, line_code)
        idx += 1

    line_no, text = get(idx, "los datos de la misión")
    mission_values = _parse_ints(
        text.split(), 4, line_no,
        "la misión (origen Pierre, origen Amélie, destino Pierre, destino Amélie)"
    )
    op, oa, dp, da = mission_values
    for station_id in (op, oa, dp, da):
        if station_id not in graph.stations:
            raise ValueError(
                f"Línea {line_no}: la estación {station_id} de la misión no existe en el grafo."
            )
    idx += 1

    known_lines = {edge.line for edge in graph.edges()}

    # Restricciones opcionales después de la misión.
    while idx < len(lines):
        line_no, text = lines[idx]
        parts = text.split()
        keyword = parts[0].upper().rstrip(":")

        if keyword in {"RESTRICCIONES", "RESTRICTIONS"}:
            idx += 1
            continue

        if keyword in {"CERRADA", "CERRADO", "CERRADAS", "LINEA_CERRADA", "CLOSED"}:
            if len(parts) not in {2, 4}:
                raise ValueError(
                    f"Línea {line_no}: formato esperado: CERRADA <linea> [inicio fin]."
                )
            line_code = parts[1].upper()
            if line_code not in known_lines:
                raise ValueError(f"Línea {line_no}: la línea {line_code} no existe en el grafo.")
            if len(parts) == 2:
                restrictions.add_closure(line_code)
            else:
                try:
                    start, end = int(parts[2]), int(parts[3])
                except ValueError as exc:
                    raise ValueError(
                        f"Línea {line_no}: el inicio y el fin del cierre deben ser enteros."
                    ) from exc
                restrictions.add_closure(line_code, start, end)
            idx += 1
            continue

        if keyword in {
            "DUPLICA", "DUPLICADA", "DUPLICADO", "LINEA_DUPLICADA",
            "DOUBLE", "RETRASO", "DELAY"
        }:
            if len(parts) not in {2, 3}:
                raise ValueError(
                    f"Línea {line_no}: formato esperado: DUPLICA <linea> [factor]."
                )
            line_code = parts[1].upper()
            if line_code not in known_lines:
                raise ValueError(f"Línea {line_no}: la línea {line_code} no existe en el grafo.")
            factor = 2
            if len(parts) == 3:
                try:
                    factor = int(parts[2])
                except ValueError as exc:
                    raise ValueError(
                        f"Línea {line_no}: el factor de duplicación debe ser entero."
                    ) from exc
            restrictions.add_double(line_code, factor)
            idx += 1
            continue

        raise ValueError(
            f"Línea {line_no}: no se reconoce la instrucción: {text!r}. "
            "Use CERRADA <linea> [inicio fin] o DUPLICA <linea> [factor]."
        )

    mission_data = {
        "origin_p": op,
        "origin_a": oa,
        "bunker_p": dp,
        "bunker_a": da,
    }
    return graph, mission_data, restrictions

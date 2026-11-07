import heapq
import itertools
from collections import namedtuple

from restrictions import Restrictions


PathNode = namedtuple("PathNode", "station line cost edge")
Candidate = namedtuple("Candidate", "cost path")
Schedule = namedtuple("Schedule", "station_intervals edge_intervals final_arrival")


def _transfer_time(graph, station_id, incoming_line, outgoing_line):
    if incoming_line is None or outgoing_line is None or incoming_line == outgoing_line:
        return 0
    return graph.stations[station_id].transfer_time


def _edge_cost(graph, station_id, current_line, edge, restrictions):
    transfer = _transfer_time(graph, station_id, current_line, edge.line)
    return transfer + restrictions.travel_time(edge)


def shortest_path(graph, start, target, restrictions, forbidden_lines=None):
    """Dijkstra con estado (estación, línea) y penalización por transbordo."""
    if start not in graph.stations or target not in graph.stations:
        return float("inf"), []

    forbidden_lines = forbidden_lines or set()
    dist = {(start, None): 0}
    prev = {(start, None): (None, None)}
    counter = itertools.count()
    pq = [(0, next(counter), start, None)]

    target_state = None
    while pq:
        cost, _, station, line = heapq.heappop(pq)
        state = (station, line)
        if cost != dist.get(state):
            continue
        if station == target:
            target_state = state
            break
        for edge in graph.adj_list.get(station, []):
            if edge.line in forbidden_lines:
                continue
            new_cost = cost + _edge_cost(graph, station, line, edge, restrictions)
            next_state = (edge.destination, edge.line)
            if new_cost < dist.get(next_state, float("inf")):
                dist[next_state] = new_cost
                prev[next_state] = (state, edge)
                heapq.heappush(pq, (new_cost, next(counter), edge.destination, edge.line))

    if target_state is None:
        return float("inf"), []

    nodes = []
    state = target_state
    while state is not None:
        station, line = state
        prev_state, edge = prev[state]
        nodes.append(PathNode(station, line, dist[state], edge))
        state = prev_state
    nodes.reverse()
    return dist[target_state], nodes


def _path_key(path):
    return tuple(node.edge.id for node in path[1:] if node.edge is not None)


def generate_candidate_paths(graph, start, target, restrictions, k=200, forbidden_lines=None):
    """Genera hasta k rutas loopless (en el grafo expandido) ordenadas por costo."""
    best_cost, _ = shortest_path(graph, start, target, restrictions, forbidden_lines)
    if best_cost == float("inf"):
        return []

    max_cost = best_cost * 3 + 200
    forbidden_lines = forbidden_lines or set()
    k_limit = max(k, 50)

    counter = itertools.count()
    pq = [(0, start, "", next(counter), (PathNode(start, None, 0, None),))]
    pop_count = {}
    results = []
    seen_paths = set()
    expansions = 0

    while pq and len(results) < k and expansions < 300000:
        cost, _, _, _, path = heapq.heappop(pq)
        expansions += 1
        current = path[-1]
        state = (current.station, current.line)
        pop_count[state] = pop_count.get(state, 0) + 1
        if pop_count[state] > k_limit:
            continue

        if current.station == target:
            key = _path_key(path)
            if key not in seen_paths:
                seen_paths.add(key)
                results.append(Candidate(cost, path))
            continue

        if cost > max_cost:
            break

        for edge in graph.adj_list.get(current.station, []):
            if edge.line in forbidden_lines:
                continue
            if any(node.station == edge.destination and node.line == edge.line for node in path):
                continue
            transfer = _transfer_time(graph, current.station, current.line, edge.line)
            new_cost = cost + transfer + restrictions.travel_time(edge)
            if new_cost > max_cost:
                continue
            new_node = PathNode(edge.destination, edge.line, new_cost, edge)
            new_path = path + (new_node,)
            heapq.heappush(
                pq,
                (new_cost, edge.destination, edge.line or "", next(counter), new_path),
            )

    results.sort(key=lambda item: (item.cost, _path_key(item.path)))
    return results


def generate_all_candidates(graph, start, target, restrictions, k=200, max_total=400):
    always_closed = restrictions.always_closed_lines()
    timed_closed = restrictions.timed_closed_lines()

    forbidden_sets = [always_closed]
    if timed_closed:
        forbidden_sets.append(always_closed | timed_closed)

    candidates = []
    seen = set()
    for forbidden in forbidden_sets:
        for candidate in generate_candidate_paths(
            graph, start, target, restrictions, k=k, forbidden_lines=forbidden
        ):
            key = _path_key(candidate.path)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)

    candidates.sort(key=lambda item: (item.cost, _path_key(item.path)))
    return candidates[:max_total]


def path_relative_edge_intervals(graph, path, restrictions):
    """Intervalos relativos (sin desfase) de cada tramo: (linea, salida, llegada)."""
    intervals = []
    for i in range(len(path) - 1):
        node = path[i]
        next_node = path[i + 1]
        transfer = _transfer_time(graph, node.station, node.line, next_node.line)
        rel_start = node.cost + transfer
        rel_end = rel_start + restrictions.travel_time(next_node.edge)
        intervals.append((next_node.edge.line, rel_start, rel_end))
    return intervals


def compute_valid_starts(graph, path, restrictions, horizon):
    """
    Devuelve un bytearray donde valid[d] == 1 si la ruta es válida para un
    desfase de salida d. Devuelve None si la ruta no usa líneas con cierres.
    """
    intervals = path_relative_edge_intervals(graph, path, restrictions)
    uses_closures = any(restrictions.windows(line) for line, _, _ in intervals)
    if not uses_closures:
        return None

    valid = bytearray([1]) * (horizon + 1)
    for line, rel_start, rel_end in intervals:
        for c_start, c_end in restrictions.windows(line):
            if c_end is None:
                lo = max(0, c_start - rel_end + 1)
                hi = horizon
            else:
                lo = max(0, c_start - rel_end + 1)
                hi = min(horizon, c_end - rel_start - 1)
            if lo <= hi:
                valid[lo:hi + 1] = b"\x00" * (hi - lo + 1)
    return valid


def _is_valid_start(valid, delay, horizon):
    if valid is None:
        return True
    if delay < 0 or delay > horizon:
        return False
    return bool(valid[delay])


def find_synchronized_time(path_p, path_a, valid_p, valid_a, horizon, best_t=None):
    """Menor T común para el que ambos desfases son válidos, o None."""
    cost_p = path_p.cost
    cost_a = path_a.cost
    delta = cost_a - cost_p  # delay_p = delay_a + delta
    delay_a_start = max(0, -delta)
    delay_a_end = horizon

    if best_t is not None:
        delay_a_end = min(delay_a_end, best_t - cost_a - 1)
    if delay_a_end < delay_a_start:
        return None

    for delay_a in range(delay_a_start, delay_a_end + 1):
        delay_p = delay_a + delta
        if delay_p < 0:
            continue
        if delay_p > horizon:
            break
        if _is_valid_start(valid_a, delay_a, horizon) and _is_valid_start(valid_p, delay_p, horizon):
            return delay_a + cost_a
    return None


def build_schedule(graph, path, start_delay, restrictions):
    station_intervals = []
    edge_intervals = []

    for i, node in enumerate(path):
        arrival = start_delay + node.cost
        outgoing_line = path[i + 1].line if i + 1 < len(path) else None
        transfer = _transfer_time(graph, node.station, node.line, outgoing_line)
        departure = arrival + transfer

        if i == 0:
            # Si hay desfase, la persona espera en su estación de origen desde
            # el minuto 0 hasta que arranca.
            station_intervals.append((node.station, 0, departure))
        else:
            station_intervals.append((node.station, arrival, departure))

        if i + 1 < len(path):
            edge = path[i + 1].edge
            edge_start = departure
            edge_end = departure + restrictions.travel_time(edge)
            edge_intervals.append((edge.src, edge.destination, edge.line, edge_start, edge_end))

    final_arrival = start_delay + path[-1].cost
    return Schedule(station_intervals, edge_intervals, final_arrival)


def _same_tunnel(u1, v1, u2, v2):
    return (u1 == u2 and v1 == v2) or (u1 == v2 and v1 == u2)


def has_collision(schedule_p, schedule_a, dest_p, dest_a, t_max):
    for station_p, start_p, end_p in schedule_p.station_intervals:
        for station_a, start_a, end_a in schedule_a.station_intervals:
            if station_p != station_a:
                continue
            if max(start_p, start_a) <= min(end_p, end_a):
                # Excepción: dos compuertas del mismo búnker en el instante final.
                if (
                    station_p == dest_p == dest_a
                    and start_p == end_p == t_max
                    and start_a == end_a == t_max
                ):
                    continue
                return True

    for u1, v1, _, start1, end1 in schedule_p.edge_intervals:
        for u2, v2, _, start2, end2 in schedule_a.edge_intervals:
            if _same_tunnel(u1, v1, u2, v2) and max(start1, start2) < min(end1, end2):
                return True

    return False


def build_output_events(graph, path, delay, origin_label, destination_label):
    events = []
    if not path:
        return events

    origin = path[0]
    events.append((delay, origin.station, origin_label))

    for i in range(len(path) - 1):
        node = path[i]
        next_node = path[i + 1]
        transfer = _transfer_time(graph, node.station, node.line, next_node.line)

        if node.line is not None and next_node.line != node.line:
            events.append((
                delay + node.cost + transfer,
                node.station,
                f"Termina Transbordo a {next_node.line}",
            ))

        if i + 1 == len(path) - 1:
            label = destination_label
        else:
            label = f"Viaje {next_node.line}"
        events.append((delay + next_node.cost, next_node.station, label))

    return events


def synchronize_escape(graph, mission, restrictions=None):
    if restrictions is None:
        restrictions = Restrictions()

    origin_p = mission["origin_p"]
    origin_a = mission["origin_a"]
    dest_p = mission["bunker_p"]
    dest_a = mission["bunker_a"]

    candidates_p = generate_all_candidates(graph, origin_p, dest_p, restrictions)
    if not candidates_p:
        return {
            "success": False,
            "message": (
                f"No existe una ruta para Pierre entre la estación {origin_p} "
                f"y la estación {dest_p} con las restricciones dadas."
            ),
        }

    candidates_a = generate_all_candidates(graph, origin_a, dest_a, restrictions)
    if not candidates_a:
        return {
            "success": False,
            "message": (
                f"No existe una ruta para Amélie entre la estación {origin_a} "
                f"y la estación {dest_a} con las restricciones dadas."
            ),
        }

    max_cost = max(
        [candidate.cost for candidate in candidates_p]
        + [candidate.cost for candidate in candidates_a]
    )
    horizon = restrictions.max_closure_end() + max_cost + 200
    horizon = min(max(horizon, 0), 100000)

    valid_p = [
        compute_valid_starts(graph, candidate.path, restrictions, horizon)
        for candidate in candidates_p
    ]
    valid_a = [
        compute_valid_starts(graph, candidate.path, restrictions, horizon)
        for candidate in candidates_a
    ]

    best = None
    saw_collision = False
    saw_no_schedule = False

    for i, candidate_p in enumerate(candidates_p):
        if best is not None and candidate_p.cost >= best["t_max"]:
            break
        for j, candidate_a in enumerate(candidates_a):
            if best is not None and candidate_a.cost >= best["t_max"]:
                break

            t_max = find_synchronized_time(
                candidate_p,
                candidate_a,
                valid_p[i],
                valid_a[j],
                horizon,
                best["t_max"] if best is not None else None,
            )
            if t_max is None:
                saw_no_schedule = True
                continue
            if best is not None and t_max >= best["t_max"]:
                continue

            delay_p = t_max - candidate_p.cost
            delay_a = t_max - candidate_a.cost
            schedule_p = build_schedule(graph, candidate_p.path, delay_p, restrictions)
            schedule_a = build_schedule(graph, candidate_a.path, delay_a, restrictions)

            if has_collision(schedule_p, schedule_a, dest_p, dest_a, t_max):
                saw_collision = True
                continue

            best = {
                "success": True,
                "t_max": t_max,
                "pierre": {
                    "origin": origin_p,
                    "destination": dest_p,
                    "cost": candidate_p.cost,
                    "delay": delay_p,
                    "path": candidate_p.path,
                    "events": build_output_events(
                        graph, candidate_p.path, delay_p,
                        "Origen", "Destino Compuerta D1"
                    ),
                },
                "amelie": {
                    "origin": origin_a,
                    "destination": dest_a,
                    "cost": candidate_a.cost,
                    "delay": delay_a,
                    "path": candidate_a.path,
                    "events": build_output_events(
                        graph, candidate_a.path, delay_a,
                        "Origen - Inicia Movimiento", "Destino Compuerta D2"
                    ),
                },
            }

    if best is not None:
        return best

    if saw_collision and not saw_no_schedule:
        message = "No se encontró un plan de escape sin colisiones entre las rutas candidatas."
    elif saw_no_schedule and not saw_collision:
        message = "No se encontró un horario válido que respete las restricciones de líneas."
    else:
        message = (
            "No se encontró un plan de escape válido: todas las rutas candidatas "
            "presentan colisiones o incumplen las restricciones de líneas."
        )
    return {"success": False, "message": message}

class Station:
    def __init__(self, station_id: int, transfer_time: int):
        self.id = station_id
        self.transfer_time = transfer_time

    def __repr__(self):
        return f"Station({self.id}, transfer={self.transfer_time})"


class Edge:
    def __init__(self, edge_id: int, src: int, dest: int, travel_time: int, line: str):
        self.id = edge_id
        self.src = src
        self.destination = dest
        self.travel_time = travel_time
        self.line = line

    def __repr__(self):
        return f"Edge({self.src}->{self.destination}, {self.travel_time}min, {self.line})"


class MetroGraph:
    def __init__(self):
        # {station_id: Station}
        self.stations = {}
        # {station_id: [Edge, ...]}
        self.adj_list = {}
        self._next_edge_id = 0

    def add_station(self, station_id: int, transfer_time: int):
        if station_id in self.stations:
            raise ValueError(f"Estación duplicada: {station_id}")
        self.stations[station_id] = Station(station_id, transfer_time)
        self.adj_list.setdefault(station_id, [])

    def add_tunnel(self, src: int, dest: int, travel_time: int, line: str):
        if src not in self.stations:
            raise ValueError(f"El túnel referencia una estación origen inexistente: {src}")
        if dest not in self.stations:
            raise ValueError(f"El túnel referencia una estación destino inexistente: {dest}")
        edge = Edge(self._next_edge_id, src, dest, travel_time, line)
        self._next_edge_id += 1
        self.adj_list[src].append(edge)
        return edge

    def edges(self):
        for edges in self.adj_list.values():
            for edge in edges:
                yield edge

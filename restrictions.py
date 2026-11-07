class Restrictions:
    """
    Restricciones opcionales del input.

    - DUPLICA <linea> [factor]: multiplica el tiempo de viaje de la línea.
      Si no se indica factor, se usa 2 (el enunciado habla de duplicar).
    - CERRADA <linea> [inicio fin]: la línea no está disponible para viajar
      durante la ventana [inicio, fin) medida en minutos desde el inicio de
      la operación. Si no se indican horas, la línea está cerrada siempre.
    """

    def __init__(self):
        self._factors = {}
        self._windows = {}

    def add_double(self, line: str, factor: int = 2):
        if factor <= 0:
            raise ValueError(f"El factor de duplicación debe ser positivo para {line}")
        self._factors[line] = factor

    def add_closure(self, line: str, start: int = 0, end=None):
        if start < 0:
            raise ValueError(f"El inicio de cierre no puede ser negativo para {line}")
        if end is not None and end < start:
            raise ValueError(f"El fin de cierre no puede ser menor que el inicio para {line}")
        self._windows.setdefault(line, []).append((start, end))

    def factor(self, line: str) -> int:
        return self._factors.get(line, 1)

    def travel_time(self, edge) -> int:
        return edge.travel_time * self.factor(edge.line)

    def windows(self, line: str):
        return self._windows.get(line, [])

    def has_closures(self) -> bool:
        return any(self._windows.values())

    def always_closed_lines(self):
        result = set()
        for line, windows in self._windows.items():
            for _, end in windows:
                if end is None:
                    result.add(line)
                    break
        return result

    def timed_closed_lines(self):
        result = set()
        for line, windows in self._windows.items():
            if any(end is not None for _, end in windows):
                result.add(line)
        return result

    def max_closure_end(self) -> int:
        maximum = 0
        for windows in self._windows.values():
            for _, end in windows:
                if end is not None:
                    maximum = max(maximum, end)
        return maximum

    def line_available(self, line: str, start: int, end: int) -> bool:
        """True si la línea no está cerrada durante el intervalo [start, end)."""
        for c_start, c_end in self.windows(line):
            if c_end is None:
                c_end = float("inf")
            if end > start:
                if start < c_end and end > c_start:
                    return False
            else:
                if c_start <= start < c_end:
                    return False
        return True

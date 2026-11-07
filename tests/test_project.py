import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parser import load_input
from reporter import generate_output_report
from restrictions import Restrictions
from solver import synchronize_escape


DATA = Path(__file__).resolve().parent / "data"


def run_case(filename):
    graph, mission, restrictions = load_input(DATA / filename)
    return graph, mission, restrictions, synchronize_escape(graph, mission, restrictions)


class SampleTests(unittest.TestCase):
    def test_sample_input(self):
        _, _, _, result = run_case("../../input.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 20)
        self.assertEqual(result["pierre"]["delay"], 0)
        self.assertEqual(result["amelie"]["delay"], 8)
        self.assertEqual(result["pierre"]["cost"], 20)
        self.assertEqual(result["amelie"]["cost"], 12)

    def test_output_format(self):
        _, _, _, result = run_case("../../input.txt")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.txt"
            generate_output_report(result, output)
            text = output.read_text(encoding="utf-8")
        self.assertIn("=== PLAN DE ESCAPE CONFIGURADO ===", text)
        self.assertIn("Tiempo Total de la Operación: 20 minutos", text)
        self.assertIn("[RUTA DE PIERRE (Tiempo total de viaje: 20 min)]", text)
        self.assertIn("Minuto 0: Estación 1 (Origen)", text)
        self.assertIn("Minuto 8: Estación 12 (Origen - Inicia Movimiento)", text)
        self.assertIn("(Termina Transbordo a L2)", text)
        self.assertIn("Minuto 20: Estación 7 (Destino Compuerta D1)", text)
        self.assertIn("Minuto 20: Estación 8 (Destino Compuerta D2)", text)
        self.assertIn("Resultado de Sincronización: ÉXITO. Llegada simultánea en el minuto 20.", text)


class CollisionTests(unittest.TestCase):
    def test_collision_avoidance(self):
        _, _, _, result = run_case("collision.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 12)

    def test_unavoidable_collision(self):
        _, _, _, result = run_case("unavoidable_collision.txt")
        self.assertFalse(result["success"])
        self.assertIn("colisiones", result["message"])

    def test_opposite_tunnel_collision(self):
        _, _, _, result = run_case("opposite_tunnel.txt")
        self.assertFalse(result["success"])
        self.assertIn("colisiones", result["message"])

    def test_bunker_exception(self):
        _, _, _, result = run_case("bunker.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 5)


class RestrictionTests(unittest.TestCase):
    def test_closed_line(self):
        _, _, _, result = run_case("closed_line.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 4)
        # La ruta de Pierre no debe contener L1.
        self.assertFalse(any(node.edge and node.edge.line == "L1" for node in result["pierre"]["path"]))
        self.assertTrue(any(node.station == 3 for node in result["pierre"]["path"]))

    def test_closed_window(self):
        _, _, _, result = run_case("closed_window.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 11)
        self.assertEqual(result["pierre"]["delay"], 10)

    def test_always_closed_line(self):
        _, _, _, result = run_case("closed_always.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["t_max"], 4)
        self.assertFalse(any(node.edge and node.edge.line == "L1" for node in result["pierre"]["path"]))

    def test_doubled_line(self):
        _, _, _, result = run_case("doubled_line.txt")
        self.assertTrue(result["success"])
        self.assertEqual(result["pierre"]["cost"], 4)
        self.assertFalse(any(node.edge and node.edge.line == "L1" for node in result["pierre"]["path"]))

    def test_line_available_helper(self):
        restrictions = Restrictions()
        restrictions.add_closure("L1", 0, 10)
        self.assertFalse(restrictions.line_available("L1", 0, 1))
        self.assertFalse(restrictions.line_available("L1", 9, 11))
        self.assertTrue(restrictions.line_available("L1", 10, 11))
        self.assertTrue(restrictions.line_available("L2", 0, 1))

    def test_double_factor(self):
        restrictions = Restrictions()
        restrictions.add_double("L1", 3)
        self.assertEqual(restrictions.factor("L1"), 3)


class FailureTests(unittest.TestCase):
    def test_no_route(self):
        _, _, _, result = run_case("no_route.txt")
        self.assertFalse(result["success"])
        self.assertIn("No existe una ruta para Pierre", result["message"])


class ParserTests(unittest.TestCase):
    def test_rejects_unknown_station(self):
        text = (
            "2 1\n"
            "1 0\n"
            "2 0\n"
            "1 99 5 L1\n"
            "1 2 1 2\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_input(path)

    def test_rejects_unknown_restriction(self):
        text = (
            "2 1\n"
            "1 0\n"
            "2 0\n"
            "1 2 5 L1\n"
            "1 2 1 2\n"
            "PROHIBIDO L1\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_input(path)

    def test_accepts_inline_comments(self):
        text = (
            "# cabecera\n"
            "2 1\n"
            "1 0\n"
            "2 0\n"
            "1 2 5 L1  # tunel\n"
            "1 2 1 2\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text(text, encoding="utf-8")
            graph, mission, restrictions = load_input(path)
        self.assertEqual(len(graph.stations), 2)
        self.assertEqual(mission["origin_p"], 1)


if __name__ == "__main__":
    unittest.main()

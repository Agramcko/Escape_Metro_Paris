import sys
from pathlib import Path

from parser import load_input
from reporter import generate_output_report
from solver import synchronize_escape


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    base_dir = Path(__file__).resolve().parent

    input_path = Path(argv[0]) if len(argv) >= 1 else base_dir / "input.txt"
    output_path = Path(argv[1]) if len(argv) >= 2 else base_dir / "output.txt"

    try:
        graph, mission, restrictions = load_input(input_path)
        result = synchronize_escape(graph, mission, restrictions)
        generate_output_report(result, output_path)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result.get("success"):
        print(f"Plan de escape generado exitosamente en {output_path}")
    else:
        print(f"No se pudo generar el plan: {result.get('message')}")
        print(f"Detalle escrito en {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

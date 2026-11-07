def _write_person(f, title, person):
    f.write(f"[{title} (Tiempo total de viaje: {person['cost']} min)]\n")
    for minute, station, label in person["events"]:
        f.write(f"Minuto {minute}: Estación {station} ({label})\n")


def generate_output_report(result, output_filepath: str):
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write("=== PLAN DE ESCAPE CONFIGURADO ===\n")

        if not result.get("success"):
            f.write("No se pudo generar un plan de escape.\n")
            f.write(f"Motivo: {result.get('message', 'Error desconocido.')}\n")
            return

        f.write(f"Tiempo Total de la Operación: {result['t_max']} minutos\n\n")

        f.write("[PROGRAMACIÓN DE SALIDAS]\n")
        for name in ("Pierre", "Amélie"):
            person = result["pierre" if name == "Pierre" else "amelie"]
            delay = person["delay"]
            if delay > 0:
                f.write(
                    f"* {name} arranca en el minuto: {delay} "
                    f"(Debe esperar {delay} minutos en su estación de origen)\n"
                )
            else:
                f.write(f"* {name} arranca en el minuto: 0\n")

        f.write("\n")
        _write_person(f, "RUTA DE PIERRE", result["pierre"])
        f.write("\n")
        _write_person(f, "RUTA DE AMÉLIE", result["amelie"])

        f.write(
            f"\nResultado de Sincronización: ÉXITO. "
            f"Llegada simultánea en el minuto {result['t_max']}.\n"
        )

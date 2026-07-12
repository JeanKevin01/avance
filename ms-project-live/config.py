"""
Configuración del servidor MCP de control en vivo de Microsoft Project.
Las variables se leen del entorno con el prefijo MSP_.
"""
import os


class Config:
    # Minutos de trabajo por día (calendario estándar MS Project = 8h = 480 min).
    # Si tu obra usa turnos de 10h, pon MSP_HORAS_POR_DIA=10.
    horas_por_dia: float = float(os.environ.get("MSP_HORAS_POR_DIA", "8"))

    # Al conectar, ¿hacer visible la ventana de MS Project? (recomendado: sí)
    hacer_visible: bool = os.environ.get("MSP_VISIBLE", "1") != "0"

    # Ruta opcional de un proyecto a abrir automáticamente al iniciar.
    proyecto_inicial: str = os.environ.get("MSP_PROYECTO_INICIAL", "")

    @property
    def minutos_por_dia(self) -> int:
        return int(round(self.horas_por_dia * 60))


config = Config()

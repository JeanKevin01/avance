"""
Servidor MCP — Control EN VIVO de Microsoft Project desde Claude.

A diferencia del enfoque por archivos XML, este servidor controla la instancia de
Microsoft Project abierta en tu PC vía COM. Los cambios aparecen al instante en pantalla.

Uso: se configura en Claude Desktop / Claude Code (ver README).
    python server.py
"""
import sys
from typing import Optional

from fastmcp import FastMCP

from config import config
from service import ProjectService

# --- El adaptador COM sólo existe en Windows; lo importamos de forma perezosa ---
_service: Optional[ProjectService] = None


def get_service() -> ProjectService:
    global _service
    if _service is None:
        try:
            from adapters.com_adapter import ComAdapter
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "No se pudo cargar el adaptador COM. ¿Estás en Windows con pywin32 "
                f"instalado (pip install pywin32) y Microsoft Project? Detalle: {e}"
            )
        adapter = ComAdapter()
        _service = ProjectService(adapter, minutos_por_dia=config.minutos_por_dia)
    if not _service.a.is_connected():
        _service.a.connect(visible=config.hacer_visible)
        if config.proyecto_inicial:
            try:
                _service.a.open_file(config.proyecto_inicial)
            except Exception:
                pass
    return _service


mcp = FastMCP(
    name="Microsoft Project EN VIVO",
    instructions="""
Controla Microsoft Project EN VIVO desde Claude vía automatización COM (Windows).

Los cambios se aplican inmediatamente sobre el proyecto abierto en pantalla.
Flujo típico:
  1. 'estado_conexion' para verificar que MS Project está conectado.
  2. 'listar_tareas' para ver el cronograma actual (cada tarea tiene un ID).
  3. Crear/editar con 'crear_tarea', 'crear_dependencia', 'asignar_recurso', etc.
  4. 'guardar' para persistir en el archivo .mpp.

Contexto: obras civiles (presas, rellenos, excavación, bypass). Duraciones en días.
Los IDs de tarea corresponden a la columna 'Id' que ves en la vista Diagrama de Gantt.
Después de crear varias tareas, vuelve a 'listar_tareas' para confirmar los IDs antes
de vincularlas.
""",
    version="1.0.0",
)


# ------------------------------------------------------------------ #
#  Conexión y archivo                                                 #
# ------------------------------------------------------------------ #
@mcp.tool(description="Verifica si Claude está conectado a Microsoft Project y qué proyecto está activo.")
def estado_conexion() -> dict:
    try:
        return get_service().estado()
    except Exception as e:
        return {"conectado": False, "error": str(e)}


@mcp.tool(description="Se conecta a la instancia de Microsoft Project abierta en el PC (o abre una nueva).")
def conectar() -> dict:
    return get_service().conectar(visible=config.hacer_visible)


@mcp.tool(description="Abre un archivo .mpp de Microsoft Project. Parámetro: ruta completa al archivo.")
def abrir_proyecto(ruta: str) -> dict:
    return get_service().abrir_proyecto(ruta)


@mcp.tool(description="Crea un proyecto nuevo y vacío en Microsoft Project.")
def crear_proyecto_nuevo() -> dict:
    return get_service().crear_proyecto_nuevo()


@mcp.tool(description="Guarda el proyecto activo. Si se indica 'ruta', hace Guardar como en esa ubicación.")
def guardar(ruta: Optional[str] = None) -> dict:
    return get_service().guardar(ruta)


@mcp.tool(description="Devuelve un resumen del proyecto: nombre, fechas, total de tareas, ruta crítica y avance global.")
def resumen_proyecto() -> dict:
    return get_service().resumen()


# ------------------------------------------------------------------ #
#  Lectura de tareas                                                  #
# ------------------------------------------------------------------ #
@mcp.tool(description="Lista todas las tareas del cronograma con ID, nombre, duración, fechas, avance y predecesores. 'solo_activas' excluye resúmenes y tareas completas.")
def listar_tareas(solo_activas: bool = False) -> list[dict]:
    return get_service().listar_tareas(solo_activas)


@mcp.tool(description="Devuelve las tareas de la ruta crítica (las que si se atrasan retrasan el proyecto completo).")
def ruta_critica() -> list[dict]:
    return get_service().ruta_critica()


# ------------------------------------------------------------------ #
#  Escritura de tareas                                               #
# ------------------------------------------------------------------ #
@mcp.tool(description="Crea una tarea nueva. duracion_dias en días hábiles. 'antes_de' = ID de la tarea ante la cual insertar (opcional). 'es_hito' para hitos (duración 0).")
def crear_tarea(nombre: str, duracion_dias: float = 1.0, antes_de: Optional[int] = None,
                es_hito: bool = False, notas: str = "") -> dict:
    return get_service().crear_tarea(nombre, duracion_dias, antes_de, es_hito, notas)


@mcp.tool(description="Actualiza una tarea existente por su ID. Solo cambia los campos indicados (nombre, duracion_dias, pct_completado, fecha_inicio 'YYYY-MM-DD', notas).")
def actualizar_tarea(tarea_id: int, nombre: Optional[str] = None,
                     duracion_dias: Optional[float] = None,
                     pct_completado: Optional[float] = None,
                     fecha_inicio: Optional[str] = None,
                     notas: Optional[str] = None) -> dict:
    return get_service().actualizar_tarea(tarea_id, nombre, duracion_dias,
                                          pct_completado, fecha_inicio, notas)


@mcp.tool(description="Elimina una tarea por su ID.")
def eliminar_tarea(tarea_id: int) -> dict:
    return get_service().eliminar_tarea(tarea_id)


@mcp.tool(description="Establece el porcentaje de avance (0-100) de una tarea por su ID.")
def establecer_avance(tarea_id: int, pct: float) -> dict:
    return get_service().establecer_avance(tarea_id, pct)


@mcp.tool(description="Crea un hito (milestone) con duración cero. 'antes_de' = ID ante el cual insertar (opcional).")
def crear_hito(nombre: str, antes_de: Optional[int] = None) -> dict:
    return get_service().crear_hito(nombre, antes_de)


@mcp.tool(description="Convierte una tarea en subtarea (aplica sangría). La tarea inmediatamente superior se vuelve tarea resumen/fase.")
def sangrar_tarea(tarea_id: int) -> dict:
    return get_service().sangrar(tarea_id)


@mcp.tool(description="Anula la sangría de una tarea (la sube un nivel en la EDT).")
def anular_sangria(tarea_id: int) -> dict:
    return get_service().anular_sangria(tarea_id)


# ------------------------------------------------------------------ #
#  Dependencias                                                       #
# ------------------------------------------------------------------ #
@mcp.tool(description="Crea una dependencia entre dos tareas por sus IDs. tipo: FS (fin-inicio, el más común), SS, FF o SF. retraso_dias puede ser negativo (adelanto).")
def crear_dependencia(predecesora_id: int, sucesora_id: int, tipo: str = "FS",
                      retraso_dias: float = 0) -> dict:
    return get_service().crear_dependencia(predecesora_id, sucesora_id, tipo, retraso_dias)


# ------------------------------------------------------------------ #
#  Recursos                                                          #
# ------------------------------------------------------------------ #
@mcp.tool(description="Lista los recursos del proyecto (personal, equipos).")
def listar_recursos() -> list[dict]:
    return get_service().listar_recursos()


@mcp.tool(description="Crea un recurso nuevo (persona o equipo).")
def crear_recurso(nombre: str) -> dict:
    return get_service().crear_recurso(nombre)


@mcp.tool(description="Asigna un recurso a una tarea. Si el recurso no existe, lo crea. unidades 1.0 = 100%.")
def asignar_recurso(tarea_id: int, nombre_recurso: str, unidades: float = 1.0) -> dict:
    return get_service().asignar_recurso(tarea_id, nombre_recurso, unidades)


if __name__ == "__main__":
    print("[MS-Project-LIVE] Servidor MCP iniciado (transporte stdio).", file=sys.stderr)
    print("[MS-Project-LIVE] Se conectará a Microsoft Project en la primera herramienta que uses.", file=sys.stderr)
    mcp.run()

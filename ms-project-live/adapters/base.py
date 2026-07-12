"""
Contrato del adaptador de Microsoft Project.

Toda la lógica de negocio (service.py) trabaja SÓLO contra esta interfaz.
Esto permite:
  - ComAdapter    -> control real de MS Project vía COM en Windows.
  - FakeAdapter   -> implementación en memoria para pruebas en cualquier SO.

Un "raw task" es un diccionario con estas claves normalizadas:
  id: int            -> ID visible en la vista Gantt (posición en el esquema)
  uid: int           -> UniqueID estable (no cambia al reordenar)
  name: str
  duration_min: int  -> duración en MINUTOS (MS Project trabaja internamente en minutos)
  start: str | None  -> ISO 8601 o None
  finish: str | None
  pct: float         -> porcentaje completado 0-100
  predecessors: str  -> texto de predecesores tal como lo muestra MS Project (ej. "2FS")
  outline_level: int -> nivel en la EDT (1 = primer nivel)
  milestone: bool
  summary: bool      -> True si es tarea resumen (fase)
  notes: str
  critical: bool     -> True si está en la ruta crítica
"""
from abc import ABC, abstractmethod
from typing import Optional


# Constantes de tipo de vínculo (PjTaskLinkType) — independientes del idioma de MS Project.
LINK_FF = 0  # Fin a Fin
LINK_FS = 1  # Fin a Inicio (el más común)
LINK_SF = 2  # Inicio a Fin
LINK_SS = 3  # Inicio a Inicio

LINK_TYPES = {"FF": LINK_FF, "FS": LINK_FS, "SF": LINK_SF, "SS": LINK_SS}


class ProjectAdapter(ABC):
    # --- Conexión y archivo -------------------------------------------------
    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def connect(self, visible: bool = True) -> None: ...

    @abstractmethod
    def open_file(self, path: str) -> None: ...

    @abstractmethod
    def new_project(self) -> None: ...

    @abstractmethod
    def save(self) -> None: ...

    @abstractmethod
    def save_as(self, path: str) -> None: ...

    @abstractmethod
    def project_info(self) -> dict: ...

    # --- Tareas -------------------------------------------------------------
    @abstractmethod
    def get_tasks(self) -> list[dict]: ...

    @abstractmethod
    def add_task(self, name: str, before_id: Optional[int] = None) -> int:
        """Crea una tarea y devuelve su ID."""

    @abstractmethod
    def set_task_field(self, task_id: int, field: str, value) -> None: ...

    @abstractmethod
    def delete_task(self, task_id: int) -> None: ...

    @abstractmethod
    def outline_indent(self, task_id: int) -> None: ...

    @abstractmethod
    def outline_outdent(self, task_id: int) -> None: ...

    @abstractmethod
    def link(self, pred_id: int, succ_id: int, link_type: int, lag_minutes: int) -> None: ...

    # --- Recursos -----------------------------------------------------------
    @abstractmethod
    def get_resources(self) -> list[dict]: ...

    @abstractmethod
    def add_resource(self, name: str) -> int:
        """Crea un recurso y devuelve su ID."""

    @abstractmethod
    def assign(self, task_id: int, resource_id: int, units: float) -> None: ...

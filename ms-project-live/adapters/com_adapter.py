"""
Adaptador COM real: controla una instancia VIVA de Microsoft Project en Windows.

Requiere:
  - Windows
  - Microsoft Project (Desktop / Professional) instalado
  - pip install pywin32

Estrategia de conexión:
  1. Intenta ADJUNTARSE a un MS Project ya abierto (GetActiveObject) -> así controla
     el proyecto que el usuario ya tiene en pantalla.
  2. Si no hay ninguno, lanza una instancia nueva (Dispatch).

Todo el acceso a win32com está aislado aquí. Si algún método falla por una diferencia
de versión de MS Project, el error se reporta claro y sólo hay que ajustar este archivo.
"""
from datetime import datetime
from typing import Optional

from .base import ProjectAdapter


def _to_iso(v) -> Optional[str]:
    if v is None:
        return None
    try:
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        s = str(v)
        if not s or "NA" in s:
            return None
        return s


def _parse_date(value):
    """Acepta 'YYYY-MM-DD' o datetime y devuelve datetime para COM."""
    if isinstance(value, datetime):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d")


class ComAdapter(ProjectAdapter):
    def __init__(self):
        self._app = None

    # --- Conexión -----------------------------------------------------------
    def is_connected(self) -> bool:
        if self._app is None:
            return False
        try:
            _ = self._app.Name
            return True
        except Exception:
            return False

    def connect(self, visible: bool = True) -> None:
        import win32com.client as wc

        app = None
        try:
            # Adjuntarse a un MS Project que ya esté abierto.
            app = wc.GetActiveObject("MSProject.Application")
        except Exception:
            # Ninguno abierto: lanzar una instancia nueva.
            app = wc.Dispatch("MSProject.Application")
        try:
            app.Visible = visible
        except Exception:
            pass
        self._app = app

    def _proj(self):
        """Devuelve el proyecto activo o lanza un error claro."""
        if not self.is_connected():
            raise RuntimeError(
                "No hay conexión con Microsoft Project. Llama a 'conectar' primero, "
                "o abre MS Project."
            )
        try:
            if self._app.Projects.Count == 0:
                raise RuntimeError(
                    "Microsoft Project está abierto pero no hay ningún proyecto. "
                    "Usa 'abrir_proyecto' o 'crear_proyecto_nuevo'."
                )
        except RuntimeError:
            raise
        except Exception:
            pass
        return self._app.ActiveProject

    def open_file(self, path: str) -> None:
        if not self.is_connected():
            self.connect()
        # Argumentos posicionales: el late binding (Dispatch) no admite argumentos por nombre.
        self._app.FileOpenEx(path)

    def new_project(self) -> None:
        if not self.is_connected():
            self.connect()
        self._app.Projects.Add()

    def save(self) -> None:
        self._proj()  # valida que haya proyecto
        self._app.FileSave()

    def save_as(self, path: str) -> None:
        self._proj()
        self._app.FileSaveAs(path)

    def project_info(self) -> dict:
        p = self._proj()
        return {
            "nombre": str(p.Name),
            "inicio": _to_iso(p.ProjectStart),
            "fin": _to_iso(p.ProjectFinish),
            "fecha_estado": _to_iso(getattr(p, "StatusDate", None)),
            "proyectos_abiertos": int(self._app.Projects.Count),
        }

    # --- Localizar tarea por ID (saltando filas vacías) ---------------------
    def _find_task(self, task_id: int):
        for t in self._proj().Tasks:
            if t is None:
                continue
            try:
                if int(t.ID) == int(task_id):
                    return t
            except Exception:
                continue
        raise RuntimeError(f"No se encontró la tarea con ID={task_id}.")

    # --- Tareas -------------------------------------------------------------
    def get_tasks(self) -> list[dict]:
        out = []
        for t in self._proj().Tasks:
            if t is None:
                continue
            try:
                out.append({
                    "id": int(t.ID),
                    "uid": int(t.UniqueID),
                    "name": str(t.Name or ""),
                    "duration_min": int(t.Duration or 0),
                    "start": _to_iso(t.Start),
                    "finish": _to_iso(t.Finish),
                    "pct": float(t.PercentComplete or 0),
                    "predecessors": str(t.Predecessors or ""),
                    "outline_level": int(t.OutlineLevel or 1),
                    "milestone": bool(t.Milestone),
                    "summary": bool(t.Summary),
                    "notes": str(t.Notes or ""),
                    "critical": bool(t.Critical),
                })
            except Exception:
                # Fila problemática: la omitimos en vez de romper toda la lectura.
                continue
        return out

    def add_task(self, name: str, before_id: Optional[int] = None) -> int:
        proj = self._proj()
        if before_id:
            before = self._find_task(before_id)
            task = proj.Tasks.Add(name, before.ID)
        else:
            task = proj.Tasks.Add(name)
        return int(task.ID)

    def set_task_field(self, task_id: int, field: str, value) -> None:
        t = self._find_task(task_id)
        if field == "Name":
            t.Name = str(value)
        elif field == "Duration":
            t.Duration = int(value)
        elif field == "PercentComplete":
            t.PercentComplete = int(value)
        elif field == "Notes":
            t.Notes = str(value)
        elif field == "Milestone":
            t.Milestone = bool(value)
        elif field == "Start":
            t.Start = _parse_date(value)
        elif field == "Finish":
            t.Finish = _parse_date(value)
        else:
            raise RuntimeError(f"Campo no soportado: {field}")

    def delete_task(self, task_id: int) -> None:
        self._find_task(task_id).Delete()

    def outline_indent(self, task_id: int) -> None:
        self._find_task(task_id).OutlineIndent()

    def outline_outdent(self, task_id: int) -> None:
        self._find_task(task_id).OutlineOutdent()

    def link(self, pred_id: int, succ_id: int, link_type: int, lag_minutes: int) -> None:
        proj = self._proj()
        pred = self._find_task(pred_id)
        succ = self._find_task(succ_id)
        # Método principal: TaskDependencies.Add con tipo numérico (independiente del idioma).
        try:
            dep = proj.TaskDependencies.Add(pred, succ)
            dep.Type = link_type
            if lag_minutes:
                dep.Lag = lag_minutes
            return
        except Exception:
            pass
        # Respaldo: campo de texto Predecessors (formato "2FS").
        code = {0: "FF", 1: "FS", 2: "SF", 3: "SS"}.get(link_type, "FS")
        current = str(succ.Predecessors or "")
        token = f"{pred_id}{code}"
        succ.Predecessors = token if not current else f"{current},{token}"

    # --- Recursos -----------------------------------------------------------
    def get_resources(self) -> list[dict]:
        out = []
        for r in self._proj().Resources:
            if r is None:
                continue
            try:
                out.append({
                    "id": int(r.ID),
                    "uid": int(r.UniqueID),
                    "name": str(r.Name or ""),
                    "max_units": float(r.MaxUnits or 0),
                })
            except Exception:
                continue
        return out

    def add_resource(self, name: str) -> int:
        res = self._proj().Resources.Add(name)
        return int(res.ID)

    def assign(self, task_id: int, resource_id: int, units: float) -> None:
        task = self._find_task(task_id)
        # Posicional: Assignments.Add(TaskID, ResourceID, Units)
        asn = task.Assignments.Add(task.ID, resource_id)
        if units:
            try:
                asn.Units = units
            except Exception:
                pass

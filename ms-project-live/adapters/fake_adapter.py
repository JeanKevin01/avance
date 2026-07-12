"""
Adaptador falso en memoria — replica el comportamiento de MS Project lo suficiente
para probar toda la lógica de service.py en cualquier sistema operativo (sin Windows,
sin COM, sin MS Project). Lo usan los tests automatizados.
"""
from typing import Optional

from .base import ProjectAdapter


_TYPE_CODE = {0: "FF", 1: "FS", 2: "SF", 3: "SS"}


class FakeAdapter(ProjectAdapter):
    def __init__(self):
        self._connected = False
        self._project_name = ""
        self._has_project = False
        self._tasks: list[dict] = []
        self._resources: list[dict] = []
        self._next_uid = 1
        self._next_res_uid = 1
        self.saved_path: Optional[str] = None
        self.save_count = 0

    # --- Conexión -----------------------------------------------------------
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, visible: bool = True) -> None:
        self._connected = True

    def open_file(self, path: str) -> None:
        self._connected = True
        self._has_project = True
        self._project_name = path.replace("\\", "/").split("/")[-1]

    def new_project(self) -> None:
        self._connected = True
        self._has_project = True
        self._project_name = "Proyecto1"
        self._tasks = []
        self._resources = []

    def _require(self):
        if not self._connected:
            raise RuntimeError("No conectado.")
        if not self._has_project:
            raise RuntimeError("No hay proyecto abierto.")

    def save(self) -> None:
        self._require()
        self.save_count += 1

    def save_as(self, path: str) -> None:
        self._require()
        self.saved_path = path
        self.save_count += 1

    def project_info(self) -> dict:
        self._require()
        starts = [t["start"] for t in self._tasks if t["start"]]
        finishes = [t["finish"] for t in self._tasks if t["finish"]]
        return {
            "nombre": self._project_name,
            "inicio": min(starts) if starts else None,
            "fin": max(finishes) if finishes else None,
            "fecha_estado": None,
            "proyectos_abiertos": 1,
        }

    # --- Tareas -------------------------------------------------------------
    def _find(self, task_id: int) -> dict:
        for t in self._tasks:
            if t["id"] == int(task_id):
                return t
        raise RuntimeError(f"No se encontró la tarea con ID={task_id}.")

    def _renumber(self):
        for i, t in enumerate(self._tasks, start=1):
            t["id"] = i

    def get_tasks(self) -> list[dict]:
        self._require()
        result = []
        for t in self._tasks:
            preds = ",".join(
                f"{p}{_TYPE_CODE.get(ty, 'FS')}" for (p, ty, _lag) in t["deps"]
            )
            result.append({
                "id": t["id"],
                "uid": t["uid"],
                "name": t["name"],
                "duration_min": t["duration_min"],
                "start": t["start"],
                "finish": t["finish"],
                "pct": t["pct"],
                "predecessors": preds,
                "outline_level": t["outline_level"],
                "milestone": t["milestone"],
                "summary": t["summary"],
                "notes": t["notes"],
                "critical": t["critical"],
            })
        return result

    def add_task(self, name: str, before_id: Optional[int] = None) -> int:
        self._require()
        task = {
            "uid": self._next_uid, "name": name, "duration_min": 480,
            "start": None, "finish": None, "pct": 0.0, "deps": [],
            "outline_level": 1, "milestone": False, "summary": False,
            "notes": "", "critical": False,
        }
        self._next_uid += 1
        if before_id:
            idx = next((i for i, t in enumerate(self._tasks) if t["id"] == before_id), len(self._tasks))
            self._tasks.insert(idx, task)
        else:
            self._tasks.append(task)
        self._renumber()
        return task["id"]

    def set_task_field(self, task_id: int, field: str, value) -> None:
        t = self._find(task_id)
        mapping = {
            "Name": "name", "Duration": "duration_min", "PercentComplete": "pct",
            "Notes": "notes", "Milestone": "milestone", "Start": "start", "Finish": "finish",
        }
        if field not in mapping:
            raise RuntimeError(f"Campo no soportado: {field}")
        key = mapping[field]
        if key == "duration_min":
            value = int(value)
        elif key == "pct":
            value = float(value)
        elif key == "milestone":
            value = bool(value)
        t[key] = value

    def delete_task(self, task_id: int) -> None:
        t = self._find(task_id)
        self._tasks.remove(t)
        self._renumber()

    def outline_indent(self, task_id: int) -> None:
        t = self._find(task_id)
        t["outline_level"] += 1
        idx = self._tasks.index(t)
        if idx > 0:
            self._tasks[idx - 1]["summary"] = True

    def outline_outdent(self, task_id: int) -> None:
        t = self._find(task_id)
        t["outline_level"] = max(1, t["outline_level"] - 1)

    def link(self, pred_id: int, succ_id: int, link_type: int, lag_minutes: int) -> None:
        self._find(pred_id)
        succ = self._find(succ_id)
        succ["deps"].append((int(pred_id), int(link_type), int(lag_minutes)))

    # --- Recursos -----------------------------------------------------------
    def get_resources(self) -> list[dict]:
        self._require()
        return [dict(r) for r in self._resources]

    def add_resource(self, name: str) -> int:
        self._require()
        res = {"id": len(self._resources) + 1, "uid": self._next_res_uid,
               "name": name, "max_units": 1.0, "assignments": []}
        self._next_res_uid += 1
        self._resources.append(res)
        return res["id"]

    def assign(self, task_id: int, resource_id: int, units: float) -> None:
        self._find(task_id)
        res = next((r for r in self._resources if r["id"] == resource_id), None)
        if res is None:
            raise RuntimeError(f"No existe el recurso ID={resource_id}.")
        res["assignments"].append({"task_id": task_id, "units": units})

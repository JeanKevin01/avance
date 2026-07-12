"""
Lógica de negocio del control de Microsoft Project.

Trabaja contra la interfaz ProjectAdapter, así que es idéntica para el control real
(COM en Windows) y para las pruebas (adaptador falso). Aquí viven:
  - conversión de días <-> minutos según el calendario,
  - construcción de dependencias con tipo y retraso,
  - validaciones y formateo amable en español.
"""
from typing import Optional

from adapters.base import ProjectAdapter, LINK_TYPES


class ProjectService:
    def __init__(self, adapter: ProjectAdapter, minutos_por_dia: int = 480):
        self.a = adapter
        self.mpd = minutos_por_dia

    # --- Conversión ---------------------------------------------------------
    def _dias(self, minutos: int) -> float:
        return round(minutos / self.mpd, 2)

    def _minutos(self, dias: float) -> int:
        return int(round(dias * self.mpd))

    def _fmt(self, raw: dict) -> dict:
        return {
            "id": raw["id"],
            "uid": raw["uid"],
            "nombre": raw["name"],
            "duracion_dias": self._dias(raw["duration_min"]),
            "inicio": raw["start"],
            "fin": raw["finish"],
            "pct_completado": raw["pct"],
            "predecesores": raw["predecessors"],
            "nivel_edt": raw["outline_level"],
            "es_hito": raw["milestone"],
            "es_resumen": raw["summary"],
            "en_ruta_critica": raw["critical"],
            "notas": raw["notes"],
        }

    def _raw(self, task_id: int) -> dict:
        for t in self.a.get_tasks():
            if t["id"] == int(task_id):
                return t
        raise RuntimeError(f"No se encontró la tarea con ID={task_id}.")

    # --- Conexión y archivo -------------------------------------------------
    def estado(self) -> dict:
        if not self.a.is_connected():
            return {"conectado": False, "mensaje": "No conectado a Microsoft Project."}
        info = self.a.project_info()
        return {"conectado": True, "proyecto": info,
                "mensaje": f"Conectado. Proyecto activo: '{info['nombre']}'."}

    def conectar(self, visible: bool = True) -> dict:
        self.a.connect(visible=visible)
        return {"conectado": True, "mensaje": "Conectado a Microsoft Project."}

    def abrir_proyecto(self, ruta: str) -> dict:
        self.a.open_file(ruta)
        return {"mensaje": f"Proyecto abierto: {ruta}", "proyecto": self.a.project_info()}

    def crear_proyecto_nuevo(self) -> dict:
        self.a.new_project()
        return {"mensaje": "Proyecto nuevo creado en Microsoft Project."}

    def guardar(self, ruta: Optional[str] = None) -> dict:
        if ruta:
            self.a.save_as(ruta)
            return {"mensaje": f"Proyecto guardado en: {ruta}"}
        self.a.save()
        return {"mensaje": "Proyecto guardado."}

    def resumen(self) -> dict:
        info = self.a.project_info()
        tasks = self.a.get_tasks()
        activas = [t for t in tasks if not t["summary"]]
        criticas = [t for t in activas if t["critical"]]
        completas = [t for t in activas if t["pct"] >= 100]
        pct_global = round(sum(t["pct"] for t in activas) / len(activas), 1) if activas else 0.0
        return {
            "proyecto": info["nombre"],
            "inicio": info["inicio"],
            "fin": info["fin"],
            "total_tareas": len(activas),
            "tareas_completas": len(completas),
            "tareas_criticas": len(criticas),
            "avance_global_pct": pct_global,
            "total_recursos": len(self.a.get_resources()),
        }

    # --- Tareas -------------------------------------------------------------
    def listar_tareas(self, solo_activas: bool = False) -> list[dict]:
        tasks = [self._fmt(t) for t in self.a.get_tasks()]
        if solo_activas:
            tasks = [t for t in tasks if not t["es_resumen"] and t["pct_completado"] < 100]
        return tasks

    def crear_tarea(self, nombre: str, duracion_dias: float = 1.0,
                    antes_de: Optional[int] = None, es_hito: bool = False,
                    notas: str = "") -> dict:
        tid = self.a.add_task(nombre, antes_de)
        if es_hito:
            self.a.set_task_field(tid, "Milestone", True)
            self.a.set_task_field(tid, "Duration", 0)
        else:
            self.a.set_task_field(tid, "Duration", self._minutos(duracion_dias))
        if notas:
            self.a.set_task_field(tid, "Notes", notas)
        return {"id": tid, "nombre": nombre,
                "mensaje": f"Tarea '{nombre}' creada con ID={tid}."}

    def actualizar_tarea(self, tarea_id: int, nombre: Optional[str] = None,
                         duracion_dias: Optional[float] = None,
                         pct_completado: Optional[float] = None,
                         fecha_inicio: Optional[str] = None,
                         notas: Optional[str] = None) -> dict:
        cambios = []
        if nombre is not None:
            self.a.set_task_field(tarea_id, "Name", nombre); cambios.append("nombre")
        if duracion_dias is not None:
            self.a.set_task_field(tarea_id, "Duration", self._minutos(duracion_dias)); cambios.append("duración")
        if pct_completado is not None:
            self.a.set_task_field(tarea_id, "PercentComplete", pct_completado); cambios.append("avance")
        if fecha_inicio is not None:
            self.a.set_task_field(tarea_id, "Start", fecha_inicio); cambios.append("inicio")
        if notas is not None:
            self.a.set_task_field(tarea_id, "Notes", notas); cambios.append("notas")
        if not cambios:
            return {"mensaje": "No se indicó ningún cambio."}
        return {"id": tarea_id, "mensaje": f"Tarea ID={tarea_id} actualizada ({', '.join(cambios)})."}

    def eliminar_tarea(self, tarea_id: int) -> dict:
        self.a.delete_task(tarea_id)
        return {"mensaje": f"Tarea ID={tarea_id} eliminada."}

    def establecer_avance(self, tarea_id: int, pct: float) -> dict:
        pct = max(0.0, min(100.0, float(pct)))
        self.a.set_task_field(tarea_id, "PercentComplete", pct)
        return {"id": tarea_id, "pct_completado": pct,
                "mensaje": f"Tarea ID={tarea_id} al {pct:.0f}%."}

    def crear_hito(self, nombre: str, antes_de: Optional[int] = None) -> dict:
        return self.crear_tarea(nombre, duracion_dias=0, antes_de=antes_de, es_hito=True)

    def sangrar(self, tarea_id: int) -> dict:
        self.a.outline_indent(tarea_id)
        return {"mensaje": f"Tarea ID={tarea_id} convertida en subtarea (sangría aplicada)."}

    def anular_sangria(self, tarea_id: int) -> dict:
        self.a.outline_outdent(tarea_id)
        return {"mensaje": f"Sangría anulada en tarea ID={tarea_id}."}

    # --- Dependencias -------------------------------------------------------
    def crear_dependencia(self, predecesora_id: int, sucesora_id: int,
                          tipo: str = "FS", retraso_dias: float = 0) -> dict:
        tipo = tipo.upper()
        if tipo not in LINK_TYPES:
            raise RuntimeError(f"Tipo de vínculo inválido: {tipo}. Usa FS, SS, FF o SF.")
        lag_min = self._minutos(retraso_dias)
        self.a.link(predecesora_id, sucesora_id, LINK_TYPES[tipo], lag_min)
        return {
            "mensaje": f"Dependencia creada: tarea {predecesora_id} -> tarea {sucesora_id} "
                       f"({tipo}{f', retraso {retraso_dias}d' if retraso_dias else ''})."
        }

    # --- Recursos -----------------------------------------------------------
    def listar_recursos(self) -> list[dict]:
        return [{"id": r["id"], "nombre": r["name"], "max_unidades": r["max_units"]}
                for r in self.a.get_resources()]

    def crear_recurso(self, nombre: str) -> dict:
        rid = self.a.add_resource(nombre)
        return {"id": rid, "mensaje": f"Recurso '{nombre}' creado con ID={rid}."}

    def asignar_recurso(self, tarea_id: int, nombre_recurso: str, unidades: float = 1.0) -> dict:
        existente = next((r for r in self.a.get_resources()
                          if r["name"].lower() == nombre_recurso.lower()), None)
        rid = existente["id"] if existente else self.a.add_resource(nombre_recurso)
        self.a.assign(tarea_id, rid, unidades)
        return {"mensaje": f"Recurso '{nombre_recurso}' asignado a la tarea ID={tarea_id}."}

    # --- Ruta crítica -------------------------------------------------------
    def ruta_critica(self) -> list[dict]:
        return [self._fmt(t) for t in self.a.get_tasks()
                if t["critical"] and not t["summary"]]

"""
Pruebas de la lógica de negocio (service.py) usando el adaptador falso en memoria.
Se ejecutan en cualquier SO (no requieren Windows ni MS Project):

    cd ms-project-live
    python -m pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from adapters.fake_adapter import FakeAdapter
from adapters.base import LINK_FS, LINK_SS
from service import ProjectService


def nuevo_servicio(minutos_por_dia=480):
    a = FakeAdapter()
    svc = ProjectService(a, minutos_por_dia=minutos_por_dia)
    svc.conectar()
    svc.crear_proyecto_nuevo()
    return svc


def test_estado_sin_conexion():
    svc = ProjectService(FakeAdapter())
    assert svc.estado()["conectado"] is False


def test_crear_proyecto_y_conectar():
    svc = nuevo_servicio()
    assert svc.estado()["conectado"] is True


def test_crear_tarea_duracion_en_dias():
    svc = nuevo_servicio()  # 480 min/día
    r = svc.crear_tarea("Excavación", duracion_dias=5)
    assert r["id"] == 1
    t = svc.listar_tareas()[0]
    assert t["nombre"] == "Excavación"
    assert t["duracion_dias"] == 5.0  # 5*480=2400 min -> 5 días


def test_calendario_de_10_horas():
    svc = nuevo_servicio(minutos_por_dia=600)  # turnos de 10h
    svc.crear_tarea("Relleno", duracion_dias=3)
    # 3 días * 600 = 1800 min, y de vuelta 1800/600 = 3 días
    assert svc.listar_tareas()[0]["duracion_dias"] == 3.0


def test_hito_tiene_duracion_cero():
    svc = nuevo_servicio()
    svc.crear_hito("Entrega Final")
    t = svc.listar_tareas()[0]
    assert t["es_hito"] is True
    assert t["duracion_dias"] == 0.0


def test_dependencia_fs_registrada():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 2)
    svc.crear_tarea("B", 3)
    svc.crear_dependencia(1, 2, tipo="FS")
    tareas = {t["id"]: t for t in svc.listar_tareas()}
    assert "1FS" in tareas[2]["predecesores"]


def test_dependencia_ss():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 2)
    svc.crear_tarea("B", 3)
    svc.crear_dependencia(1, 2, tipo="SS")
    assert "1SS" in {t["id"]: t for t in svc.listar_tareas()}[2]["predecesores"]


def test_dependencia_tipo_invalido():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 1)
    svc.crear_tarea("B", 1)
    with pytest.raises(RuntimeError):
        svc.crear_dependencia(1, 2, tipo="XX")


def test_actualizar_avance():
    svc = nuevo_servicio()
    svc.crear_tarea("Compactación", 4)
    svc.establecer_avance(1, 75)
    assert svc.listar_tareas()[0]["pct_completado"] == 75.0


def test_avance_se_limita_a_100():
    svc = nuevo_servicio()
    svc.crear_tarea("X", 1)
    r = svc.establecer_avance(1, 150)
    assert r["pct_completado"] == 100.0


def test_actualizar_varios_campos():
    svc = nuevo_servicio()
    svc.crear_tarea("Original", 2)
    r = svc.actualizar_tarea(1, nombre="Renombrada", duracion_dias=8, pct_completado=50)
    assert "nombre" in r["mensaje"] and "duración" in r["mensaje"]
    t = svc.listar_tareas()[0]
    assert t["nombre"] == "Renombrada"
    assert t["duracion_dias"] == 8.0
    assert t["pct_completado"] == 50.0


def test_eliminar_tarea_renumera():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 1)
    svc.crear_tarea("B", 1)
    svc.crear_tarea("C", 1)
    svc.eliminar_tarea(2)  # elimina B
    ids = [t["id"] for t in svc.listar_tareas()]
    nombres = [t["nombre"] for t in svc.listar_tareas()]
    assert ids == [1, 2]
    assert nombres == ["A", "C"]


def test_insertar_antes_de():
    svc = nuevo_servicio()
    svc.crear_tarea("Primera", 1)
    svc.crear_tarea("Tercera", 1)
    svc.crear_tarea("Segunda", 1, antes_de=2)  # insertar antes de "Tercera"
    nombres = [t["nombre"] for t in svc.listar_tareas()]
    assert nombres == ["Primera", "Segunda", "Tercera"]


def test_sangria_crea_resumen():
    svc = nuevo_servicio()
    svc.crear_tarea("Fase", 5)
    svc.crear_tarea("Subtarea", 2)
    svc.sangrar(2)
    tareas = {t["id"]: t for t in svc.listar_tareas()}
    assert tareas[1]["es_resumen"] is True
    assert tareas[2]["nivel_edt"] == 2


def test_asignar_recurso_lo_crea_si_no_existe():
    svc = nuevo_servicio()
    svc.crear_tarea("Excavación", 5)
    svc.asignar_recurso(1, "Cuadrilla Civil")
    recursos = svc.listar_recursos()
    assert len(recursos) == 1
    assert recursos[0]["nombre"] == "Cuadrilla Civil"


def test_asignar_recurso_existente_no_duplica():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 1)
    svc.crear_tarea("B", 1)
    svc.crear_recurso("Excavadora")
    svc.asignar_recurso(1, "Excavadora")
    svc.asignar_recurso(2, "excavadora")  # mismo recurso, distinta capitalización
    assert len(svc.listar_recursos()) == 1


def test_resumen_proyecto():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 5)
    svc.crear_tarea("B", 3)
    svc.establecer_avance(1, 100)
    svc.establecer_avance(2, 50)
    r = svc.resumen()
    assert r["total_tareas"] == 2
    assert r["tareas_completas"] == 1
    assert r["avance_global_pct"] == 75.0


def test_solo_activas_filtra_completas():
    svc = nuevo_servicio()
    svc.crear_tarea("Hecha", 1)
    svc.crear_tarea("Pendiente", 1)
    svc.establecer_avance(1, 100)
    activas = svc.listar_tareas(solo_activas=True)
    assert len(activas) == 1
    assert activas[0]["nombre"] == "Pendiente"


def test_guardar_como():
    svc = nuevo_servicio()
    svc.crear_tarea("A", 1)
    svc.guardar(ruta="C:/obra/proyecto.mpp")
    assert svc.a.saved_path == "C:/obra/proyecto.mpp"

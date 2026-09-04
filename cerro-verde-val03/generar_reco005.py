# -*- coding: utf-8 -*-
"""
Llena el registro RE-CO-005 "Control de Trabajo Remoto" (Kampfer, Version 01,
19/07/2021) a partir de la bitacora de actividades en formato JSON.

La geometria de la tabla (posiciones de columnas, filas y cabecera) se tomo del
PDF original del formato, de modo que el documento generado es visualmente
identico al formato vigente; solo cambia el contenido.
"""

import json
import os

from reportlab.lib.colors import Color, black, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BASE = os.path.dirname(os.path.abspath(__file__))

# --- Geometria tomada del formato original (puntos PDF, origen abajo-izq.) ---
PAGE_W, PAGE_H = 595.2, 841.68

BANNER = (15.8, 742.8, 557.6, 55.5)          # x, y, ancho, alto de la cabecera

INFO_TOP, INFO_BOTTOM = 735.4, 698.6         # bloque MES / COLABORADOR / GERENCIA
INFO_SPLIT = 194.9                           # separador etiqueta / valor
INFO_DNI_X = 420.5

HEAD_TOP, HEAD_MID, HEAD_BOTTOM = 698.6, 679.3, 660.0   # cabecera de la tabla
BODY_TOP, BODY_BOTTOM = 660.0, 95.2                     # cuerpo de la tabla

# Bordes verticales de las columnas
X_L, X_NUM, X_FECHA, X_HRLAB, X_HRS, X_DESC, X_FIRMA, X_VOBO, X_R = (
    17.2, 33.2, 71.4, 104.2, 129.6, 351.8, 418.5, 485.3, 571.2
)

BLANK_ROW_H = 56.4                            # alto de una fila vacia del formato
BLANK_SUBLINES = 5                            # renglones internos de una fila vacia

SIG_LEFT = (41.5, 209.1, 44.3)                # firma y sello Jefatura
SIG_RIGHT = (370.7, 532.7, 45.9)              # firma y sello Gerencia Responsable

LW = 0.5                                      # grosor de linea
GREY = Color(0.35, 0.35, 0.35)
SHADE = Color(0.925, 0.925, 0.925)            # relleno de la fila de totales

F_REG, F_BLD, F_ITA, F_BI = (
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"
)


# --------------------------------------------------------------------------- #
# Utilidades de texto
# --------------------------------------------------------------------------- #
def wrap_runs(c, runs, max_w):
    """Ajusta una secuencia de tramos (texto, fuente, tamano) a un ancho dado.

    Devuelve una lista de lineas; cada linea es una lista de tramos.
    """
    tokens = []
    for text, font, size in runs:
        parts = text.split(" ")
        for i, part in enumerate(parts):
            if part:
                tokens.append((part, font, size))
            if i < len(parts) - 1:
                tokens.append((" ", font, size))

    lines, line, width = [], [], 0.0
    for tok, font, size in tokens:
        w = c.stringWidth(tok, font, size)
        if tok == " " and not line:
            continue
        if line and width + w > max_w:
            while line and line[-1][0] == " ":
                line.pop()
            lines.append(line)
            line, width = [], 0.0
            if tok == " ":
                continue
        line.append((tok, font, size))
        width += w
    if line:
        while line and line[-1][0] == " ":
            line.pop()
        lines.append(line)
    return lines or [[]]


def draw_runs(c, x, y, line, color=black):
    """Dibuja una linea compuesta por varios tramos a partir de (x, y)."""
    cur = x
    for tok, font, size in line:
        c.setFont(font, size)
        c.setFillColor(color if font != F_ITA else GREY)
        c.drawString(cur, y, tok)
        cur += c.stringWidth(tok, font, size)
    c.setFillColor(black)


def centered(c, x0, x1, y, text, font, size, color=black):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString((x0 + x1) / 2.0, y, text)
    c.setFillColor(black)


def center_block(c, x0, x1, y_top, y_bot, lines, font, size, leading):
    """Centra vertical y horizontalmente un bloque de lineas en una celda."""
    total = len(lines) * leading
    y = (y_top + y_bot) / 2.0 + total / 2.0 - leading + (leading - size) / 2.0 + 0.6
    for ln in lines:
        centered(c, x0, x1, y, ln, font, size)
        y -= leading


# --------------------------------------------------------------------------- #
# Calculo de horas
# --------------------------------------------------------------------------- #
def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes):
    return "%d:%02d" % (minutes // 60, minutes % 60)


def calcular_duraciones(actividades):
    """Duracion imputada a cada registro.

    La bitacora registra la hora de *culminacion* de cada actividad ("Culminacion
    de...", "Finalizacion de..."), por lo que a cada registro le corresponde el
    tiempo transcurrido desde el registro anterior. El primer registro es la
    marca de inicio de jornada y no consume tiempo.
    """
    duraciones = [0]
    for prev, act in zip(actividades, actividades[1:]):
        duraciones.append(to_min(act["hora"]) - to_min(prev["hora"]))
    return duraciones


# --------------------------------------------------------------------------- #
# Construccion del documento
# --------------------------------------------------------------------------- #
def build(data, salida):
    info = data["informacion_general"]
    acts = data["bitacora_actividades"]
    dur = calcular_duraciones(acts)
    total = sum(dur)

    c = canvas.Canvas(salida, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("RE-CO-005 Control de Trabajo Remoto - VAL 03 Cerro Verde")
    c.setAuthor(info["contratista"])
    c.setSubject(info["objetivo"])
    c.setLineWidth(LW)
    c.setStrokeColor(black)

    # ---- Cabecera institucional (imagen del formato original) ----
    c.drawImage(
        ImageReader(os.path.join(BASE, "assets", "reco005_cabecera.png")),
        BANNER[0], BANNER[1], width=BANNER[2], height=BANNER[3], mask="auto"
    )

    # ---- Bloque de datos generales ----
    rows_y = [INFO_TOP, INFO_TOP - 12.27, INFO_TOP - 24.53, INFO_BOTTOM]
    for y in rows_y:
        c.line(X_L, y, X_R, y)
    for x in (X_L, INFO_SPLIT, X_R):
        c.line(x, INFO_TOP, x, INFO_BOTTOM)

    etiquetas = [
        "MES:",
        "APELLIDOS Y NOMBRES COLABORADOR :",
        "GERENCIA RESPONSABLE - Apellidos y Nombres",
    ]
    for i, txt in enumerate(etiquetas):
        c.setFont(F_BI, 7)
        c.setFillColor(black)
        c.drawString(X_L + 1.9, rows_y[i] - 8.5, txt)

    c.setFont(F_BI, 7)
    c.drawString(INFO_DNI_X, rows_y[1] - 8.5, "DNI:")

    # Valores conocidos por la bitacora. Los datos personales del colaborador y
    # el mes/fecha no forman parte de la bitacora y quedan para su llenado.
    c.setFont(F_REG, 7)
    c.drawString(INFO_SPLIT + 4, rows_y[0] - 8.5, "")

    # ---- Cabecera de la tabla ----
    for y in (HEAD_TOP, HEAD_BOTTOM):
        c.line(X_L, y, X_R, y)
    c.line(X_HRS - 25.4, HEAD_MID, X_DESC, HEAD_MID)   # divide Hrs / Descripcion
    for x in (X_L, X_NUM, X_FECHA, X_HRLAB, X_DESC, X_FIRMA, X_VOBO, X_R):
        c.line(x, HEAD_TOP, x, HEAD_BOTTOM)
    c.line(X_HRS, HEAD_MID, X_HRS, HEAD_BOTTOM)

    center_block(c, X_L, X_NUM, HEAD_TOP, HEAD_BOTTOM, ["N\xb0"], F_BI, 7, 8.6)
    center_block(c, X_NUM, X_FECHA, HEAD_TOP, HEAD_BOTTOM, ["FECHA"], F_BI, 7, 8.6)
    center_block(c, X_FECHA, X_HRLAB, HEAD_TOP, HEAD_BOTTOM,
                 ["HR.", "LABORA", "DAS"], F_BI, 7, 8.6)
    center_block(c, X_HRLAB, X_DESC, HEAD_TOP, HEAD_MID,
                 ["ACTIVIDADES REALIZADAS"], F_BI, 7, 8.6)
    center_block(c, X_HRLAB, X_HRS, HEAD_MID, HEAD_BOTTOM, ["Hrs"], F_BI, 7, 8.6)
    center_block(c, X_HRS, X_DESC, HEAD_MID, HEAD_BOTTOM,
                 ["Descripci\xf3n"], F_BI, 7, 8.6)
    center_block(c, X_DESC, X_FIRMA, HEAD_TOP, HEAD_BOTTOM,
                 ["FIRMA", "COLABORADOR"], F_BI, 7, 8.6)
    center_block(c, X_FIRMA, X_VOBO, HEAD_TOP, HEAD_BOTTOM,
                 ["V\xbaB\xba GERENCIA"], F_BI, 7, 8.6)
    center_block(c, X_VOBO, X_R, HEAD_TOP, HEAD_BOTTOM,
                 ["OBSERVACIONES", "GERENCIA", "RESPONSABLE"], F_BI, 7, 8.6)

    # ---- Composicion del cuerpo: fila 1 = jornada de la bitacora ----
    desc_w = X_DESC - X_HRS - 7.0
    fs, lead = 6.2, 7.3

    intro = wrap_runs(c, [
        ("PROYECTO CERRO VERDE \xb7 %s \xb7 VALORIZACI\xd3N 03 (VAL 03). "
         % info["contratista"].upper(), F_BLD, fs),
        ("Objetivo: %s. Jornada: %s a %s." % (
            info["objetivo"], info["hora_inicio"], info["hora_fin"]), F_REG, fs),
    ], desc_w)

    sub = []       # (texto_hrs, lineas_descripcion)
    sub.append(("", intro))
    for act, d in zip(acts, dur):
        # Evita parentesis anidados en la cita del medio de sustento.
        ref = act["referencia_visual"]
        if ref.endswith(")") and " (" in ref:
            ref = ref.replace(" (", ", ").rstrip(")")
        runs = [
            ("%s \xb7 %s:" % (act["hora"], act["actividad"]), F_BLD, fs),
            (" " + act["descripcion"], F_REG, fs),
            (" (Sustento: %s)" % ref, F_ITA, fs),
        ]
        sub.append((to_hhmm(d) if d else "inicio", wrap_runs(c, runs, desc_w)))
    sub.append(("%s" % to_hhmm(total),
                wrap_runs(c, [("TOTAL DE HORAS REGISTRADAS EN LA JORNADA",
                               F_BLD, fs)], desc_w)))

    pad = 2.6
    heights = [max(11.28, len(ln) * lead + pad) for _, ln in sub]
    row1_h = sum(heights)

    disponible = BODY_TOP - BODY_BOTTOM
    n_blank = int((disponible - row1_h) // BLANK_ROW_H)
    sobrante = disponible - row1_h - n_blank * BLANK_ROW_H
    extra = sobrante / len(heights)                 # reparte el remanente
    heights = [h + extra for h in heights]
    row1_h = sum(heights)

    # ---- Fila 1 ----
    y_top = BODY_TOP
    y_bot = y_top - row1_h

    centered(c, X_L, X_NUM, (y_top + y_bot) / 2.0 - 2.2, "1", F_ITA, 7)
    center_block(c, X_NUM, X_FECHA, y_top, y_bot, [""], F_REG, 7, 8.0)
    center_block(c, X_FECHA, X_HRLAB, y_top, y_bot,
                 [to_hhmm(total)], F_BLD, 7.5, 8.6)

    y = y_top
    for (hrs, lines), h in zip(sub, heights):
        y_next = y - h
        if hrs == to_hhmm(total) and lines is sub[-1][1]:
            c.setFillColor(SHADE)
            c.rect(X_HRLAB, y_next, X_DESC - X_HRLAB, h, stroke=0, fill=1)
            c.setFillColor(black)
        if hrs:
            centered(c, X_HRLAB, X_HRS, (y + y_next) / 2.0 - 2.2, hrs,
                     F_BLD if hrs != "inicio" else F_ITA,
                     6.5 if hrs != "inicio" else 5.8)
        ty = (y + y_next) / 2.0 + (len(lines) * lead) / 2.0 - lead + 1.6
        for ln in lines:
            draw_runs(c, X_HRS + 3.0, ty, ln)
            ty -= lead
        if y_next > y_bot + 0.1:
            c.line(X_HRLAB, y_next, X_DESC, y_next)
        y = y_next

    # ---- Filas vacias restantes del formato ----
    y = y_bot
    for n in range(2, 2 + n_blank):
        top, bot = y, y - BLANK_ROW_H
        centered(c, X_L, X_NUM, (top + bot) / 2.0 - 2.2, str(n), F_ITA, 7)
        step = BLANK_ROW_H / BLANK_SUBLINES
        for k in range(1, BLANK_SUBLINES):
            yy = top - k * step
            c.line(X_HRLAB, yy, X_DESC, yy)
            c.line(X_VOBO, yy, X_R, yy)
        y = bot

    # ---- Marco y verticales del cuerpo ----
    y = BODY_TOP - row1_h
    c.line(X_L, y, X_R, y)
    for n in range(n_blank):
        y -= BLANK_ROW_H
        c.line(X_L, y, X_R, y)
    for x in (X_L, X_NUM, X_FECHA, X_HRLAB, X_HRS, X_DESC, X_FIRMA, X_VOBO, X_R):
        c.line(x, BODY_TOP, x, BODY_BOTTOM)
    c.line(X_L, BODY_BOTTOM, X_R, BODY_BOTTOM)

    # ---- Pie de firmas ----
    for x0, x1, yy in (SIG_LEFT, SIG_RIGHT):
        c.line(x0, yy, x1, yy)
    centered(c, SIG_LEFT[0], SIG_LEFT[1], SIG_LEFT[2] - 11.5,
             "Firma y Sello Jefatura", F_BI, 7.5)
    centered(c, SIG_RIGHT[0], SIG_RIGHT[1], SIG_RIGHT[2] - 11.5,
             "Firma y Sello Gerencia Responsable", F_BI, 7.5)

    c.showPage()
    c.save()
    return total, n_blank


if __name__ == "__main__":
    with open(os.path.join(BASE, "bitacora_val03.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    out = os.path.join(BASE, "RECO005_Control_de_Trabajo_Remoto_VAL03.pdf")
    total, libres = build(data, out)
    print("Generado: %s" % out)
    print("Total horas imputadas: %s | filas libres: %d" % (to_hhmm(total), libres))

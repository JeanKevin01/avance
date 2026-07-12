Attribute VB_Name = "ClaudeMSProject"
'======================================================================
'  Claude para Microsoft Project  -  Plugin de instrucciones en vivo
'----------------------------------------------------------------------
'  Permite escribir instrucciones en LENGUAJE NATURAL dentro de
'  Microsoft Project y que Claude modifique el cronograma directamente.
'
'  Ejemplo: pulsas el boton, escribes:
'     "Agrega 3 tareas: excavacion 5 dias, compactacion 3 dias y
'      relleno 4 dias, una tras otra, y un hito de entrega al final"
'  ...y aparecen en tu Gantt al instante.
'
'  COMO FUNCIONA:
'   1. Toma tu instruccion + el listado de tareas actual.
'   2. Llama a la API de Anthropic (Claude).
'   3. Claude responde con comandos simples separados por lineas.
'   4. Este modulo ejecuta cada comando sobre el proyecto activo.
'
'  REQUISITOS:
'   - Una clave de API de Anthropic (https://console.anthropic.com).
'   - Conexion a internet.
'   - Pega tu clave en la constante API_KEY de abajo.
'======================================================================

Option Explicit

' ==== CONFIGURACION (edita estas 3 lineas) ============================
Private Const API_KEY As String = "TU_API_KEY_AQUI"    ' <-- pega tu clave sk-ant-...
Private Const MODELO As String = "claude-sonnet-4-5"   ' <-- cambia si tu cuenta usa otro modelo
Private Const HORAS_POR_DIA As Double = 8              ' <-- 8 estandar; 10 si trabajas turnos de 10h
' ======================================================================


'--- BOTON PRINCIPAL: llamalo desde la cinta, Alt+F8, o un boton ------
Public Sub PreguntarAClaude()
    Dim instruccion As String
    instruccion = InputBox( _
        "Escribe lo que quieres hacer con el cronograma:" & vbCrLf & vbCrLf & _
        "Ej: 'Crea las fases de excavacion, compactacion y relleno " & _
        "con sus duraciones y enlazalas en secuencia'", _
        "Claude para MS Project")

    If Trim(instruccion) = "" Then Exit Sub

    If API_KEY = "TU_API_KEY_AQUI" Then
        MsgBox "Primero pega tu clave de API de Anthropic en la constante " & _
               "API_KEY del modulo (menu Programador > Visual Basic).", _
               vbExclamation, "Configuracion pendiente"
        Exit Sub
    End If

    Application.StatusBar = "Consultando a Claude..."
    Dim respuesta As String
    On Error GoTo fallo
    respuesta = LlamarClaude(instruccion, ConstruirContexto())
    Application.StatusBar = "Aplicando cambios..."
    EjecutarComandos respuesta
    Application.StatusBar = False
    Exit Sub

fallo:
    Application.StatusBar = False
    MsgBox "Ocurrio un error: " & Err.Description, vbCritical, "Claude para MS Project"
End Sub


'--- Construye el contexto: listado de tareas actuales ----------------
Private Function ConstruirContexto() As String
    Dim s As String, t As Task
    s = "Tareas actuales (ID | Nombre | Duracion dias | % avance):" & vbLf
    If ActiveProject.Tasks.Count = 0 Then
        s = s & "(el cronograma esta vacio)" & vbLf
    Else
        For Each t In ActiveProject.Tasks
            If Not t Is Nothing Then
                s = s & t.ID & " | " & t.Name & " | " & _
                    Format(t.Duration / (60 * HORAS_POR_DIA), "0.##") & " | " & _
                    t.PercentComplete & "%" & vbLf
            End If
        Next t
    End If
    ConstruirContexto = s
End Function


'--- Llama a la API de Anthropic y devuelve el texto de la respuesta ---
Private Function LlamarClaude(instruccion As String, contexto As String) As String
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")

    Dim sistema As String
    sistema = "Eres un asistente que controla Microsoft Project para obras civiles. " & _
      "Responde UNICAMENTE con comandos, uno por linea, sin explicaciones ni markdown. " & _
      "Comandos disponibles (usa | como separador):" & vbLf & _
      "CREAR_TAREA|nombre|duracion_dias" & vbLf & _
      "HITO|nombre" & vbLf & _
      "ACTUALIZAR|id|campo|valor   (campo: nombre, duracion, avance, notas)" & vbLf & _
      "ELIMINAR|id" & vbLf & _
      "DEPENDENCIA|id_predecesora|id_sucesora|tipo   (tipo: FS, SS, FF o SF)" & vbLf & _
      "RECURSO|nombre" & vbLf & _
      "ASIGNAR|id_tarea|nombre_recurso" & vbLf & _
      "AVANCE|id_tarea|porcentaje" & vbLf & _
      "MENSAJE|texto de confirmacion para el usuario" & vbLf & _
      "Los IDs nuevos siguen el orden de creacion tras las tareas existentes. " & _
      "Termina SIEMPRE con una linea MENSAJE resumiendo lo hecho."

    Dim contenido As String
    contenido = contexto & vbLf & "Instruccion del usuario: " & instruccion

    Dim body As String
    body = "{""model"":""" & MODELO & """,""max_tokens"":2000," & _
           """system"":""" & JsonEscape(sistema) & """," & _
           """messages"":[{""role"":""user"",""content"":""" & JsonEscape(contenido) & """}]}"

    http.Open "POST", "https://api.anthropic.com/v1/messages", False
    http.setRequestHeader "content-type", "application/json"
    http.setRequestHeader "x-api-key", API_KEY
    http.setRequestHeader "anthropic-version", "2023-06-01"
    http.send body

    If http.Status <> 200 Then
        Err.Raise vbObjectError, , "La API respondio " & http.Status & ": " & http.responseText
    End If

    LlamarClaude = ExtraerTexto(http.responseText)
End Function


'--- Ejecuta la lista de comandos devuelta por Claude -----------------
Private Sub EjecutarComandos(respuesta As String)
    Dim lineas() As String, i As Long, partes() As String
    Dim mensajeFinal As String, creadas As Long
    respuesta = Replace(respuesta, vbCr, "")
    lineas = Split(respuesta, vbLf)

    For i = LBound(lineas) To UBound(lineas)
        Dim linea As String
        linea = Trim(lineas(i))
        If linea <> "" Then
            partes = Split(linea, "|")
            Dim op As String
            op = UCase(Trim(partes(0)))

            Select Case op
                Case "CREAR_TAREA"
                    Dim t As Task
                    Set t = ActiveProject.Tasks.Add(Trim(partes(1)))
                    If UBound(partes) >= 2 Then
                        t.Duration = CDbl(Val(partes(2))) * 60 * HORAS_POR_DIA
                    End If
                    creadas = creadas + 1

                Case "HITO"
                    Dim h As Task
                    Set h = ActiveProject.Tasks.Add(Trim(partes(1)))
                    h.Milestone = True
                    h.Duration = 0
                    creadas = creadas + 1

                Case "ACTUALIZAR"
                    ActualizarTarea CLng(Val(partes(1))), LCase(Trim(partes(2))), partes(3)

                Case "ELIMINAR"
                    BuscarTarea(CLng(Val(partes(1)))).Delete

                Case "DEPENDENCIA"
                    CrearDependencia CLng(Val(partes(1))), CLng(Val(partes(2))), _
                                     UCase(Trim(partes(3)))

                Case "RECURSO"
                    ActiveProject.Resources.Add Trim(partes(1))

                Case "ASIGNAR"
                    AsignarRecurso CLng(Val(partes(1))), Trim(partes(2))

                Case "AVANCE"
                    BuscarTarea(CLng(Val(partes(1)))).PercentComplete = CLng(Val(partes(2)))

                Case "MENSAJE"
                    If UBound(partes) >= 1 Then mensajeFinal = partes(1)
            End Select
        End If
    Next i

    If mensajeFinal = "" Then mensajeFinal = "Listo. Cambios aplicados: " & creadas & " tarea(s)."
    MsgBox mensajeFinal, vbInformation, "Claude para MS Project"
End Sub


'--- Utilidades sobre el proyecto -------------------------------------
Private Function BuscarTarea(id As Long) As Task
    Dim t As Task
    For Each t In ActiveProject.Tasks
        If Not t Is Nothing Then
            If t.ID = id Then
                Set BuscarTarea = t
                Exit Function
            End If
        End If
    Next t
    Err.Raise vbObjectError, , "No existe la tarea con ID " & id
End Function

Private Sub ActualizarTarea(id As Long, campo As String, valor As String)
    Dim t As Task
    Set t = BuscarTarea(id)
    Select Case campo
        Case "nombre": t.Name = valor
        Case "duracion": t.Duration = CDbl(Val(valor)) * 60 * HORAS_POR_DIA
        Case "avance": t.PercentComplete = CLng(Val(valor))
        Case "notas": t.Notes = valor
    End Select
End Sub

Private Sub CrearDependencia(pred As Long, succ As Long, tipo As String)
    Dim dep As TaskDependency
    Set dep = ActiveProject.TaskDependencies.Add(BuscarTarea(pred), BuscarTarea(succ))
    Select Case tipo
        Case "SS": dep.Type = pjStartToStart
        Case "FF": dep.Type = pjFinishToFinish
        Case "SF": dep.Type = pjStartToFinish
        Case Else: dep.Type = pjFinishToStart
    End Select
End Sub

Private Sub AsignarRecurso(idTarea As Long, nombreRecurso As String)
    Dim r As Resource, existe As Resource
    For Each r In ActiveProject.Resources
        If Not r Is Nothing Then
            If LCase(r.Name) = LCase(nombreRecurso) Then Set existe = r
        End If
    Next r
    If existe Is Nothing Then Set existe = ActiveProject.Resources.Add(nombreRecurso)
    Dim tar As Task
    Set tar = BuscarTarea(idTarea)
    tar.Assignments.Add tar.ID, existe.ID
End Sub


'--- Utilidades JSON (sin librerias externas) -------------------------
Private Function JsonEscape(s As String) As String
    s = Replace(s, "\", "\\")
    s = Replace(s, """", "\""")
    s = Replace(s, vbCr, "")
    s = Replace(s, vbLf, "\n")
    s = Replace(s, vbTab, "\t")
    JsonEscape = s
End Function

'--- Extrae el primer "text":"..." de la respuesta de la API ----------
Private Function ExtraerTexto(json As String) As String
    Dim marca As String, p As Long, q As Long, i As Long, ch As String, out As String
    marca = """text"":"""
    p = InStr(json, marca)
    If p = 0 Then
        ExtraerTexto = ""
        Exit Function
    End If
    i = p + Len(marca)
    Do While i <= Len(json)
        ch = Mid(json, i, 1)
        If ch = "\" Then
            Dim nxt As String
            nxt = Mid(json, i + 1, 1)
            Select Case nxt
                Case "n": out = out & vbLf
                Case "r": ' ignorar
                Case "t": out = out & vbTab
                Case """": out = out & """"
                Case "\": out = out & "\"
                Case "/": out = out & "/"
                Case Else: out = out & nxt
            End Select
            i = i + 2
        ElseIf ch = """" Then
            Exit Do
        Else
            out = out & ch
            i = i + 1
        End If
    Loop
    ExtraerTexto = out
End Function

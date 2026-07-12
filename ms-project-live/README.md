# MS Project EN VIVO — Control desde Claude

Conecta **Microsoft Project** con **Claude** para controlar tus cronogramas en vivo.
A diferencia del enfoque por archivos XML, aquí Claude modifica el proyecto que tienes
**abierto en pantalla** — los cambios aparecen al instante.

Tienes **dos formas de usarlo**, y puedes tener ambas a la vez:

| | **A. Claude Desktop + MCP** | **B. Plugin dentro de MS Project (VBA)** |
|---|---|---|
| Dónde escribes | En la ventana de Claude Desktop | En el propio MS Project (un botón) |
| Qué necesitas | Suscripción de Claude | Clave de API de Anthropic (de pago por uso) |
| Ideal para | Conversación larga, análisis, planificación | Instrucciones rápidas sin salir de MS Project |
| Motor | Servidor MCP (Python + COM) | Macro VBA que llama a la API |

Ambas controlan el mismo MS Project. Empieza por la que prefieras.

---

## Requisitos comunes

- **Windows** con **Microsoft Project** (Desktop / Professional) instalado
- **Python 3.11+** (para la opción A)

---

## Opción A — Claude Desktop + MCP (recomendada para empezar)

### 1. Instala dependencias
Abre PowerShell en la carpeta del proyecto:
```powershell
cd C:\Users\HP\Documents\GitHub\MCP-Ms-Project\ms-project-live
pip install -r requirements.txt
```

### 2. Configura Claude Desktop
Edita (o crea) el archivo:
```
C:\Users\<TU_USUARIO>\AppData\Roaming\Claude\claude_desktop_config.json
```
Pega el contenido de `claude_desktop_config.ejemplo.json` **ajustando la ruta** a donde
clonaste el repo. Reinicia Claude Desktop.

### 3. Úsalo
1. Abre **Microsoft Project** con tu cronograma (o vacío).
2. Abre **Claude Desktop** y escribe, por ejemplo:

```
Conéctate a mi Microsoft Project y muéstrame las tareas actuales.
```
```
Crea la fase de excavación: limpieza (5 días), cut-off trench (8 días)
y relleno zona 2B (12 días), enlazadas en secuencia. Agrega un hito de
entrega al final y guarda el proyecto.
```
```
La tarea 4 va al 60% de avance. Actualízala.
```

Claude usará las herramientas del MCP y verás los cambios aparecer en MS Project en vivo.

---

## Opción B — Plugin dentro de MS Project (VBA)

Esto agrega un botón **"Preguntar a Claude"** dentro de MS Project.

### 1. Consigue una clave de API
En https://console.anthropic.com → **API Keys** → crea una (`sk-ant-...`).
> Nota: la API es de pago por uso, distinta de tu suscripción de Claude.

### 2. Importa el módulo VBA
1. En MS Project: pestaña **Programador** → **Visual Basic**
   (si no ves "Programador": Archivo → Opciones → Personalizar cinta → marca "Programador").
2. En el editor VBA: **Archivo → Importar archivo** → elige `vba\ClaudeMSProject.bas`.
3. Abre el módulo importado y pega tu clave en la línea:
   ```vba
   Private Const API_KEY As String = "TU_API_KEY_AQUI"
   ```
   Si tu obra usa turnos de 10 horas, cambia también `HORAS_POR_DIA`.

### 3. Crea el botón (opcional pero cómodo)
Archivo → Opciones → Barra de herramientas de acceso rápido → en "Comandos disponibles"
elige **Macros** → selecciona `PreguntarAClaude` → **Agregar**. Aparecerá un botón arriba.

### 4. Úsalo
Pulsa el botón (o **Alt+F8 → PreguntarAClaude**), escribe tu instrucción en español y listo.

---

## Herramientas disponibles (opción A)

**Conexión / archivo:** `estado_conexion`, `conectar`, `abrir_proyecto`,
`crear_proyecto_nuevo`, `guardar`, `resumen_proyecto`

**Tareas:** `listar_tareas`, `crear_tarea`, `actualizar_tarea`, `eliminar_tarea`,
`establecer_avance`, `crear_hito`, `sangrar_tarea`, `anular_sangria`, `ruta_critica`

**Dependencias:** `crear_dependencia` (FS / SS / FF / SF, con retraso opcional)

**Recursos:** `listar_recursos`, `crear_recurso`, `asignar_recurso`

---

## Comandos del plugin VBA (opción B)

Claude responde con comandos que el módulo ejecuta automáticamente:
`CREAR_TAREA`, `HITO`, `ACTUALIZAR`, `ELIMINAR`, `DEPENDENCIA`, `RECURSO`,
`ASIGNAR`, `AVANCE`, `MENSAJE`.

---

## Arquitectura

```
Claude  ──►  server.py (FastMCP)  ──►  service.py  ──►  adapters/com_adapter.py  ──►  MS Project (COM, en vivo)
                                            │
                                            └──►  adapters/fake_adapter.py  (para pruebas sin Windows)

MS Project (botón VBA)  ──►  API de Anthropic  ──►  comandos  ──►  cronograma
```

La lógica de negocio (`service.py`) está aislada del acceso COM mediante un **adaptador**.
Por eso los **19 tests** de `tests/` se ejecutan en cualquier sistema operativo con el
adaptador falso, sin necesitar Windows ni MS Project:

```powershell
python -m pytest tests/ -v
```

---

## Estado de verificación

- ✅ **Lógica de negocio** (conversión de duraciones, dependencias, avances, EDT,
  recursos, resumen): **19/19 tests automatizados pasando**.
- ✅ **Servidor MCP**: carga y registra las 19 herramientas correctamente.
- ⚠️ **Capa COM y VBA**: escritas siguiendo el modelo de objetos oficial de MS Project,
  pero deben probarse en tu PC Windows con MS Project (este entorno de desarrollo es Linux
  y no puede ejecutar COM). Todo el acceso a COM está aislado en `adapters/com_adapter.py`,
  así que cualquier ajuste por versión de MS Project se hace en un solo archivo.

---

## Notas técnicas

- Las **duraciones** se manejan en días y se convierten a minutos según `MSP_HORAS_POR_DIA`
  (calendario estándar de MS Project = 8 h/día = 480 min/día).
- Los **IDs de tarea** corresponden a la columna *Id* de la vista Diagrama de Gantt.
  Tras crear varias tareas, pídele a Claude que liste de nuevo para confirmar los IDs
  antes de vincularlas.
- El servidor intenta **adjuntarse** a un MS Project ya abierto; si no hay ninguno, abre
  uno nuevo.

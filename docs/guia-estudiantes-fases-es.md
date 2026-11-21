# Construye tu pieza de danza con fases: guía para estudiantes

Escrita en lenguaje simple. Versión en inglés: `student-guide-phases-en.md`.

## 1. La idea

Haces tu pieza por pasos:

1. Tu canción tiene partes. Cada parte se llama **fase**. Una pieza tiene un máximo de 10 fases.
2. En cada fase eliges los instrumentos que se ven (Medios, Cámara, Ruido, Franjas de color, Partículas, Figura con disparadores).
3. En cada fase haces 4 **conexiones**. Una conexión une un movimiento del bailarín con un instrumento.
   - Un **movimiento** (subir el brazo, cruzar el escenario) controla un ajuste todo el tiempo.
   - Un **momento** (un golpe, presionar el botón, una nota de la canción, entrar en una zona) hace algo una vez.
4. Cada fase guarda sus propios instrumentos y conexiones. Cuando cambia la fase, todo cambia con ella.

No necesitas escribir código. Solo cambias ajustes en el panel de control.

## 2. Antes de empezar

1. Abre el proyecto. Se abre la ventana **Stage**.
2. El panel de control está a la derecha de la ventana Stage. Si no lo ves, presiona la tecla **P**.
3. Arriba del panel hay pestañas: **Función**, **Fases**, **Composición**, **Movimiento**, **Entradas**.
4. Para cambiar el idioma, haz clic en **English / Español**, abajo a la derecha.
5. Haz clic en **Función**. Revisa que **Nivel** esté en **Básico**.

Consejo: pon el ratón sobre el nombre de un ajuste y espera. Aparece un texto de ayuda.

## 3. Fases

### 3.1 Divide tu canción en fases

Ejemplo: tu canción tiene 3 partes. Un inicio tranquilo, un medio rápido y un final lento.

1. Carga tu canción y su archivo MIDI (pide ayuda al profesor).
2. Haz clic en la pestaña **Fases**.
3. Revisa que **Seguir MIDI** esté activado (**On**).
4. Pon **Fase** en **Fase 2**.
5. En **Nota para esta fase**, escribe la nota MIDI que empieza el medio rápido, por ejemplo `2`.
6. Pon **Fase** en **Fase 3**. Escribe la nota que empieza el final lento, por ejemplo `1`.
7. La fase 1 empieza al inicio de la canción. No necesita nota.

Para encontrar los números de las notas, reproduce la canción y mira la ventana **Notas MIDI**, abajo en la ventana Stage. Si no conoces las notas, pregunta al profesor.

`-1` significa "sin nota". Una fase con `-1` no empieza desde la canción.

### 3.2 Cambia de fase con las teclas de números

Presiona una tecla de número: **1** a **9** eligen las fases 1 a 9. **0** elige la fase 10.

La fase cambia después de un momento corto (menos de medio segundo). Cuando escribes un número en un ajuste (por ejemplo una nota), la fase no cambia.

### 3.3 Elige los instrumentos de cada fase

1. Pon **Fase** en **Fase 1**.
2. Haz clic en **Composición**. Pon **Encendido** en cada instrumento que quieres. Apaga los otros instrumentos.
3. Para **Medios**, haz clic en **Elegir carpeta...** y elige una carpeta con fotos y videos.
4. Pon **Fase** en **Fase 2** (o presiona **2**). La fase 2 empieza como copia de la fase 1. Cámbiala.
5. Presiona **1** y luego **2**. El aspecto cambia cada vez.

No necesitas guardar cada fase. Cada cambio se guarda en la fase que ves.

Los instrumentos siempre están en el mismo orden: Medios al fondo, luego Cámara, Ruido, Franjas de color, Partículas, y la Figura con disparadores adelante. Las partes oscuras de un instrumento dejan ver los instrumentos de abajo.

## 4. Conexiones

Haz clic en **Movimiento**. Cada fase tiene 4 conexiones. Una conexión tiene cuatro menús:

| Menú | Qué eliges | Ejemplo |
|---|---|---|
| Fuente | De dónde viene el movimiento | Sensor 1 |
| Entrada | El movimiento o el momento | Golpe |
| Instrumento | El instrumento que cambia | Toda la imagen |
| Hace | Qué pasa | Impulso: Glitch |

Los menús te ayudan:

- **Entrada** muestra solo las entradas de la fuente que elegiste.
- **Hace** muestra solo lo que el instrumento puede hacer con esa entrada.
  - Para un movimiento, **Hace** muestra "Controla: ..." (el movimiento fija el valor todo el tiempo).
  - Para un momento, **Hace** muestra acciones que pasan una vez: "Impulso: ..." (el valor salta y vuelve) y las acciones propias del instrumento (Saltar, Archivo siguiente ...).
  - Algunas entradas son las dos cosas (por ejemplo "En zona 1 / entra en la zona 1"). Entonces **Hace** muestra las dos.

Cuando los cuatro menús están puestos, la conexión se activa (**Activa**).

### 4.1 Sube el brazo y las partículas crecen (un movimiento)

1. Pon **1 Fuente** en **Sensor 1**.
2. Pon **1 Entrada** en **Subir o bajar el brazo (pitch)**.
3. Pon **1 Instrumento** en **Partículas**.
4. Pon **1 Hace** en **Controla: Tamaño**.
5. Sube y baja el brazo. Las partículas crecen y se achican.

### 4.2 Das un golpe y la imagen hace glitch (un momento)

1. Pon **2 Fuente** en **Sensor 1**.
2. Pon **2 Entrada** en **Golpe**.
3. Pon **2 Instrumento** en **Toda la imagen**.
4. Pon **2 Hace** en **Impulso: Glitch**.
5. Da un golpe. La imagen hace glitch por un momento. **2 Cantidad** fija qué tan fuerte.

### 4.3 Entras en una zona y se ve el video siguiente (un momento)

1. Pon **3 Fuente** en **Cuerpo (cámara)**.
2. Pon **3 Entrada** en **En zona 2 / entra en la zona 2**.
3. Pon **3 Instrumento** en **Medios**.
4. Pon **3 Hace** en **Archivo siguiente**.
5. Entra en la zona 2. Se ve la foto o el video siguiente. La cámara te debe ver.

### 4.4 Una nota de la canción hace saltar la figura

1. Pon **4 Fuente** en **Canción (MIDI)**.
2. Pon **4 Entrada** en **Una nota de la canción**. Escribe el número de la nota en **4 Nota**.
3. Pon **4 Instrumento** en **Figura con disparadores** y **4 Hace** en **Saltar**.

### 4.5 Las entradas

| Fuente | Entrada | Tipo |
|---|---|---|
| Sensor 1-3 | Girar la muñeca (roll), Subir o bajar el brazo (pitch), Actividad, velocidades de giro | Movimiento |
| Sensor 1-3 | Golpe, Presionar el botón | Momento |
| Sensor 1-3 | Quieto / se queda quieto | Las dos |
| Cuerpo (cámara) | Posición izquierda-derecha, altura de las manos, brazos abiertos, energía | Movimiento |
| Cuerpo (cámara) | En zona 1-5 / entra en la zona 1-5, Bailarín visto / aparece el bailarín | Las dos |
| Movimiento en la cámara | Movimiento, izquierda, derecha | Movimiento |
| Canción (MIDI) | Una nota de la canción | Momento |
| Señales de prueba | Nivel, Zona (movimiento), Disparador de prueba (momento) | Para probar sin bailarín |

Zonas: la imagen de la cámara se corta en franjas de izquierda a derecha (pestaña Entradas, **Zonas del escenario**, Avanzado).

Consejo: "Girar la muñeca" no funciona bien cuando el brazo apunta recto hacia abajo o hacia arriba. Usa **Subir o bajar el brazo** para movimientos grandes del brazo.

### 4.6 Qué pueden hacer los instrumentos

| Instrumento | Acciones de una vez (momentos) | Controla (movimientos) |
|---|---|---|
| Toda la imagen | Impulso de Brillo, Saturación, Glitch, Contorno, Destello | Los mismos ajustes |
| Figura con disparadores | Pulso (crecer), Girar, Más lados, Saltar, Destello de color | Tamaño, posición, giro ... |
| Medios | Reproducir desde el inicio, Archivo siguiente, Archivo al azar | Posición en el video, Opacidad |
| Franjas de color | Mezclar los colores | Separación, Velocidad, Opacidad |
| Partículas, Ruido, Cámara | Impulso de un ajuste | Cada ajuste |

## 5. Guarda tu trabajo

Tu trabajo se guarda solo: unos segundos después de cada cambio, el show se escribe en `shows/autosave.json`. Cuando se abre el proyecto, carga este archivo si es más nuevo que el proyecto.

Para guardar una copia con tu nombre:

1. Haz clic en la pestaña **Fases**.
2. En **Archivo del show**, escribe un nombre con tu nombre, por ejemplo `shows/ana_show.json`.
3. Haz clic en **Guardar show**. **Estado del show** muestra "Saved ana_show.json" (guardado).

Para abrir tu show otra vez: escribe el mismo nombre en **Archivo del show** y haz clic en **Abrir show**.

El archivo del show guarda tus fases y sus notas, los instrumentos de cada fase, las conexiones de cada fase y tu canción.

## 6. Salida al proyector

En la pestaña **Función**, en **Salida**:

1. Pon **Pantalla** en el proyector (la pantalla 1 es la pantalla principal de la computadora).
2. Deja **Sin bordes (llenar la pantalla)** en **On**.
3. Haz clic en **Abrir ventana de salida**. Para cerrarla, haz clic en **Cerrar ventana de salida**.

**Nivel** hace toda la imagen más oscura o más clara. **Saturación** hace los colores más intensos (2) o blanco y negro (0).

## 7. Si hay un problema

| Problema | Qué hacer |
|---|---|
| Las teclas de números no hacen nada. | Presiona una sola tecla y espera. No presiones otras teclas al mismo tiempo. |
| Un instrumento no aparece. | Revisa su **Encendido** en la pestaña **Composición**, en la fase que suena ahora. |
| Una conexión no hace nada. | Revisa **Activa**, **Fuente**, **Entrada**, **Instrumento** y **Hace**. Revisa que el instrumento esté **Encendido**. Sensores: revisa que el sensor esté encendido y conectado (pestaña Entradas, **Estado**). Entradas de **Cuerpo**: la cámara te debe ver. |
| Medios no muestra nada. | Revisa **Carpeta** en la pestaña **Composición**. |
| La fase no cambia con la canción. | Revisa que **Seguir MIDI** esté en **On**. Revisa la nota en **Nota para esta fase**. |
| La computadora va lenta. | Pregunta al profesor. Apaga los instrumentos que no usas (pestaña Composición). |

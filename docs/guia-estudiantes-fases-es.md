# Construye tu pieza de danza con fases: guía para estudiantes

Escrita en lenguaje simple. Versión en inglés: `student-guide-phases-en.md`.

## 1. La idea

Haces tu pieza por pasos:

1. Tu canción tiene partes. Cada parte se llama **fase**. Una pieza tiene un máximo de 10 fases.
2. En cada fase eliges los instrumentos (Partículas, Ruido, Video eco, Formas, Figura con disparadores) y sus ajustes.
3. Conectas tus movimientos a los instrumentos:
   - Un **disparador** es un momento: un golpe, presionar el botón, una nota de la canción, entrar en una zona. Cada vez que pasa, la figura hace algo una vez.
   - Una **conexión** es continua: mientras te mueves, un número cambia, y cambia un ajuste todo el tiempo (por ejemplo, subes el brazo y las partículas crecen).
4. Cada fase guarda sus propios ajustes de instrumentos, disparadores y conexiones. Cuando cambia la fase, todo cambia con ella.

No necesitas escribir código. Solo cambias ajustes en el panel de control.

## 2. Antes de empezar

1. Abre el proyecto. Se abre la ventana **Stage**.
2. El panel de control está a la derecha de la ventana Stage. Si no lo ves, presiona la tecla **P**.
3. Arriba del panel hay pestañas: **Función**, **Fases**, **Instrumentos**, **Composición**, **Movimiento**, **Entradas**.
4. Para cambiar el idioma, haz clic en **English / Español**, abajo a la derecha.
5. Haz clic en **Función**. Pon **Nivel** en **Nivel 1**.

Consejo: pon el ratón sobre el nombre de un ajuste y espera. Aparece un texto de ayuda.

## 3. Nivel 1: fases, instrumentos y disparadores

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

1. Haz clic en la imagen de la ventana Stage (no en el panel de control).
2. Presiona una tecla de número: **1** a **9** eligen las fases 1 a 9. **0** elige la fase 10.

Las teclas de números no funcionan mientras escribes en el panel de control. Primero haz clic en la imagen.

### 3.3 Haz el aspecto de cada fase

Ejemplo: el inicio tranquilo tiene partículas lentas y azules. El medio rápido tiene partículas rápidas y ruido.

1. Pon **Fase** en **Fase 1**.
2. Haz clic en **Composición**. En **Partículas**, pon **Encendido** en **On**. Pon **Encendido** de los otros instrumentos en **Off**.
3. Haz clic en **Instrumentos**. En **Partículas**, pon **Preset** en **Calma**. Cambia **Color** si quieres.
4. Pon **Fase** en **Fase 2** (o presiona **2**). La fase 2 empieza como una copia de la fase 1.
5. Haz clic en **Composición**. En **Ruido**, pon **Encendido** en **On**.
6. Haz clic en **Instrumentos**. En **Partículas**, pon **Preset** en **Enérgico**.
7. Presiona **1**, luego **2**. El aspecto cambia cada vez.

No necesitas guardar cada fase. Cada cambio se guarda en la fase que ves.

Las capas siempre están en el mismo orden: Video eco al fondo, luego Ruido, luego Partículas, luego Formas, y la Figura con disparadores al frente. Las partes oscuras de una capa dejan ver las capas de abajo.

### 3.4 Un disparador: un momento hace que la figura haga algo

Ejemplo: la bailarina da un golpe y la figura salta.

1. Haz clic en **Composición**. En **Figura con disparadores**, pon **Encendida** en **On**.
2. Haz clic en **Movimiento**. Ve a **Disparadores**.
3. Pon **1 Activo** en **On**.
4. Pon **1 Fuente** en **Sensor 1**.
5. Pon **1 Momento** en **Golpe**.
6. Pon **1 Hace** en **Saltar**.
7. Ponte el sensor 1 y da un golpe. La figura salta.

### 3.5 Qué puede escuchar un disparador

| Fuente | Momento |
|---|---|
| Canción (MIDI) | Una nota de la canción. Escribe su número en **Nota**. |
| Sensor 1, 2 o 3 | **Golpe** (un movimiento rápido), **Presionar el botón**, **Se queda quieto** |
| Cuerpo (cámara) | **Aparece el bailarín**, **Entra en la zona 1** ... **Entra en la zona 5** |
| Señales de prueba | **Disparador de prueba** (para probar sin bailarín) |

Zonas: la imagen de la cámara se corta en franjas de izquierda a derecha (pestaña Entradas, **Zonas del escenario**). "Entra en la zona 2" pasa una vez, en el momento en que el bailarín entra en la zona 2.

### 3.6 Qué hace un disparador

| Hace | Qué pasa |
|---|---|
| Pulso (crecer) | La figura crece por un momento. |
| Girar | La figura gira. **Cantidad** = grados. |
| Más lados | La figura tiene más lados (o menos). |
| Saltar | La figura salta a otro lugar. |
| Destello de color | La figura destella en otro color. |

## 4. Nivel 2: conexiones (el movimiento cambia un ajuste todo el tiempo)

Haz clic en **Función** y pon **Nivel** en **Nivel 2**. Tu trabajo del Nivel 1 no cambia. Ahora la pestaña **Movimiento** también muestra 8 **conexiones**.

Una conexión tiene cuatro menús cortos:

| Menú | Qué eliges | Ejemplo |
|---|---|---|
| Fuente | De dónde viene el movimiento | Sensor 1 |
| Entrada | Qué movimiento de esa fuente | Subir o bajar el brazo (pitch) |
| Instrumento | Qué instrumento cambia | Partículas |
| Ajuste | Qué ajuste de ese instrumento | Tamaño |

El menú **Entrada** muestra solo los movimientos de la fuente que elegiste. El menú **Ajuste** muestra solo los ajustes del instrumento que elegiste.

### 4.1 Sube el brazo y las partículas crecen

1. Haz clic en **Movimiento**. Ve a **Asignaciones 1-4**.
2. Pon **1 Fuente** en **Sensor 1**.
3. Pon **1 Entrada** en **Subir o bajar el brazo (pitch)**.
4. Pon **1 Instrumento** en **Partículas**.
5. Pon **1 Ajuste** en **Tamaño**. La conexión se activa (**On**).
6. Sube y baja el brazo. Las partículas crecen y se hacen más pequeñas.

### 4.2 El ruido te sigue por el escenario

1. Pon **2 Fuente** en **Cuerpo (cámara)**.
2. Pon **2 Entrada** en **Posición izquierda-derecha**.
3. Pon **2 Instrumento** en **Ruido** y **2 Ajuste** en **Velocidad**.
4. Camina de izquierda a derecha. El ruido se mueve más rápido. La cámara te debe ver.

### 4.3 Los movimientos

| Fuente | Entrada | Tu movimiento |
|---|---|---|
| Sensor 1-3 | Girar la muñeca (roll) | Gira el antebrazo, como cuando giras una llave |
| Sensor 1-3 | Subir o bajar el brazo (pitch) | Brazo abajo = bajo, brazo adelante = medio, brazo arriba = alto |
| Sensor 1-3 | Actividad | Cuánto te mueves |
| Sensor 1-3 | Velocidad de giro / inclinación / vuelta | Qué tan rápido giras el sensor |
| Sensor 1-3 | Quieto, Golpe, Botón | 1 mientras pasa, si no 0 |
| Cuerpo (cámara) | Posición izquierda-derecha, altura de las manos, apertura de brazos, energía | Tu cuerpo en la imagen de la cámara |
| Cuerpo (cámara) | En zona 1-5 | 1 mientras estás en esa zona, si no 0 |
| Movimiento en la cámara | Movimiento, izquierda, derecha | Movimiento en cualquier parte de la imagen |

Consejo: "Girar la muñeca" no funciona bien cuando el brazo apunta recto hacia abajo o hacia arriba. Usa **Subir o bajar el brazo** para movimientos grandes del brazo.

### 4.4 Más ajustes (Avanzado)

En **Avanzado**, cada conexión también tiene **Desde**, **Hasta**, **Suavizado** y **Sensibilidad**:

- **Desde** y **Hasta**: los valores del ajuste en los dos extremos del movimiento. Si el ajuste se mueve al revés, intercambia **Desde** y **Hasta**.
- **Suavizado**: segundos que tarda el ajuste en seguir el movimiento.
- **Sensibilidad**: 2 = la mitad del movimiento llega a **Hasta**.

## 5. Guarda tu trabajo

Tu trabajo se guarda solo: unos segundos después de cada cambio, el show se escribe en `shows/autosave.json`. Cuando se abre el proyecto, carga este archivo si es más nuevo que el proyecto.

Para guardar una copia con tu nombre:

1. Haz clic en la pestaña **Fases**.
2. En **Archivo del show**, escribe un nombre con tu nombre, por ejemplo `shows/ana_show.json`.
3. Haz clic en **Guardar show**. **Estado del show** muestra "Saved ana_show.json" (guardado).

Para abrir tu show otra vez: escribe el mismo nombre en **Archivo del show** y haz clic en **Abrir show**.

El archivo del show guarda tus fases y sus notas, los ajustes de cada fase, los disparadores y las conexiones de cada fase, y tu canción.

## 6. Salida al proyector

En la pestaña **Función**, en **Salida**:

1. Pon **Pantalla** en el proyector (la pantalla 1 es la pantalla principal de la computadora).
2. Deja **Sin bordes (llenar la pantalla)** en **On**.
3. Haz clic en **Abrir ventana de salida**. Para cerrarla, haz clic en **Cerrar ventana de salida**.

**Nivel** hace toda la imagen más oscura o más clara. **Saturación** hace los colores más intensos (2) o blanco y negro (0).

## 7. Si hay un problema

| Problema | Qué hacer |
|---|---|
| Las teclas de números no hacen nada. | Primero haz clic en la imagen de la ventana Stage, luego presiona la tecla. |
| Un instrumento no aparece. | Revisa su **Encendido** en la pestaña **Composición**, en la fase que suena ahora. |
| El disparador no hace nada. | Revisa **Activo**, **Fuente** y **Momento**. Revisa que la Figura con disparadores esté **Encendida**. Revisa que el sensor esté encendido y conectado (ventana Sensores corporales, abajo en la ventana Stage). |
| La conexión no hace nada. | Pon **Nivel** en **Nivel 2**. Revisa **Fuente**, **Entrada**, **Instrumento** y **Ajuste**. Para las entradas de **Cuerpo**, la cámara te debe ver. |
| La fase no cambia con la canción. | Revisa que **Seguir MIDI** esté en **On**. Revisa la nota en **Nota para esta fase**. |
| La computadora va lenta. | Pregunta al profesor. Apaga los instrumentos que no usas (pestaña Composición). |

# Construye tu pieza de danza con fases: guía para estudiantes

Escrita en lenguaje simple. Versión en inglés: `student-guide-phases-en.md`.

## 1. La idea

Haces tu pieza por pasos:

1. Tu canción tiene partes. Cada parte se llama **fase**.
2. En cada fase pones figuras simples en la pantalla. Cada figura se llama **evento**. Un evento es un rectángulo, un círculo o un triángulo con un nombre adentro, por ejemplo "golpe" o "salto".
3. Tus movimientos muestran las figuras, las esconden y las mueven.
4. Después cambias las figuras simples por visuales reales.

No necesitas escribir código. Solo cambias ajustes en el panel de control.

## 2. Antes de empezar

1. Abre el proyecto. Se abre la ventana **Stage**.
2. El panel de control está a la derecha de la ventana Stage. Si no lo ves, presiona la tecla **P**.
3. Arriba del panel hay pestañas: **Función**, **Fases**, **Instrumentos**, **Composición**, **Movimiento**, **Entradas**.
4. Para cambiar el idioma, haz clic en **English / Español**, abajo a la derecha.
5. Haz clic en **Función**. Pon **Nivel** en **Nivel 1**.

Consejo: pon el ratón sobre el nombre de un ajuste y espera. Aparece un texto de ayuda.

## 3. Nivel 1: fases y figuras

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

### 3.2 Tu primera figura: siempre en pantalla

Ejemplo: durante el inicio tranquilo, un círculo azul con el nombre "respira" está siempre en pantalla.

1. Pon **Fase** en **Fase 1**.
2. Baja hasta **Evento 1**.
3. Pon **1 Activo** en **On**.
4. En **1 Nombre**, escribe `respira`.
5. Pon **1 Figura** en **Círculo** y **1 Color** en **Azul**.
6. Pon **1 Mostrar** en **Siempre**.
7. Haz clic en **Reproducir**, abajo en la ventana Stage. El círculo aparece en pantalla.

### 3.3 Cambia la posición y el tamaño

- **X** mueve la figura a la izquierda y a la derecha. `-1` es el borde izquierdo, `0` es el centro, `1` es el borde derecho.
- **Y** mueve la figura abajo y arriba. `-1` es abajo, `0` es el centro, `1` es arriba.
- **Tamaño** hace la figura más grande o más pequeña.

Ejemplo: para poner "respira" arriba a la izquierda, pon **1 X** en `-0.5` y **1 Y** en `0.5`.

### 3.4 Una figura que aparece con un movimiento: Alternar

Ejemplo: la bailarina da un golpe y aparece un cuadrado rojo. Da otro golpe y el cuadrado desaparece.

1. Ve a **Evento 2**. Pon **2 Activo** en **On**.
2. En **2 Nombre**, escribe `golpe`.
3. Pon **2 Figura** en **Rectángulo** y **2 Color** en **Rojo**.
4. Pon **2 Mostrar** en **Alternar**.
5. Pon **2 Disparador** en **Sensor 1: golpe**.
6. Ponte el sensor 1 y da un golpe. Aparece el cuadrado. Da otro golpe. El cuadrado desaparece.

### 3.5 Una figura por un tiempo corto: Por un tiempo

Ejemplo: el bailarín pisa fuerte y aparece un triángulo amarillo por 2 segundos.

1. Ve a **Evento 3**. Ponlo en **On**, nombre `pisada`, **Triángulo**, **Amarillo**.
2. Pon **3 Mostrar** en **Por un tiempo**.
3. Pon **3 Tiempo** en `2`.
4. Pon **3 Disparador** en **Sensor 2: golpe**.
5. Pisa fuerte. El triángulo aparece por 2 segundos. Si pisas otra vez antes de que terminen los 2 segundos, los 2 segundos empiezan de nuevo.

### 3.6 Una figura con la música: nota MIDI

Ejemplo: un círculo blanco aparece en cada golpe de tambor de la canción.

1. Ve a **Evento 4**. Ponlo en **On**, nombre `ritmo`, **Círculo**, **Blanco**.
2. Pon **4 Mostrar** en **Por un tiempo** y **4 Tiempo** en `0.3`.
3. Pon **4 Disparador** en **Nota MIDI (canción)**.
4. En **4 Nota**, escribe la nota MIDI del tambor.
5. Reproduce la canción. El círculo aparece en cada golpe.

### 3.7 Qué hace cada ajuste

| Ajuste | Qué hace |
|---|---|
| Activo | Usa este evento. Off: el evento no aparece. |
| Nombre | La palabra dentro de la figura. Usa el nombre del movimiento, por ejemplo "golpe". |
| Figura | Rectángulo, Círculo o Triángulo. |
| Color | El color de la figura. |
| X, Y, Tamaño | La posición y el tamaño de la figura. |
| Mostrar | **Siempre**: en pantalla durante toda la fase. **Alternar**: el disparador la muestra, el disparador otra vez la esconde. **Por un tiempo**: el disparador la muestra por los segundos de **Tiempo**. |
| Tiempo | Solo para **Por un tiempo**: el número de segundos. |
| Disparador | Qué muestra la figura: **Nota MIDI (canción)**, **Sensor 1-3: golpe** (un movimiento rápido) o **Sensor 1-3: botón**. |
| Nota | Solo para **Nota MIDI (canción)**: el número de la nota. |

Un ajuste gris no tiene efecto con lo que elegiste. Por ejemplo, **Tiempo** está gris cuando **Mostrar** no es **Por un tiempo**.

### 3.8 Bueno saber

- Cada fase tiene sus propios 8 eventos. El Evento 1 de la Fase 1 y el Evento 1 de la Fase 2 son diferentes.
- Cuando empieza una fase nueva, las figuras de la fase anterior desaparecen. Las figuras **Siempre** de la fase nueva aparecen.
- **Borrar fase** borra todos los eventos de la fase que ves. Cuidado: no se puede deshacer.
- Cuando la canción pasa a una fase nueva, el ajuste **Fase** cambia también. Así ves los eventos de esa fase.

## 4. Nivel 2: figuras que siguen tu cuerpo

Haz clic en **Función** y pon **Nivel** en **Nivel 2**. Tu trabajo del Nivel 1 no cambia. Ahora cada evento tiene 2 **enlaces**.

Un enlace conecta un movimiento de tu cuerpo con un ajuste de la figura. El enlace funciona cuando la figura está en pantalla.

### 4.1 Gira un cuadrado con tu brazo

Ejemplo: la bailarina da un golpe y aparece el cuadrado rojo (de 3.4). Después inclina el brazo y el cuadrado gira.

1. Ve a **Evento 2** (el cuadrado "golpe").
2. Pon **2 Enlace 1 Movimiento** en `serial_w1_roll`.
3. Pon **2 Enlace 1 Mueve** en **Rotación**.
4. Deja **2 Enlace 1 Desde** en `-180` y **2 Enlace 1 Hasta** en `180`.
5. Da un golpe para mostrar el cuadrado. Inclina el brazo a la izquierda y a la derecha. El cuadrado gira.

### 4.2 Mueve una figura con la posición de tu cuerpo

Ejemplo: un círculo sigue al bailarín de izquierda a derecha en el escenario. La cámara debe ver al bailarín.

1. Ve a un evento con **Mostrar** en **Siempre**.
2. Pon **Enlace 1 Movimiento** en `pose_x`.
3. Pon **Enlace 1 Mueve** en **Posición X**.
4. Camina del lado izquierdo al lado derecho. El círculo se mueve contigo.

### 4.3 Dos enlaces en una figura

Ejemplo: el círculo te sigue (enlace 1, de 4.2) y crece cuando abres los brazos.

1. En el mismo evento, pon **Enlace 2 Movimiento** en `pose_spread`.
2. Pon **Enlace 2 Mueve** en **Tamaño**.
3. Abre y cierra los brazos. El círculo crece y se hace más pequeño.

### 4.4 Los movimientos

| Nombre en el menú | Tu movimiento |
|---|---|
| `serial_w1_roll` (`w2`, `w3` para los sensores 2 y 3) | Inclinar el sensor hacia un lado |
| `serial_w1_pitch` | Inclinar el sensor arriba y abajo |
| `serial_w1_act` | Cuánto te mueves (actividad) |
| `serial_w1_gx`, `gy`, `gz` | Qué tan rápido tuerces, inclinas o giras |
| `pose_x` | Tu posición, de izquierda a derecha (cámara) |
| `pose_hand_l`, `pose_hand_r` | La altura de tu mano izquierda o derecha (cámara) |
| `pose_spread` | Cuánto abres los brazos (cámara) |
| `pose_energy` | Cuánto se mueve tu cuerpo (cámara) |
| `camera_motion`, `camera_left`, `camera_right` | Movimiento en la imagen de la cámara |

### 4.5 Qué hace cada ajuste del enlace

| Ajuste | Qué hace |
|---|---|
| Movimiento | El movimiento del cuerpo que controla la figura. |
| Mueve | Qué cambia: **Tamaño**, **Posición X**, **Posición Y**, **Rotación** o **Brillo**. |
| Desde | El valor al inicio del movimiento (por ejemplo, el brazo inclinado del todo a la izquierda). |
| Hasta | El valor al final del movimiento (por ejemplo, el brazo inclinado del todo a la derecha). |

Consejo: si la figura se mueve al revés, intercambia **Desde** y **Hasta**. Ejemplo: Desde `180`, Hasta `-180`.

## 5. Nivel 3

El Nivel 3 es para el siguiente paso: cambiar las figuras simples por visuales reales. Todavía no está listo. Por ahora, el Nivel 3 muestra lo mismo que el Nivel 2.

## 6. Guarda tu trabajo

Guarda tu show al final de cada sesión.

1. Haz clic en la pestaña **Fases**.
2. En **Archivo del show**, escribe un nombre con tu nombre, por ejemplo `shows/ana_show.json`.
3. Haz clic en **Guardar show**. **Estado del show** muestra "Saved ana_show.json" (guardado).

Para abrir tu show otra vez:

1. Escribe el mismo nombre en **Archivo del show**.
2. Haz clic en **Abrir show**. **Estado del show** muestra "Loaded ana_show.json" (abierto).

El archivo del show guarda tus fases, tus eventos, tu canción, tus ajustes de movimiento y tus ajustes de instrumentos.

Cuando cambias el **Nivel**, no pierdes trabajo. Los ajustes que no ves no cambian.

## 7. Si hay un problema

| Problema | Qué hacer |
|---|---|
| La figura no aparece. | Revisa que **Activo** esté en **On**. Revisa que **Fase** sea la fase que suena ahora. Revisa que **Eventos de fase** esté **Encendido** (pestaña Composición). |
| La figura no aparece cuando me muevo. | Revisa el **Disparador**. Revisa que el sensor esté encendido y conectado (ventana Sensores corporales, abajo en la ventana Stage). |
| La fase no cambia con la canción. | Revisa que **Seguir MIDI** esté en **On**. Revisa la nota en **Nota para esta fase**. |
| El enlace no hace nada. | Pon **Nivel** en **Nivel 2**. Revisa que la figura esté en pantalla. Para los movimientos `pose_`, la cámara te debe ver. |
| La computadora va lenta. | Pregunta al profesor. Apaga los instrumentos que no usas (pestaña Composición). |

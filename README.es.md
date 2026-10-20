<p align="center">
  <img src="docs/assets/icon.png" width="192" alt="Icono de Jumping Finn Turbo">
</p>

<h1 align="center">Finn NX</h1>
<p align="center">Jumping Finn Turbo / Finn Saltarín para Nintendo Switch homebrew</p>
<p align="center">
  <a href="https://github.com/RadiantDelux/Finn-NX/releases">Descargas</a> ·
  <a href="README.md">English</a> ·
  <a href="docs/BUILDING.md">Compilación</a> ·
  <a href="https://github.com/RadiantDelux/Finn-NX/issues">Reportar un fallo</a>
</p>

Finn NX ejecuta la versión **Android 1.1.6** de Jumping Finn Turbo con sus
bibliotecas ARMv7 y sus scripts originales de Unity/Mono. Usa **OpenGL ES con
Mesa/Nouveau** y permite jugar con pantalla táctil o mando, también en dock.

La descarga contiene el lanzador y el runtime de homebrew. **Debes aportar tu
propio APK compatible; el juego no está incluido.** Este es un port comunitario no oficial.

## Requisitos y APK

- Nintendo Switch con Atmosphère y una configuración capaz de instalar y ejecutar forwarders homebrew.
- hbmenu o sphaira y espacio de escritura disponible en la SD.
- El APK exacto de esta tabla. Este port no utiliza el IPA de iOS.

| Campo | Valor requerido |
| --- | --- |
| Juego | Jumping Finn Turbo / Finn Saltarín |
| Versión Android | **1.1.6** |
| Paquete | `com.turner.jft` |
| Arquitectura | `armeabi-v7a` |
| Motor | Unity `4.3.0f4`, Mono |
| Tamaño del APK | 50.439.654 bytes |

**SHA-256 del APK**

```text
7b3c4d0058c8f613b0a696fbbdd96b4fd0162e75d3ee85da11d9f38cf768d040
```

El nombre puede ser cualquiera con extensión `.apk`, también en mayúsculas.
El lanzador y el juego buscan los APK de su carpeta y comprueban el archivo
completo. Otra versión, un repack o un APK modificado se rechazan.

En Windows puedes comprobar tu copia con:

```powershell
Get-FileHash -Algorithm SHA256 "C:\Juegos\JumpingFinnTurbo.apk"
```

## Instalación

1. Descarga `finn_nx.nro` o el paquete para SD desde [Releases](https://github.com/RadiantDelux/Finn-NX/releases).
2. Copia el NRO y tu APK compatible en `sd:/switch/finn_nx/`:

   ```text
   switch/
   └── finn_nx/
       ├── finn_nx.nro
       └── tu-juego.apk
   ```

3. Abre el NRO desde Álbum/hbmenu. Reutiliza un forwarder instalado de Finn o
   instala su icono de HOME y solicita iniciar el juego. No hace falta descargar un NSP aparte.
4. El primer arranque extrae las bibliotecas nativas del APK; deja que termine.
   Después puedes abrir el icono de HOME directamente.

El NRO es un lanzador de 64 bits y el juego se ejecuta como **aplicación de
32 bits** tras el salto. Abrirlo desde Álbum no ejecuta Unity dentro del applet.

Si la instalación automática no está disponible en tu configuración, usa
**Install Forwarder** en sphaira sobre el NRO y abre ese icono desde HOME.

## Controles

| Entrada | Función |
| --- | --- |
| **Y** | Patada de Jake en el aire |
| **X** | Recovery / rebote |
| **B** | Medidor inicial: una pulsación lo inicia; otra realiza la patada |
| **B**, durante el vuelo | Toques para meteorito, arcoíris, pájaros y hielo; mantener repite |
| **L** o **ZL** | Aplastar un pingüino visible de la izquierda |
| **R** o **ZR** | Aplastar un pingüino visible de la derecha |
| **−** | Reiniciar la run como el botón original, conservando la partida |
| **+** | Pausar / reanudar desde el menú de pausa del juego |
| Stick izquierdo | Mover y mostrar el cursor rosado |
| **A** | Pulsar o arrastrar con el cursor, también en los menús |
| Clic del stick derecho | Android Back / atrás |
| **L + R + +** | Salir |
| Pantalla táctil | Controles táctiles originales en portátil |

La patada y el recovery respetan la disponibilidad y las recargas del juego.
Cualquier otro botón oculta el cursor; **A** lo mantiene visible al pulsar.
Mover el stick vuelve a mostrarlo. Reiniciar recarga la escena y puede mostrar
brevemente la transición de carga normal.

## Actualización y partidas

Sustituye `sd:/switch/finn_nx/finn_nx.nro` y vuelve a abrir Finn. El runtime
actualiza el programa ARM32 del icono existente. Conserva el APK y `data/`;
las partidas están en `sd:/switch/finn_nx/data/`.

El autor visible del NRO y del forwarder generado es **RadiantDelux**. El icono,
título y autor de HOME se copian al instalar el forwarder; reinstala uno ya
existente para renovar esos campos después de una actualización.

El forwarder automático utiliza el ID homebrew `059669A728222000` y genera
`sd:/atmosphere/contents/059669A728222000/exefs.nsp`. `title_id.txt` registra
los IDs de los iconos asociados a esta instalación.

## Si algo falla

| Síntoma | Qué revisar |
| --- | --- |
| APK ausente o rechazado | Carpeta, versión Android y SHA-256 exacto |
| Falla la instalación o el salto | `sd:/switch/finn_nx/forwarder-install.log`; prueba HOME o la alternativa de sphaira |
| Pantalla negra o cierre | `sd:/switch/finn_nx/debug.log` y `crash.log`, si se genera |
| Un botón del mando no actúa | Comprueba que esa acción esté disponible en el juego |

Incluye versión del port, modo de apertura, versión de Atmosphère y los registros
relevantes al [reportar un fallo](https://github.com/RadiantDelux/Finn-NX/issues/new?template=bug_report.yml).
No adjuntes APK ni partidas. Las [notas de pruebas](docs/TESTING.md) distinguen las
comprobaciones de PC de las pruebas que necesitan una consola.

## Desarrollo y créditos

- [Compilación](docs/BUILDING.md), [arquitectura](docs/ARCHITECTURE.md) e [historial de cambios](CHANGELOG.md).
- [Revisión de publicación y correcciones](docs/REVIEW.md).
- Basado en [aks796/android32](https://github.com/aks796/android32) y en la integración
  Unity/Mono de [aks796/dcr_sea_nx](https://github.com/aks796/dcr_sea_nx).
- El soporte AArch32 utiliza trabajo de xerpi/vita2hos, libnx32 y Mesa. El forwarder utiliza nx-hbloader.
- Atribución y licencias completas: [THIRD_PARTY.md](THIRD_PARTY.md).

El código del port y del runtime se distribuye con [licencia MIT](LICENSE),
conservando los avisos de terceros. El icono, los recursos del juego, sus nombres
y marcas pertenecen a sus respectivos propietarios.

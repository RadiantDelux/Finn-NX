<p align="center">
  <img src="docs/assets/icon.png" width="176" alt="Jumping Finn Turbo">
</p>

<h1 align="center">Finn NX</h1>
<p align="center">Jumping Finn Turbo / Finn Saltarín para Nintendo Switch</p>
<p align="center">
  <a href="https://github.com/RadiantDelux/Finn-NX/releases/latest"><b>Descargar</b></a> ·
  <a href="README.md">English</a> ·
  <a href="#controles">Controles</a> ·
  <a href="https://github.com/RadiantDelux/Finn-NX/issues">Reportar un fallo</a>
</p>

Port nativo no oficial de **Jumping Finn Turbo**, basado en su versión **Android 1.1.6**.
Port por [RadiantDelux](https://github.com/RadiantDelux).

## Características

- El código ARMv7 original del juego se ejecuta en la CPU de Switch mediante android32.
- Gráficos OpenGL ES mediante Mesa/Nouveau.
- Controles táctiles en portátil y soporte de mando para jugar en dock.
- Instalación automática del forwarder de HOME desde el NRO, también al abrir desde Álbum/hbmenu.

**El juego no está incluido. Debes aportar tu propio APK compatible.**

## Requisitos

- Nintendo Switch con Atmosphère, configurada para instalar y ejecutar forwarders homebrew.
- hbmenu o sphaira y espacio de escritura disponible en la SD.
- **Jumping Finn Turbo para Android, versión 1.1.6**, con estos datos exactos:

| APK | Valor requerido |
| --- | --- |
| Paquete | `com.turner.jft` |
| Arquitectura | `armeabi-v7a` (ARM de 32 bits) |
| Tamaño | 50.439.654 bytes |
| SHA-256 | Indicado debajo |

```text
7b3c4d0058c8f613b0a696fbbdd96b4fd0162e75d3ee85da11d9f38cf768d040
```

El nombre puede ser cualquiera que termine en `.apk`, también en mayúsculas.
Finn NX busca los APK de su carpeta y comprueba el SHA-256 completo. Otras
versiones y los APK modificados se rechazan.

<details>
<summary>Comprobar tu APK en Windows</summary>

```powershell
Get-FileHash -Algorithm SHA256 "C:\Juegos\JumpingFinnTurbo.apk"
```

</details>

## Instalación

1. Descarga **Finn-NX-0.1.11-SD.zip** desde [la última release](https://github.com/RadiantDelux/Finn-NX/releases/latest) y extráelo en la raíz de la SD.
2. Añade tu APK compatible a la misma carpeta que el NRO:

   ```text
   sd:/switch/finn_nx/
   ├── finn_nx.nro
   └── tu-juego.apk
   ```

3. Abre **Finn NX** desde Álbum/hbmenu. El NRO instala o reutiliza su forwarder de HOME e inicia el juego.
4. Deja terminar la extracción inicial de bibliotecas. Después puedes abrirlo desde el icono de HOME.

También puedes descargar `finn_nx.nro` por separado y crear la carpeta a mano.
No necesitas un NSP aparte. Tras el salto, el juego se ejecuta como **aplicación de
32 bits**; Unity no se ejecuta dentro del applet de Álbum.

Si falla la instalación automática, usa **Install Forwarder** en sphaira sobre el
NRO y abre el icono resultante desde HOME.

## Controles

| Entrada | Función |
| --- | --- |
| Pantalla táctil | Controles táctiles originales |
| **Y** | Patada de Jake en el aire |
| **X** | Recovery / rebote |
| **B** | Patada inicial: una pulsación inicia el medidor; otra realiza la patada |
| **B** durante el vuelo | Toques para meteorito, arcoíris, pájaros y hielo; mantener repite |
| **L / ZL** | Aplastar un pingüino visible de la izquierda |
| **R / ZR** | Aplastar un pingüino visible de la derecha |
| **−** | Reiniciar la run, conservando la partida |
| **+** | Menú de pausa |
| Stick izquierdo | Mover y mostrar el cursor rosado |
| **A** | Pulsar / arrastrar con el cursor, también en los menús |
| Clic del stick derecho | Atrás |
| **L + R + Plus** | Salir |

Las acciones respetan la disponibilidad y las recargas del juego. Otros botones
ocultan el cursor; **A** lo mantiene visible. Mueve el stick para volver a mostrarlo.

## Actualización y soporte

Sustituye `sd:/switch/finn_nx/finn_nx.nro` y abre Finn de nuevo. **Conserva el APK y
la carpeta `data/`**; las partidas están en `sd:/switch/finn_nx/data/`.

El NRO y el forwarder generado muestran **RadiantDelux** como autor. Para renovar
el autor o el icono de un forwarder antiguo de HOME, elimina ese forwarder desde
la gestión de programas y abre el nuevo NRO para reinstalarlo.

Si falla la instalación, revisa `forwarder-install.log` en la carpeta del juego.
Para una pantalla negra o un cierre, revisa `debug.log` y `crash.log`, si se genera.
Incluye la versión del port, la de Atmosphère, cómo lo abriste y los registros
relevantes en un [reporte de fallo](https://github.com/RadiantDelux/Finn-NX/issues/new?template=bug_report.yml).

## Compilar desde el código

El entorno admitido es Windows con PowerShell, devkitPro y Python nativo 3.10+:

```powershell
git clone https://github.com/RadiantDelux/Finn-NX.git
cd Finn-NX
./build.ps1 -ApkPath "C:\Juegos\JumpingFinnTurbo.apk"
```

La [guía de compilación](docs/BUILDING.md) detalla las herramientas y el empaquetado.
`tools/` contiene las herramientas de desarrollo; `tests/`, las pruebas de regresión.
[Arquitectura](docs/ARCHITECTURE.md) · [Pruebas](docs/TESTING.md) · [Contribuir](CONTRIBUTING.md)

## Créditos y licencia

- **RadiantDelux** — port de Finn NX, controles e integración del forwarder de HOME.
- **aks796** — [android32](https://github.com/aks796/android32), [dcr_sea_nx](https://github.com/aks796/dcr_sea_nx), libnx32 y mesa32.
- **xerpi**, **TheOfficialFloW**, **fgsfds** y **Switchbrew** — AArch32, cargador nativo y libnx.
- **Colaboradores de Mesa/Nouveau** — gráficos; **colaboradores de nx-hbloader** — cargador del forwarder.
- **Cartoon Network / Turner y los creadores originales** — juego e ilustraciones.

El código se distribuye con [licencia MIT](LICENSE), conservando los avisos de
terceros en [THIRD_PARTY.md](THIRD_PARTY.md) y en las descargas. Los recursos, los
nombres y las marcas del juego pertenecen a sus respectivos propietarios.
Finn NX es un proyecto comunitario no oficial.

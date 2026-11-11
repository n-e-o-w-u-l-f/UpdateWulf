<div align="center">

# UpdateWulf

### Tus actualizaciones. Tus sistemas. Tú decides.

**Consulta las actualizaciones pendientes de tus equipos. Inicia las actualizaciones nativas de paquetes cuando lo decidas.**

[Descargar](#download) · [Primeros pasos](#quick-start) · [Instalar](#installation) · [Manual](docs/manual.md) · [Solución de problemas](docs/troubleshooting.md)

[English](Readme.md) · [Deutsch](Readme.de.md) · [Français](Readme.fr.md) · [Русский](Readme.ru.md) · **Español** · [Polski](Readme.pl.md) · [Português](Readme.pt.md)

</div>

![Vista previa del terminal UpdateWulf con datos ilustrativos](docs/assets/terminal-preview.svg)

---

| Una vista conjunta | Control explícito | Actualización independiente de la aplicación |
| :--- | :--- | :--- |
| Estado almacenado en caché de los equipos registrados, incluidos los datos antiguos y los equipos sin conexión. | Una solicitud autenticada inicia el actualizador nativo de paquetes del equipo de destino. | UpdateWulf actualiza sus propios archivos desde su repositorio público de GitHub. |

<a id="at-a-glance"></a>

## De un vistazo

UpdateWulf es un servicio de Python y una herramienta de línea de comandos para un pequeño conjunto de equipos de confianza. Un hub HTTPS recibe los informes de actualizaciones; cada equipo registrado ejecuta un proceso de trabajo. La integración con el shell muestra los resultados en caché sin consultar la red cada vez que aparece el indicador de comandos.

El código público indica actualmente la **versión 2.1.0**. Incluye adaptadores para **APT, pacman, NetBSD pkgin y Windows Update Agent**. La cobertura de los adaptadores y de las pruebas nativas varía según la plataforma; consulta los [requisitos](#requirements) y el [registro de verificación](docs/documentation-status.md). Las siete traducciones del README **no** implican siete interfaces del programa totalmente traducidas: algunos mensajes siguen en alemán.

### Casos de uso

- Un laboratorio doméstico o un pequeño grupo de equipos cuyo estado de actualización quieras consultar en un solo terminal.
- Equipos Linux, Windows y NetBSD con sus gestores nativos de paquetes.
- Sesiones SSH en las que una línea de estado compacta sea más útil que un panel.
- Operadores que quieran decidir cuándo ejecutar las actualizaciones de paquetes y mantener los límites de privilegios del sistema operativo.

UpdateWulf no es un sistema de copias de seguridad ni una plataforma general de despliegue de software. No implementa winget, Flatpak, Snap, Homebrew ni la gestión automática de reinicios. La sincronización de repositorios se conserva como función de compatibilidad con instalaciones anteriores; las nuevas funciones de sincronización de Git corresponden a GitSyncWulf.

<a id="quick-start"></a>

## Primeros pasos

**Para explorar el programa:** utiliza Python 3.9+ y Git para la clonación que se muestra a continuación, o descarga y extrae primero el ZIP del código fuente. No se necesita ningún servicio ni configuración.

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git
cd UpdateWulf
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

En Windows, utiliza `py -3` en lugar de `python3` si ese es tu lanzador de Python.

**¿Ya está instalado y registrado?** Abre un terminal nuevo:

```sh
updatewulf status
updatewulf status --json
updatewulf diagnose
updatewulf --self update --check
```

`status` lee una instantánea local. `diagnose` comprueba el hub HTTPS configurado. `--self update --check` consulta la rama pública de la aplicación sin instalarla. Una instantánea vacía no demuestra que todos los equipos estén actualizados.

<a id="requirements"></a>

## Requisitos

| Plataforma | Entorno de ejecución y adaptador nativo | Método de instalación | Limitaciones actuales |
| :--- | :--- | :--- | :--- |
| Debian / Raspberry Pi OS | Python 3.9+, `apt-get` | Servicio de usuario; servicio de sistema systemd | Los análisis nuevos utilizan una caché de metadatos independiente. |
| Arch Linux | Python 3.9+, `pacman`, `vercmp` | Servicio de usuario; servicio de sistema systemd | Los metadatos de repositorios y las actualizaciones de paquetes necesitan acceso a la red. |
| Windows | Python 3.9+ con un `python.exe` real; Windows PowerShell y Windows Update Agent | Tarea programada de usuario; tareas de sistema con privilegios elevados | Sin adaptador winget; no se ejecutaron pruebas nativas de Windows durante esta sesión de documentación. |
| NetBSD | Python 3.9+, `pkgin` | Alternativa mediante cron de usuario; servicio nativo `rc.d` | Los análisis sin root pueden utilizar metadatos de pkgin en caché. |
| Android / Termux | Python 3.9+, APT, cuenta real de Termux | Script de arranque de Termux | Requiere Termux:Boot para iniciarse después de reiniciar; no actualiza el sistema Android. |
| Otras plataformas | Python puede ejecutar la CLI | Sin procedimiento completo de instalación nativa | Los recolectores no compatibles indican `UNSUPPORTED`, no cero actualizaciones. |

Todos los procesos de trabajo conectados a la red necesitan una configuración registrada, un hub HTTPS, su certificado de confianza, un token de miembro único y almacenamiento de estado con permiso de escritura. **Git es necesario para actualizar la propia aplicación.** La instalación de usuario en Unix necesita un gestor de servicios systemd de usuario operativo o `crontab`; `scripts/install.sh` requiere Bash. Los antiguos asistentes opcionales de registro utilizan Paramiko; el servicio principal utiliza la biblioteca estándar de Python.

<a id="download"></a>

## Descargar

- [Descargar el ZIP del código fuente actual](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip).
- [Explorar el código fuente](https://github.com/n-e-o-w-u-l-f/UpdateWulf).
- [Consultar las versiones publicadas](https://github.com/n-e-o-w-u-l-f/UpdateWulf/releases).

En el punto de referencia de esta documentación no había archivos de versiones etiquetadas ni instaladores MSI, EXE, DEB o PKG publicados. El ZIP sigue la rama cambiante `main`. Para una instalación reproducible desde un clon, registra el commit descargado con `git rev-parse HEAD`. No consideres el ZIP un instalador nativo firmado.

<a id="installation"></a>

## Instalación

### Elegir el alcance

| Necesitas… | Elige… | Qué cambia |
| :--- | :--- | :--- |
| Comandos y una línea de estado del shell para tu cuenta | Instalación de usuario | Tus lanzadores, los bloques administrados de los perfiles del shell y un proceso de trabajo de usuario opcional. |
| Un proceso que arranque con el equipo y pueda ejecutar actualizaciones autorizadas del sistema | Servicio de sistema | Servicio o tarea nativos, asistente protegido de actualización de paquetes y configuración explícita del propietario. |
| Solo explorar la herramienta | Copia del código fuente | Ejecuta `pc_mesh.py --help` / `--version`; no requiere instalación. |

**Configura primero el registro:** sigue la [configuración del hub y los miembros](docs/configuration.md#first-setup). Los archivos de [examples/](examples/) contienen valores de ejemplo que debes sustituir, no credenciales utilizables. Guarda la configuración completada fuera del árbol del código, normalmente en `~/.config/pc-mesh/config.json` (`%USERPROFILE%\.config\pc-mesh\config.json` en Windows). Mantén el directorio descargado del programa en una ubicación permanente: los instaladores apuntan a él.

### Instalar para tu usuario

Desde el directorio del código descargado, utiliza la cuenta que ejecutará UpdateWulf:

```sh
# Unix: instalar los scripts de lanzamiento, la integración con el shell y un proceso de usuario persistente.
python3 install.py
```

```powershell
# Windows PowerShell: usar el ejecutable real de Python, no un alias de Microsoft Store.
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
.\install_windows.ps1 -Python $Python
```

Para instalar solo la integración con el shell, utiliza `python3 install.py --prompt-only` o `.\install_windows.ps1 -Python $Python -PromptOnly`. Esta opción no recopila datos de estado nuevos: necesita la caché de un proceso de trabajo existente. En Termux se utiliza `python install_termux.py` dentro de la sesión real de Termux. Las actualizaciones de la aplicación en Termux requieren actualmente una sustitución manual mediante su instalador nativo; mantén `auto_self_update: false`, ya que el actualizador general no modifica su script de arranque.

Abre un terminal nuevo y ejecuta `updatewulf --version`, `updatewulf diagnose` y `updatewulf status`. La [guía de instalación](docs/installation.md) explica las rutas, el arranque, la verificación y la vuelta a la versión anterior.

### Instalar para todo el sistema

La instalación de sistema proporciona un proceso de trabajo nativo y privilegios controlados para actualizar paquetes; no configura automáticamente el shell de cada usuario. Prepara primero una cuenta de servicio dedicada y su configuración registrada. Utiliza una ruta permanente del código controlada por un administrador y sigue los pasos de transición de la plataforma:

- [Linux / systemd](docs/installation.md#linux-systemwide): `enable_machine_updates.py --user … --config … --state … --source …`, desde una sesión real de root.
- [Windows](docs/installation.md#windows-systemwide): `enable_machine_updates_windows.ps1 -Python … -Config … -Owner …`, desde una consola del propietario con privilegios elevados.
- [NetBSD](docs/installation.md#netbsd-systemwide): `enable_machine_updates_netbsd.py --config … --state … --python …`, desde una sesión real de root.

Estos instaladores no elevan sus propios privilegios. Una instalación gestionada por un servicio de sistema utiliza su procedimiento nativo de cambio de versión, no el instalador de actualización de usuario.

<a id="everyday-examples"></a>

## Ejemplos habituales

Sustituye `workstation.local` por un nombre de host notificado o registrado, o utiliza el ID exacto del miembro. Se aceptan tanto la sintaxis que comienza por el host como la que comienza por la acción.

| Objetivo | Comando | Efecto |
| :--- | :--- | :--- |
| Leer el estado del conjunto de equipos en caché | `updatewulf status` | Lectura local. |
| Consultar un equipo | `updatewulf workstation.local status` | Instantánea local filtrada. |
| Exportar el estado | `updatewulf status --json` | Instantánea sin procesar, incluidas las marcas de tiempo. |
| Desactivar los colores de la CLI | `updatewulf status --no-color` | Texto sin colores. |
| Diagnosticar la conexión | `updatewulf diagnose` | `GET /fleet` autenticado; no crea una tarea de actualización. |
| Solicitar un análisis nuevo | `updatewulf workstation.local refresh --wait 60` | Encola un análisis y espera hasta 60 segundos. |
| Instalar actualizaciones de paquetes del sistema | `updatewulf workstation.local update --wait 600` | Solicitud explícita de actualización nativa; requiere registro y privilegios en el destino. |
| Encolar sin esperar | `updatewulf workstation.local update --wait 0` | Muestra la tarea encolada; no demuestra que haya terminado. |
| Abrir el menú | `updatewulf tui` | Menú interactivo del operador; consulta el problema conocido cuando no hay equipos. |
| Comprobar el propio UpdateWulf | `updatewulf --self update --check` | Consulta la rama pública de la aplicación. |
| Actualizar el propio UpdateWulf | `updatewulf --self update` | Prepara, comprueba y activa el código de la aplicación para una instalación de usuario compatible. |

`updatewulf all update` solicita actualizaciones para **todos los destinos registrados**. Utilízalo solo cuando ese sea el alcance deseado. Un tiempo de espera agotado de la CLI no cancela un gestor de paquetes que ya se esté ejecutando. La referencia completa de acciones, opciones y códigos de salida está en el [manual](docs/manual.md).

<a id="configuration"></a>

## Configuración

La configuración está en JSON. Empieza con un ejemplo de [cliente](examples/config.client.json), [hub](examples/config.hub.json) u [operador](examples/control.json) y sigue la [referencia completa de configuración](docs/configuration.md). Las rutas JSON son literales: utiliza rutas absolutas; `~` y las variables de entorno no se expanden de forma general dentro de las cadenas JSON.

| Ajuste | Valor predeterminado en el código | Significado |
| :--- | :--- | :--- |
| `scan_interval` | `1800` segundos | Intervalo entre análisis de paquetes. |
| `report_interval` | `20` segundos | Intervalo entre informes al hub. |
| `auto_self_update` | `true` | Activa el actualizador de la aplicación cuando el modo del proceso de trabajo lo permite. |
| `self_update_interval` | `21600` segundos | Intervalo de comprobación de la aplicación; limitado a 1–24 horas, tras una espera inicial de 5 minutos. |
| `self_update_branch` | `main` | Rama pública de la aplicación. |
| `announce_only` | `false` | Desactiva el trabajo heredado de Git; con `machine_control: false`, también desactiva el procesamiento de solicitudes. |
| `machine_control` | `false` | Activa las solicitudes de análisis e instalación en el modo de solo anuncios. |
| `native_installer` | `false` | Envía las instalaciones a un asistente nativo previamente configurado. |

Los ejemplos establecen deliberadamente `auto_self_update: false` para que la primera configuración sea previsible. Actívalo después de verificar una instalación pública de usuario. Para los comandos del operador, `control.json` en la ruta predeterminada tiene prioridad sobre `config.json`; un `--config` explícito con otra ruta selecciona ese archivo. Las rutas personalizadas de configuración y estado tienen limitaciones durante la actualización de la aplicación, descritas en los [problemas conocidos](docs/troubleshooting.md#known-issues).

<a id="services-status-and-self-update"></a>

## Servicios, estado y actualización de la aplicación

El servicio de usuario se llama `updatewulf.service` en systemd o `UpdateWulf-User` en el Programador de tareas de Windows. Los nombres de los servicios de sistema son distintos; la [guía de instalación](docs/installation.md) los enumera. Los registros y las instantáneas suelen estar en `~/.local/state/pc-mesh/`, incluidos `service.log`, `heartbeat.json`, `fleet.json` y `executed-commands.json`.

El estado puede ser `OK`, `CACHED`, `CHECKING`, `UNKNOWN`, `ERROR` o `UNSUPPORTED`. Los datos en caché y los de equipos sin conexión siguen siendo visibles sin presentarse como un análisis nuevo completado correctamente. Las tareas tienen sus propios estados, incluidos `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_ADMIN`, `EXPIRED` e `INTERRUPTED`.

La actualización de la aplicación verifica la identidad del repositorio, la integridad y la ascendencia de los objetos Git, ejecuta las comprobaciones de la versión preparada y conserva la versión actual y la anterior. La verificación de Git no es un sistema de firma de versiones. La primera migración requiere un comando explícito del operador. La configuración y el registro existentes se guardan fuera del directorio de la versión. El [manual](docs/manual.md#application-self-update) explica la vuelta a una versión anterior y los límites conservadores de la limpieza.

<a id="known-issues-and-troubleshooting"></a>

## Problemas conocidos y solución de problemas

La [guía de problemas](docs/troubleshooting.md#known-issues) recoge limitaciones concretas y alternativas prácticas. Actualmente:

- No existe un desinstalador multiplataforma completo; sigue el [procedimiento de eliminación manual](docs/installation.md#uninstall).
- La actualización de usuario no conserva de forma fiable las rutas personalizadas de estado y configuración en Unix; utiliza las rutas predeterminadas o una transición nativa manual.
- La TUI puede fallar al navegar por un conjunto vacío de equipos; utiliza `status` y `diagnose` hasta registrar un miembro.
- La integración del indicador de Bash no respeta por completo `NO_COLOR`; utiliza `status --no-color` para garantizar una salida CLI sin colores.
- El contenido desconocido de una versión, incluidos directorios adicionales de documentación, impide por precaución la limpieza automática.
- Los adaptadores macOS/Homebrew, winget, Flatpak y Snap y la traducción completa del programa no están implementados.

Si no se encuentra un comando, abre un shell nuevo y comprueba el directorio de ejecutables del usuario. Para `NEEDS_ADMIN`, verifica el asistente nativo y el permiso `allow_install` del miembro. Ante errores TLS o de autenticación, verifica el certificado, el nombre de host y el registro. No interpretes una comprobación fallida como cero actualizaciones pendientes.

<a id="manual-and-project-information"></a>

## Manual e información del proyecto

| Documentación | Contenido |
| :--- | :--- |
| [Instalación](docs/installation.md) | Configuración de usuario/sistema, servicios, verificación, vuelta a la versión anterior y desinstalación. |
| [Manual](docs/manual.md) | Todas las acciones y opciones de la CLI, ejemplos, estados, registros y actualización de la aplicación. |
| [Configuración](docs/configuration.md) | Configuración del hub, miembros y operadores, claves, valores predeterminados, rutas y prioridades. |
| [Solución de problemas](docs/troubleshooting.md) | Síntomas, errores conocidos, soluciones prácticas y preguntas frecuentes. |
| [Verificación](docs/documentation-status.md) | Qué se comprobó y qué sigue necesitando una prueba nativa en la plataforma. |
| [Plantilla README](docs/README_TEMPLATE.md) | Estructura reutilizable de presentación de proyectos en siete idiomas. |
| [Investigación de diseño](docs/readme-design-research.md) | Diez README de referencia de fuentes primarias y las decisiones de diseño adoptadas. |

El manual técnico detallado se mantiene actualmente en inglés; cada uno de los siete README ofrece los mismos primeros pasos y la misma visión del funcionamiento en su idioma.

**Contribuir / obtener ayuda:** [abre una incidencia](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues) indicando el sistema operativo, la versión de Python, el commit de UpdateWulf, el comando exacto y la salida sin datos sensibles. No adjuntes nunca tokens, claves privadas ni archivos reales de configuración. Consulta las [comprobaciones para contribuir](docs/manual.md#contributing).

**Licencia:** el repositorio no contiene actualmente ningún archivo de licencia. Esta documentación no selecciona ni concede una licencia; consulta al mantenedor qué usos están permitidos.

---

<div align="center">

[Volver arriba](#updatewulf) · [Descargar el código fuente](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip) · [Leer el manual](docs/manual.md)

</div>

<div align="center">

# UpdateWulf

### Twoje aktualizacje. Twoje komputery. Twoja decyzja.

**Sprawdzaj oczekujące aktualizacje na swoich komputerach. Uruchamiaj aktualizacje pakietów za pomocą narzędzi systemowych wtedy, gdy zdecydujesz.**

[Pobierz](#download) · [Zacznij](#quick-start) · [Zainstaluj](#installation) · [Podręcznik](docs/manual.md) · [Rozwiązywanie problemów](docs/troubleshooting.md)

[English](Readme.md) · [Deutsch](Readme.de.md) · [Français](Readme.fr.md) · [Русский](Readme.ru.md) · [Español](Readme.es.md) · **Polski** · [Português](Readme.pt.md)

</div>

![Podgląd terminala UpdateWulf z przykładowymi danymi](docs/assets/terminal-preview.svg)

---

| Wspólny widok | Działanie na wyraźne żądanie | Osobna aktualizacja aplikacji |
| :--- | :--- | :--- |
| Zapisany stan zarejestrowanych komputerów, z oznaczeniem nieaktualnych danych i niedostępnych urządzeń. | Uwierzytelnione żądanie uruchamia systemowe narzędzie aktualizacji pakietów na komputerze docelowym. | UpdateWulf aktualizuje własne pliki programu z publicznego repozytorium GitHub. |

## Najważniejsze informacje

UpdateWulf to usługa i narzędzie wiersza poleceń napisane w Pythonie, przeznaczone dla niewielkiej grupy zaufanych komputerów. Centralny węzeł HTTPS odbiera raporty o aktualizacjach, a na każdym zarejestrowanym komputerze działa proces roboczy. Integracja z powłoką wyświetla zapisane wyniki bez odpytywania sieci przy każdym wyświetleniu znaku zachęty.

Publiczny kod źródłowy zgłasza obecnie **wersję 2.1.0**. Zawiera adaptery dla **APT, pacman, NetBSD pkgin i Windows Update Agent**. Zakres implementacji adapterów i testów akceptacyjnych na poszczególnych platformach jest różny; zobacz [wymagania](#requirements) i [zapis weryfikacji](docs/documentation-status.md). Siedem tłumaczeń README **nie oznacza** siedmiu w pełni przetłumaczonych interfejsów programu: niektóre komunikaty podczas działania nadal są po niemiecku.

### Zastosowania

- Domowe laboratorium lub niewielka grupa komputerów, których stan aktualizacji chcesz widzieć w jednym terminalu.
- Komputery z Linuksem, Windows i NetBSD korzystające z istniejących systemowych menedżerów pakietów.
- Sesje SSH, w których zwięzły wiersz stanu jest przydatniejszy niż osobny panel.
- Operatorzy, którzy chcą wybierać moment aktualizacji pakietów i zachować istniejące ograniczenia uprawnień systemu operacyjnego.

UpdateWulf nie jest systemem kopii zapasowych ani uniwersalną platformą wdrażania oprogramowania. Nie obsługuje winget, Flatpak, Snap, Homebrew ani automatycznego zarządzania restartami. Synchronizacja repozytoriów pozostaje funkcją zgodności ze starszymi wersjami; nowe zadania synchronizacji Git należą do GitSyncWulf.

<a id="quick-start"></a>
## Szybki start

**Chcesz tylko poznać program?** Potrzebujesz Python 3.9+ oraz Git do pokazanego poniżej klonowania; zamiast Git możesz najpierw pobrać i rozpakować ZIP kodu źródłowego. Nie potrzebujesz usługi ani konfiguracji.

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git
cd UpdateWulf
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

W Windows użyj `py -3` zamiast `python3`, jeśli tak uruchamiasz Pythona.

**Program jest już zainstalowany, a komputer zarejestrowany?** Otwórz nowy terminal:

```sh
updatewulf status
updatewulf status --json
updatewulf diagnose
updatewulf --self update --check
```

`status` odczytuje lokalny zapis stanu. `diagnose` sprawdza skonfigurowany węzeł HTTPS. `--self update --check` sprawdza publiczną gałąź aplikacji bez instalacji. Pusty zapis nie dowodzi, że wszystkie komputery są aktualne.

<a id="requirements"></a>
## Wymagania

| Platforma | Środowisko uruchomieniowe i adapter systemowy | Sposób instalacji | Obecne ograniczenia |
| :--- | :--- | :--- | :--- |
| Debian / Raspberry Pi OS | Python 3.9+, `apt-get` | Usługa użytkownika; usługa systemowa systemd | Nowe skanowanie używa osobnej pamięci podręcznej metadanych. |
| Arch Linux | Python 3.9+, `pacman`, `vercmp` | Usługa użytkownika; usługa systemowa systemd | Metadane repozytoriów i aktualizacje pakietów wymagają dostępu do sieci. |
| Windows | Python 3.9+ z rzeczywistym `python.exe`; Windows PowerShell i Windows Update Agent | Zadanie użytkownika; zadania systemowe z podwyższonymi uprawnieniami | Brak adaptera winget; podczas tej pracy nad dokumentacją nie wykonano testów bezpośrednio w Windows. |
| NetBSD | Python 3.9+, `pkgin` | Cron użytkownika jako mechanizm zastępczy; systemowa usługa `rc.d` | Skanowanie bez uprawnień root może korzystać z zapisanych metadanych pkgin. |
| Android / Termux | Python 3.9+, APT, rzeczywiste konto Termux | Skrypt startowy Termux | Uruchamianie po restarcie wymaga Termux:Boot; nie jest to narzędzie aktualizacji systemu Android. |
| Inne platformy | Python może uruchomić interfejs wiersza poleceń | Brak kompletnej instrukcji instalacji systemowej | Nieobsługiwane mechanizmy zbierania danych zgłaszają `UNSUPPORTED`, a nie zero aktualizacji. |

Każdy sieciowy proces roboczy potrzebuje konfiguracji rejestracji, węzła HTTPS, jego zaufanego certyfikatu, unikatowego tokenu uczestnika oraz katalogu stanu z prawem zapisu. **Samoaktualizacja aplikacji wymaga Git.** Instalacja użytkownika w Uniksie wymaga działającego menedżera usług użytkownika systemd albo `crontab`; skrypt `scripts/install.sh` wymaga Bash. Opcjonalne starsze narzędzia pomocnicze rejestracji używają Paramiko; podstawowa usługa korzysta ze standardowej biblioteki Pythona.

<a id="download"></a>
## Pobieranie

- [Pobierz bieżący kod źródłowy w ZIP](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip).
- [Przeglądaj kod źródłowy](https://github.com/n-e-o-w-u-l-f/UpdateWulf).
- [Sprawdź opublikowane wydania](https://github.com/n-e-o-w-u-l-f/UpdateWulf/releases).

W wersji bazowej sprawdzonej dla tej dokumentacji nie opublikowano plików wydań oznaczonych tagami ani instalatorów MSI, EXE, DEB czy PKG. ZIP odpowiada zmieniającej się gałęzi `main`. Aby instalacja była odtwarzalna, przy korzystaniu z klonu zapisz commit poleceniem `git rev-parse HEAD`. ZIP nie jest podpisanym instalatorem systemowym.

<a id="installation"></a>
## Instalacja

### Wybierz zakres

| Potrzebujesz… | Wybierz… | Co się zmieni |
| :--- | :--- | :--- |
| Poleceń i wiersza stanu powłoki dla swojego konta | Instalację użytkownika | Twoje skrypty uruchamiające, zarządzane bloki w profilach powłok i opcjonalny proces roboczy użytkownika. |
| Procesu uruchamianego wraz z komputerem, który może wykonywać autoryzowane aktualizacje systemu | Usługę ogólnosystemową | Systemowa usługa lub zadanie, chroniony komponent aktualizacji pakietów i jawnie określona konfiguracja właściciela. |
| Tylko obejrzeć narzędzie | Kopię kodu źródłowego | Uruchom `pc_mesh.py --help` / `--version`; instalacja nie jest potrzebna. |

**Najpierw skonfiguruj rejestrację:** postępuj według [instrukcji konfiguracji centralnego węzła i uczestników](docs/configuration.md#first-setup). Przykłady w [examples/](examples/) zawierają wartości zastępcze, a nie działające dane uwierzytelniające. Gotową konfigurację przechowuj poza drzewem źródeł, zwykle w `~/.config/pc-mesh/config.json` (`%USERPROFILE%\.config\pc-mesh\config.json` w Windows). Umieść pobrany katalog programu w stałej lokalizacji: instalatory tworzą odwołania do niego.

### Instalacja dla bieżącego użytkownika

Uruchom polecenia z katalogu pobranego kodu źródłowego, używając konta, które będzie korzystać z UpdateWulf:

```sh
# Unix: zainstaluj skrypty uruchamiające, integrację z powłoką i trwały proces roboczy użytkownika.
python3 install.py
```

```powershell
# Windows PowerShell: użyj rzeczywistego pliku wykonywalnego Pythona, a nie aliasu Microsoft Store.
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
.\install_windows.ps1 -Python $Python
```

Aby zainstalować samą integrację z powłoką, użyj `python3 install.py --prompt-only` albo `.\install_windows.ps1 -Python $Python -PromptOnly`. Ten tryb nie zbiera nowych danych: potrzebuje pamięci podręcznej istniejącego procesu roboczego. W Termux uruchom `python install_termux.py` bezpośrednio w sesji Termux. Aktualizacja aplikacji w Termux wymaga obecnie ręcznej wymiany przez jego własny instalator; pozostaw `auto_self_update: false`, ponieważ ogólny mechanizm aktualizacji nie zmienia skryptu startowego Termux.

Otwórz nowy terminal i wykonaj `updatewulf --version`, `updatewulf diagnose` oraz `updatewulf status`. [Instrukcja instalacji](docs/installation.md) opisuje ścieżki, uruchamianie, weryfikację i przywracanie poprzedniej wersji.

### Instalacja ogólnosystemowa

Instalacja ogólnosystemowa oznacza systemowy proces roboczy i kontrolowane uprawnienia do aktualizacji pakietów; nie konfiguruje automatycznie powłoki każdego użytkownika. Najpierw przygotuj osobne konto usługi i jego konfigurację rejestracji. Użyj stałej lokalizacji źródeł kontrolowanej przez administratora i wykonaj właściwe dla platformy kroki przełączenia:

- [Linux / systemd](docs/installation.md#linux-systemwide): `enable_machine_updates.py --user … --config … --state … --source …`, w rzeczywistej sesji root.
- [Windows](docs/installation.md#windows-systemwide): `enable_machine_updates_windows.ps1 -Python … -Config … -Owner …`, w konsoli właściciela z podwyższonymi uprawnieniami.
- [NetBSD](docs/installation.md#netbsd-systemwide): `enable_machine_updates_netbsd.py --config … --state … --python …`, w rzeczywistej sesji root.

Te instalatory nie podnoszą samodzielnie swoich uprawnień. Instalacja zarządzana przez usługę systemową korzysta z systemowej procedury przełączenia wydania, a nie z instalatora samoaktualizacji użytkownika.

## Przykłady codziennego użycia

Zastąp `workstation.local` zgłoszoną lub zarejestrowaną nazwą komputera albo użyj dokładnego identyfikatora uczestnika. Akceptowane są oba porządki: najpierw komputer albo najpierw działanie.

| Cel | Polecenie | Działanie |
| :--- | :--- | :--- |
| Odczyt zapisanego stanu wszystkich komputerów | `updatewulf status` | Odczyt lokalny. |
| Odczyt jednego komputera | `updatewulf workstation.local status` | Lokalny zapis z filtrowaniem. |
| Eksport stanu | `updatewulf status --json` | Surowe dane, w tym znaczniki czasu. |
| Wyłączenie kolorów CLI | `updatewulf status --no-color` | Zwykły tekst. |
| Diagnoza połączenia | `updatewulf diagnose` | Uwierzytelnione `GET /fleet`; bez zadania aktualizacji. |
| Żądanie nowego skanowania | `updatewulf workstation.local refresh --wait 60` | Kolejkuje skanowanie i czeka maksymalnie 60 sekund. |
| Instalacja aktualizacji pakietów systemu | `updatewulf workstation.local update --wait 600` | Jawne żądanie aktualizacji systemowej; wymaga rejestracji i odpowiednich uprawnień na celu. |
| Kolejkowanie bez oczekiwania | `updatewulf workstation.local update --wait 0` | Wyświetla zakolejkowane zadanie; nie potwierdza jego ukończenia. |
| Otwarcie menu | `updatewulf tui` | Interaktywne menu operatora; zobacz znany problem pustej listy komputerów. |
| Sprawdzenie samego UpdateWulf | `updatewulf --self update --check` | Sprawdza publiczną gałąź aplikacji. |
| Aktualizacja samego UpdateWulf | `updatewulf --self update` | Przygotowuje, sprawdza i aktywuje źródła aplikacji dla obsługiwanej instalacji użytkownika. |

`updatewulf all update` żąda aktualizacji **wszystkich zarejestrowanych komputerów docelowych**. Użyj tego polecenia tylko wtedy, gdy taki jest zamierzony zakres. Upłynięcie limitu oczekiwania CLI nie anuluje działającego menedżera pakietów. Pełną listę działań, opcji i kodów wyjścia znajdziesz w [podręczniku](docs/manual.md).

## Konfiguracja

Konfiguracja ma format JSON. Zacznij od przykładu [klienta](examples/config.client.json), [centralnego węzła](examples/config.hub.json) albo [operatora](examples/control.json), a następnie skorzystaj z [pełnego opisu konfiguracji](docs/configuration.md). Ścieżki w JSON są traktowane dosłownie: używaj ścieżek bezwzględnych; `~` i zmienne środowiskowe zwykle nie są rozwijane wewnątrz ciągów JSON.

| Ustawienie | Wartość domyślna w kodzie | Znaczenie |
| :--- | :--- | :--- |
| `scan_interval` | `1800` sekund | Czas między skanowaniami pakietów. |
| `report_interval` | `20` sekund | Czas między raportami do centralnego węzła. |
| `auto_self_update` | `true` | Włącza aktualizator aplikacji tam, gdzie pozwala na to tryb procesu roboczego. |
| `self_update_interval` | `21600` sekund | Odstęp sprawdzania aplikacji, ograniczony do 1–24 godzin, po początkowym oczekiwaniu 5 minut. |
| `self_update_branch` | `main` | Publiczna gałąź aplikacji. |
| `announce_only` | `false` | Wyłącza starsze funkcje Git; przy `machine_control: false` wyłącza również proces obsługi żądań. |
| `machine_control` | `false` | Włącza żądania skanowania i instalacji w trybie announce-only. |
| `native_installer` | `false` | Kieruje instalacje przez wcześniej przygotowany systemowy komponent pomocniczy. |

Przykłady celowo ustawiają `auto_self_update: false`, aby pierwsza konfiguracja była przewidywalna. Włącz tę funkcję po sprawdzeniu instalacji użytkownika z publicznego repozytorium. Dla poleceń operatora plik `control.json` w domyślnej lokalizacji ma pierwszeństwo przed `config.json`; jawny, niestandardowy `--config` wybiera wskazany plik. Ograniczenia samoaktualizacji przy niestandardowych ścieżkach konfiguracji i stanu opisano w [znanych problemach](docs/troubleshooting.md#known-issues).

## Usługi, stan i samoaktualizacja

Usługa użytkownika nazywa się `updatewulf.service` w systemd albo `UpdateWulf-User` w Harmonogramie zadań Windows. Nazwy usług systemowych są różne; wymienia je [instrukcja instalacji](docs/installation.md). Logi i zapisane stany zwykle znajdują się w `~/.local/state/pc-mesh/`, w tym `service.log`, `heartbeat.json`, `fleet.json` oraz `executed-commands.json`.

Możliwe stany to `OK`, `CACHED`, `CHECKING`, `UNKNOWN`, `ERROR` i `UNSUPPORTED`. Zapisane dane, także dotyczące niedostępnych komputerów, pozostają widoczne bez przedstawiania ich jako nowego, udanego skanowania. Zadania mają własne stany, w tym `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_ADMIN`, `EXPIRED` oraz `INTERRUPTED`.

Samoaktualizacja sprawdza tożsamość repozytorium, integralność obiektów Git i relację przodków między commitami, uruchamia kontrole przygotowanego kodu oraz zachowuje obecne i poprzednie wydanie. Weryfikacja Git nie jest systemem podpisów wydań. Pierwsza migracja wymaga jawnego polecenia operatora. Istniejąca konfiguracja i dane rejestracji znajdują się poza katalogiem wydania. Przywracanie wersji oraz zachowawcze ograniczenia czyszczenia opisano w [podręczniku](docs/manual.md#application-self-update).

## Znane błędy i rozwiązywanie problemów

[Poradnik problemów](docs/troubleshooting.md#known-issues) opisuje konkretne ograniczenia i sposoby obejścia. Obecnie:

- Brak kompletnego deinstalatora dla wszystkich platform; skorzystaj z [procedury ręcznego usuwania](docs/installation.md#uninstall).
- Samoaktualizacja użytkownika nie zawsze zachowuje niestandardowe ścieżki stanu i konfiguracji w Uniksie; używaj ścieżek domyślnych albo ręcznej procedury przełączenia systemowego.
- TUI może ulec awarii przy poruszaniu się po pustej liście komputerów; do czasu zarejestrowania uczestnika używaj `status` i `diagnose`.
- Integracja znaku zachęty Bash nie uwzględnia w pełni `NO_COLOR`; użyj `status --no-color`, aby zagwarantować zwykły, niekolorowany wynik CLI.
- Nieznana zawartość wydania, w tym dodatkowe katalogi dokumentacji, z ostrożności blokuje automatyczne usuwanie starych wydań.
- Adaptery macOS/Homebrew, winget, Flatpak i Snap oraz pełne tłumaczenie komunikatów programu nie są zaimplementowane.

Jeśli polecenie nie jest odnajdywane, otwórz nową powłokę i sprawdź katalog plików wykonywalnych użytkownika. Przy `NEEDS_ADMIN` sprawdź systemowy komponent pomocniczy oraz uprawnienie `allow_install` uczestnika. Przy błędach TLS lub uwierzytelniania sprawdź certyfikat, nazwę komputera i rejestrację. Nie zastępuj nieudanej kontroli założeniem, że liczba aktualizacji wynosi zero.

## Podręcznik i informacje o projekcie

| Dokumentacja | Zawartość |
| :--- | :--- |
| [Instalacja](docs/installation.md) | Konfiguracja użytkownika i systemu, usługi, weryfikacja, przywracanie wersji i usuwanie. |
| [Podręcznik](docs/manual.md) | Wszystkie działania i opcje CLI, przykłady, stany, logi i samoaktualizacja. |
| [Konfiguracja](docs/configuration.md) | Konfiguracja węzła centralnego, uczestnika i operatora, klucze, wartości domyślne, ścieżki i pierwszeństwo. |
| [Rozwiązywanie problemów](docs/troubleshooting.md) | Objawy, znane błędy, praktyczne obejścia i FAQ. |
| [Weryfikacja](docs/documentation-status.md) | Co sprawdzono i gdzie nadal potrzebny jest test na docelowej platformie. |
| [Szablon README](docs/README_TEMPLATE.md) | Standard prezentacji projektu w siedmiu językach do ponownego wykorzystania. |
| [Badanie projektów README](docs/readme-design-research.md) | Dziesięć wzorców README z pierwotnych źródeł i przyjęte decyzje dotyczące wyglądu. |

Szczegółowy podręcznik techniczny jest obecnie prowadzony po angielsku; każdy z siedmiu plików README zawiera ten sam przetłumaczony przegląd uruchomienia i obsługi.

**Współpraca / pomoc:** [otwórz zgłoszenie](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues), podając system operacyjny, wersję Pythona, commit UpdateWulf, dokładne polecenie i wynik pozbawiony danych poufnych. Nigdy nie załączaj tokenów, kluczy prywatnych ani używanych plików konfiguracji. Zobacz [kontrole dla współtwórców](docs/manual.md#contributing).

**Licencja:** repozytorium nie zawiera obecnie pliku licencji. Ta dokumentacja nie wybiera ani nie udziela licencji; zapytaj opiekuna projektu o dozwolone ponowne wykorzystanie.

---

<div align="center">

[Na górę](#updatewulf) · [Pobierz źródła](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip) · [Czytaj podręcznik](docs/manual.md)

</div>

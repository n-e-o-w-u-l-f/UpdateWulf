<div align="center">

# UpdateWulf

### As suas atualizações. Os seus sistemas. A sua decisão.

**Consulte as atualizações pendentes nos seus computadores. Inicie as atualizações nativas de pacotes quando decidir.**

[Descarregar](#download) · [Primeiros passos](#quick-start) · [Instalar](#installation) · [Manual](docs/manual.md) · [Resolução de problemas](docs/troubleshooting.md)

[English](Readme.md) · [Deutsch](Readme.de.md) · [Français](Readme.fr.md) · [Русский](Readme.ru.md) · [Español](Readme.es.md) · [Polski](Readme.pl.md) · **Português**

</div>

![Pré-visualização do terminal UpdateWulf com dados ilustrativos](docs/assets/terminal-preview.svg)

---

| Uma vista conjunta | Controlo explícito | Atualização separada da aplicação |
| :--- | :--- | :--- |
| Estado em cache dos computadores registados, incluindo dados antigos e equipamentos sem ligação. | Um pedido autenticado inicia o atualizador nativo de pacotes do computador de destino. | O UpdateWulf atualiza os seus próprios ficheiros a partir do repositório público no GitHub. |

<a id="at-a-glance"></a>

## Visão geral

O UpdateWulf é um serviço Python e uma ferramenta de linha de comandos para um pequeno conjunto de computadores de confiança. Um hub HTTPS recebe relatórios de atualizações; cada computador registado executa um processo de trabalho. A integração com o shell apresenta os resultados em cache sem contactar a rede sempre que surge o prompt.

O código público indica atualmente a **versão 2.1.0**. Inclui adaptadores para **APT, pacman, NetBSD pkgin e Windows Update Agent**. A cobertura dos adaptadores e dos testes nativos varia consoante a plataforma; consulte os [requisitos](#requirements) e o [registo de verificação](docs/documentation-status.md). As sete traduções do README **não** significam sete interfaces do programa totalmente traduzidas: algumas mensagens continuam em alemão.

### Casos de utilização

- Um laboratório doméstico ou um pequeno conjunto de equipamentos cujas atualizações queira consultar num único terminal.
- Computadores Linux, Windows e NetBSD com os seus gestores nativos de pacotes.
- Sessões SSH em que uma linha de estado compacta seja mais útil do que um painel.
- Operadores que pretendam escolher quando executar atualizações de pacotes e manter os limites de privilégios do sistema operativo.

O UpdateWulf não é um sistema de cópias de segurança nem uma plataforma geral de distribuição de software. Não implementa winget, Flatpak, Snap, Homebrew ou gestão automática de reinícios. A sincronização de repositórios mantém-se como função de compatibilidade com instalações anteriores; as novas funções de sincronização Git pertencem ao GitSyncWulf.

<a id="quick-start"></a>

## Primeiros passos

**Para explorar o programa:** utilize Python 3.9+ e Git para a clonagem abaixo, ou descarregue e extraia primeiro o ZIP do código-fonte. Não é necessário qualquer serviço ou configuração.

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git
cd UpdateWulf
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

No Windows, utilize `py -3` em vez de `python3` se esse for o seu lançador Python.

**Já está instalado e registado?** Abra um novo terminal:

```sh
updatewulf status
updatewulf status --json
updatewulf diagnose
updatewulf --self update --check
```

`status` lê uma imagem local do estado. `diagnose` verifica o hub HTTPS configurado. `--self update --check` consulta o ramo público da aplicação sem o instalar. Uma imagem de estado vazia não prova que todos os computadores estejam atualizados.

<a id="requirements"></a>

## Requisitos

| Plataforma | Ambiente de execução e adaptador nativo | Método de instalação | Limitações atuais |
| :--- | :--- | :--- | :--- |
| Debian / Raspberry Pi OS | Python 3.9+, `apt-get` | Serviço de utilizador; serviço de sistema systemd | As novas análises utilizam uma cache de metadados separada. |
| Arch Linux | Python 3.9+, `pacman`, `vercmp` | Serviço de utilizador; serviço de sistema systemd | Os metadados dos repositórios e as atualizações dos pacotes necessitam de acesso à rede. |
| Windows | Python 3.9+ com um `python.exe` real; Windows PowerShell e Windows Update Agent | Tarefa agendada de utilizador; tarefas de sistema com privilégios elevados | Sem adaptador winget; os testes nativos do Windows não foram executados nesta sessão de documentação. |
| NetBSD | Python 3.9+, `pkgin` | Alternativa com cron de utilizador; serviço nativo `rc.d` | As análises sem root podem utilizar metadados pkgin em cache. |
| Android / Termux | Python 3.9+, APT, conta real do Termux | Script de arranque do Termux | Requer Termux:Boot para arrancar após reiniciar; não atualiza o sistema Android. |
| Outras plataformas | O Python poderá executar a CLI | Sem procedimento completo de instalação nativa | Os coletores não suportados apresentam `UNSUPPORTED`, não zero atualizações. |

Todos os processos de trabalho ligados à rede necessitam de uma configuração registada, de um hub HTTPS, do respetivo certificado de confiança, de um token de membro único e de armazenamento de estado com permissão de escrita. **O Git é necessário para atualizar a própria aplicação.** A instalação de utilizador em Unix requer um gestor de serviços systemd de utilizador funcional ou `crontab`; `scripts/install.sh` requer Bash. Os antigos utilitários opcionais de registo usam Paramiko; o serviço principal utiliza a biblioteca padrão do Python.

<a id="download"></a>

## Descarregar

- [Descarregar o ZIP do código-fonte atual](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip).
- [Explorar o código-fonte](https://github.com/n-e-o-w-u-l-f/UpdateWulf).
- [Consultar as versões publicadas](https://github.com/n-e-o-w-u-l-f/UpdateWulf/releases).

No ponto de referência desta documentação não existiam ficheiros publicados de versões etiquetadas nem instaladores MSI, EXE, DEB ou PKG. O ZIP acompanha o ramo `main`, que continua a evoluir. Para uma instalação reproduzível a partir de um clone, registe o commit descarregado com `git rev-parse HEAD`. Não trate o ZIP como um instalador nativo assinado.

<a id="installation"></a>

## Instalação

### Escolher o âmbito

| Precisa de… | Escolha… | O que muda |
| :--- | :--- | :--- |
| Comandos e uma linha de estado do shell para a sua conta | Instalação de utilizador | Os seus lançadores, blocos geridos nos perfis do shell e um processo de trabalho de utilizador opcional. |
| Um processo que arranque com o computador e possa executar atualizações autorizadas do sistema | Serviço de sistema | Serviço ou tarefa nativos, utilitário protegido de atualização de pacotes e configuração explícita do proprietário. |
| Apenas explorar a ferramenta | Cópia do código-fonte | Execute `pc_mesh.py --help` / `--version`; não é necessário instalar. |

**Configure primeiro o registo:** siga a [configuração do hub e dos membros](docs/configuration.md#first-setup). Os ficheiros em [examples/](examples/) contêm valores a substituir, não credenciais utilizáveis. Guarde a configuração preenchida fora da árvore do código, normalmente em `~/.config/pc-mesh/config.json` (`%USERPROFILE%\.config\pc-mesh\config.json` no Windows). Mantenha o diretório descarregado do programa numa localização permanente: os instaladores apontam para esse diretório.

### Instalar para o seu utilizador

No diretório do código descarregado, utilize a conta que irá executar o UpdateWulf:

```sh
# Unix: instalar os scripts de lançamento, a integração com o shell e um processo de utilizador persistente.
python3 install.py
```

```powershell
# Windows PowerShell: utilizar o executável real do Python, não um alias da Microsoft Store.
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
.\install_windows.ps1 -Python $Python
```

Para instalar apenas a integração com o shell, utilize `python3 install.py --prompt-only` ou `.\install_windows.ps1 -Python $Python -PromptOnly`. Esta opção não recolhe novos dados de estado: precisa da cache de um processo de trabalho existente. No Termux, utilize `python install_termux.py` na sessão real do Termux. As atualizações da aplicação no Termux exigem atualmente uma substituição manual através do instalador nativo; mantenha `auto_self_update: false`, pois o atualizador geral não modifica o script de arranque.

Abra um novo terminal e execute `updatewulf --version`, `updatewulf diagnose` e `updatewulf status`. O [guia de instalação](docs/installation.md) explica os caminhos, o arranque, a verificação e a reposição da versão anterior.

### Instalar para todo o sistema

A instalação de sistema fornece um processo de trabalho nativo e privilégios controlados para atualizar pacotes; não configura automaticamente o shell de todos os utilizadores. Prepare primeiro uma conta de serviço dedicada e a respetiva configuração registada. Utilize um caminho permanente do código controlado pelo administrador e siga os passos de transição específicos da plataforma:

- [Linux / systemd](docs/installation.md#linux-systemwide): `enable_machine_updates.py --user … --config … --state … --source …`, numa sessão root real.
- [Windows](docs/installation.md#windows-systemwide): `enable_machine_updates_windows.ps1 -Python … -Config … -Owner …`, numa consola do proprietário com privilégios elevados.
- [NetBSD](docs/installation.md#netbsd-systemwide): `enable_machine_updates_netbsd.py --config … --state … --python …`, numa sessão root real.

Estes instaladores não elevam os próprios privilégios. Uma instalação gerida por um serviço de sistema utiliza o seu procedimento nativo de transição de versão, não o instalador de atualização ao nível do utilizador.

<a id="everyday-examples"></a>

## Exemplos de utilização

Substitua `workstation.local` por um nome de host comunicado ou registado, ou utilize o ID exato do membro. São aceites tanto a sintaxe que começa pelo host como a que começa pela ação.

| Objetivo | Comando | Efeito |
| :--- | :--- | :--- |
| Ler o estado dos equipamentos em cache | `updatewulf status` | Leitura local. |
| Consultar um computador | `updatewulf workstation.local status` | Imagem local do estado, filtrada. |
| Exportar o estado | `updatewulf status --json` | Dados de estado em bruto, incluindo marcas de tempo. |
| Desativar as cores da CLI | `updatewulf status --no-color` | Texto sem cores. |
| Diagnosticar a ligação | `updatewulf diagnose` | `GET /fleet` autenticado; não cria uma tarefa de atualização. |
| Pedir uma nova análise | `updatewulf workstation.local refresh --wait 60` | Coloca uma análise na fila e espera até 60 segundos. |
| Instalar atualizações de pacotes do sistema | `updatewulf workstation.local update --wait 600` | Pedido explícito de atualização nativa; requer registo e privilégios no destino. |
| Colocar na fila sem esperar | `updatewulf workstation.local update --wait 0` | Apresenta a tarefa na fila; não prova a sua conclusão. |
| Abrir o menu | `updatewulf tui` | Menu interativo do operador; consulte o problema conhecido quando não há equipamentos. |
| Verificar o próprio UpdateWulf | `updatewulf --self update --check` | Consulta o ramo público da aplicação. |
| Atualizar o próprio UpdateWulf | `updatewulf --self update` | Prepara, verifica e ativa o código da aplicação para uma instalação de utilizador suportada. |

`updatewulf all update` pede atualizações para **todos os destinos registados**. Utilize-o apenas quando esse for o âmbito pretendido. O fim do tempo de espera da CLI não cancela um gestor de pacotes que já esteja em execução. A referência completa de ações, opções e códigos de saída está no [manual](docs/manual.md).

<a id="configuration"></a>

## Configuração

A configuração está em JSON. Comece por um exemplo de [cliente](examples/config.client.json), [hub](examples/config.hub.json) ou [operador](examples/control.json) e siga a [referência completa de configuração](docs/configuration.md). Os caminhos JSON são literais: utilize caminhos absolutos; `~` e as variáveis de ambiente não são normalmente expandidos dentro das cadeias JSON.

| Definição | Valor predefinido no código | Significado |
| :--- | :--- | :--- |
| `scan_interval` | `1800` segundos | Intervalo entre análises de pacotes. |
| `report_interval` | `20` segundos | Intervalo entre relatórios enviados ao hub. |
| `auto_self_update` | `true` | Ativa a atualização da aplicação quando o modo do processo de trabalho o permite. |
| `self_update_interval` | `21600` segundos | Intervalo de verificação da aplicação; limitado a 1–24 horas, após uma espera inicial de 5 minutos. |
| `self_update_branch` | `main` | Ramo público da aplicação. |
| `announce_only` | `false` | Desativa o processamento Git legado; com `machine_control: false`, também desativa o processamento de pedidos. |
| `machine_control` | `false` | Ativa pedidos de análise e instalação no modo apenas de anúncios. |
| `native_installer` | `false` | Encaminha as instalações para um utilitário nativo previamente configurado. |

Os exemplos definem deliberadamente `auto_self_update: false` para tornar a primeira configuração previsível. Ative esta opção depois de verificar uma instalação pública de utilizador. Nos comandos do operador, `control.json` no caminho predefinido tem prioridade sobre `config.json`; um `--config` explícito com outro caminho seleciona esse ficheiro. Os caminhos personalizados de configuração e estado têm limitações durante a atualização da aplicação, descritas nos [problemas conhecidos](docs/troubleshooting.md#known-issues).

<a id="services-status-and-self-update"></a>

## Serviços, estado e atualização da aplicação

O serviço de utilizador chama-se `updatewulf.service` no systemd ou `UpdateWulf-User` no Agendador de Tarefas do Windows. Os nomes dos serviços de sistema são diferentes; o [guia de instalação](docs/installation.md) enumera cada um. Os registos e as imagens do estado ficam normalmente em `~/.local/state/pc-mesh/`, incluindo `service.log`, `heartbeat.json`, `fleet.json` e `executed-commands.json`.

O estado pode ser `OK`, `CACHED`, `CHECKING`, `UNKNOWN`, `ERROR` ou `UNSUPPORTED`. Os dados em cache e os dos equipamentos sem ligação continuam visíveis sem serem apresentados como uma nova análise bem-sucedida. As tarefas têm os seus próprios estados, incluindo `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_ADMIN`, `EXPIRED` e `INTERRUPTED`.

A atualização da aplicação verifica a identidade do repositório, a integridade e a ascendência dos objetos Git, executa as verificações na versão preparada e mantém a versão atual e a anterior. A verificação Git não é um mecanismo de assinatura de versões. A primeira migração requer um comando explícito do operador. A configuração existente e os dados de registo ficam fora do diretório da versão. A reposição de versões anteriores e os limites conservadores da limpeza estão explicados no [manual](docs/manual.md#application-self-update).

<a id="known-issues-and-troubleshooting"></a>

## Problemas conhecidos e resolução de problemas

O [guia de problemas](docs/troubleshooting.md#known-issues) regista limitações concretas e soluções alternativas. Atualmente:

- Não existe um desinstalador multiplataforma completo; siga o [procedimento de remoção manual](docs/installation.md#uninstall).
- A atualização de utilizador não preserva de forma fiável os caminhos personalizados de estado e configuração em Unix; utilize os caminhos predefinidos ou uma transição nativa manual.
- A TUI pode falhar ao navegar num conjunto vazio de equipamentos; utilize `status` e `diagnose` até registar um membro.
- A integração do prompt Bash não respeita totalmente `NO_COLOR`; utilize `status --no-color` para garantir uma saída CLI sem cores.
- O conteúdo desconhecido de uma versão, incluindo diretórios de documentação adicionais, impede por precaução a limpeza automática.
- Os adaptadores macOS/Homebrew, winget, Flatpak e Snap e a tradução completa do programa não estão implementados.

Se um comando não for encontrado, abra um novo shell e verifique o diretório de executáveis do utilizador. Para `NEEDS_ADMIN`, verifique o utilitário nativo e a permissão `allow_install` do membro. Perante erros TLS ou de autenticação, verifique o certificado, o nome do host e o registo. Não interprete uma verificação falhada como zero atualizações pendentes.

<a id="manual-and-project-information"></a>

## Manual e informações do projeto

| Documentação | Conteúdo |
| :--- | :--- |
| [Instalação](docs/installation.md) | Configuração de utilizador/sistema, serviços, verificação, reposição da versão anterior e desinstalação. |
| [Manual](docs/manual.md) | Todas as ações e opções da CLI, exemplos, estados, registos e atualização da aplicação. |
| [Configuração](docs/configuration.md) | Configuração do hub, dos membros e dos operadores, chaves, valores predefinidos, caminhos e prioridades. |
| [Resolução de problemas](docs/troubleshooting.md) | Sintomas, erros conhecidos, soluções práticas e perguntas frequentes. |
| [Verificação](docs/documentation-status.md) | O que foi verificado e o que ainda necessita de um teste nativo na plataforma. |
| [Modelo README](docs/README_TEMPLATE.md) | Estrutura reutilizável de apresentação de projetos em sete idiomas. |
| [Pesquisa de design](docs/readme-design-research.md) | Dez README de referência de fontes primárias e as decisões de apresentação adotadas. |

O manual técnico detalhado é atualmente mantido em inglês; cada um dos sete README apresenta os mesmos primeiros passos e a mesma visão do funcionamento no respetivo idioma.

**Contribuir / obter ajuda:** [abra uma issue](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues) indicando o sistema operativo, a versão do Python, o commit do UpdateWulf, o comando exato e a saída sem dados sensíveis. Nunca anexe tokens, chaves privadas ou ficheiros reais de configuração. Consulte as [verificações para contribuir](docs/manual.md#contributing).

**Licença:** o repositório não contém atualmente um ficheiro de licença. Esta documentação não escolhe nem concede uma licença; pergunte ao responsável pelo projeto quais as reutilizações permitidas.

---

<div align="center">

[Voltar ao início](#updatewulf) · [Descarregar o código-fonte](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip) · [Ler o manual](docs/manual.md)

</div>

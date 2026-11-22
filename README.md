# Áudio ao vivo com transcrição, resumo incremental e integridade Ed25519

Projeto 2 da disciplina de Redes de Computadores (UFES). Transmite áudio ao vivo em pacotes UDP
(**PCM** ou **Opus**) para múltiplos clientes simultâneos e usa um canal **WebSocket** separado
para legendas sincronizadas, resumo ao vivo, assinatura digital e controle.

O cliente é uma aplicação desktop **PySide6**. O núcleo de rede (`AudioPacket`, `FrameEncoder`,
`FrameDecoder`, `JitterBuffer`) não depende da interface gráfica e é reutilizado diretamente nos
experimentos headless com `tc netem`.

## O que está implementado

| Camada | Recursos principais |
| :--- | :--- |
| **Núcleo obrigatório** | Protocolo binário estilo RTP (`RA`, codec, sequência, `timestamp_samples`); transmissão UDP multi-cliente para `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac` e `.mp4` (incluindo envio de áudio pela interface); codecs **PCM** e **Opus** via PyAV (`libopus` embutido); `JitterBuffer` configurável com contagem de perda/atraso/duplicata/KB; controles de pausar, continuar e parar; transcrição local em CPU (`faster-whisper` `base`, `int8`, `word_timestamps`) com prévia ao vivo e legendas sincronizadas. |
| **Incremento 1 (Inteligência)** | **Resumo ao vivo** assíncrono em tarefa paralela usando **Ollama** (`/api/chat`, `qwen2.5:1.5b`) com fallback extrativo em Python puro; quem entra no meio recebe imediatamente o último resumo confirmado. |
| **Incremento 2 (Segurança)** | **Integridade da transcrição**: assinatura digital **Ed25519** em cada legenda finalizada no servidor e verificação com chave pública no cliente, com botão para simular adulteração. |
| **Experimento obrigatório** | Scripts [run_matrix.py](experiments/run_matrix.py) e [plot_results.py](experiments/plot_results.py) para rodar no Linux/WSL2 a matriz `tc netem` (0%, 1%, 5%, 10%, 20% em PCM e Opus, 3 repetições = 30 execuções), calcular WER e latência e gerar 4 gráficos. |

## Arquitetura

```text
Servidor Python / FastAPI
├── UDP: áudio PCM ou Opus em quadros de 20 ms (sequência + timestamp_samples)
└── WebSocket (/ws): registro, chave pública Ed25519, legendas, resumo e controle
                │
                ▼
Cliente desktop PySide6
├── NetworkWorker (UDP + WebSocket)
├── JitterBuffer (prefill configurável + contagem de perda/atraso/duplicata)
├── PlaybackWorker (decodificação PCM/Opus + buffer em anel no sounddevice)
└── Interface (legendas sincronizadas, resumo ao vivo, Ed25519, métricas e controles)
```

## Requisitos

- Python **3.11 ou 3.12** (`>=3.11,<3.13`)
- Windows 10/11 ou Linux, com dispositivo de saída de áudio
- No Linux desktop: PortAudio e bibliotecas gráficas usadas pelo Qt/PySide6
- Linux ou **WSL2** com `tc` (`iproute2`) para os experimentos com `tc netem`
- **Opcional (recomendado para o resumo com IA):** Ollama local com o modelo `qwen2.5:1.5b`

## Instalação (Windows)

### Ambiente do projeto

> **Importante no Windows:** coloque a pasta do projeto em um caminho curto (por exemplo,
> `C:\trab-redes`) para evitar o limite de 260 caracteres do Windows ao instalar o `PySide6`.

```powershell
.\scripts\setup.ps1
```

O script cria a `.venv` e instala o servidor, o cliente PySide6, IA/codec (`faster-whisper`,
`av`, `cryptography`, `httpx`), experimentos (`jiwer`, `matplotlib`, `pandas`) e testes.

## Instalação (Linux - Ubuntu/Debian)

O servidor funciona em uma máquina Linux sem ambiente gráfico. Para abrir também o cliente
PySide6 e reproduzir áudio, instale as bibliotecas do Qt e do PortAudio:

```bash
sudo apt update
sudo apt install -y python3 python3-venv iproute2 libportaudio2 libgl1 libegl1 \
  libxkbcommon-x11-0 libxcb-cursor0
```

Em seguida, na raiz do repositório:

```bash
bash scripts/setup.sh
```

O script cria `.venv-linux`, atualiza o `pip` e instala os mesmos componentes disponíveis no
Windows. O ambiente separado evita misturar executáveis Windows e Linux quando o repositório é
acessado pelo WSL2. Para usar outro local, defina `REDES_VENV=/caminho/do/ambiente`.
Em outras distribuições, instale os pacotes equivalentes para Python venv, PortAudio, OpenGL/EGL,
XKB e XCB. O cliente precisa de uma sessão gráfica X11/Wayland e de uma saída PipeWire/PulseAudio
ou ALSA. O servidor, os testes e os experimentos podem ser executados sem interface gráfica.

## Ollama (opcional - Windows e Linux)

Sem o Ollama, o servidor funciona normalmente usando um resumo extrativo simples em Python.
Com o Ollama ligado, o resumo é gerado por IA (`ollama:qwen2.5:1.5b`):

No Windows, instale o Ollama pelo `winget` (ou pelo site oficial):

```powershell
winget install -e --id Ollama.Ollama
```

*(Para desinstalar posteriormente: `winget uninstall Ollama.Ollama`.)*

No Linux, o instalador oficial é:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Também há instalação manual na [página oficial do Ollama para Linux](https://ollama.com/download/linux).
Depois da instalação, os comandos de preparação são os mesmos nos dois sistemas.

1. Inicie o serviço do Ollama em um terminal (ou abra o aplicativo no Windows):

```powershell
ollama serve
```

2. Em outro terminal, baixe o modelo leve `qwen2.5:1.5b` (~1,1 GB, roda em CPU sem GPU):

```powershell
ollama pull qwen2.5:1.5b
```

*(Se o registro padrão do Ollama der timeout de rede/IPv6, baixe o mesmo modelo direto pelo
HuggingFace e crie o alias:)*

```powershell
ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
ollama cp hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M qwen2.5:1.5b
```

3. Confirme que o serviço está respondendo na porta `11434`.

No PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

No Linux:

```bash
curl --fail http://127.0.0.1:11434/api/tags
```

## Como executar no Windows

- **Terminal 1 (opcional — IA do resumo):**
  ```powershell
  ollama serve
  ```
  *(Se o Ollama já estiver aberto na bandeja do Windows, não precisa rodar novamente. Se não
  estiver rodando, o servidor cai automaticamente no modo extrativo local.)*

- **Terminal 2 (servidor):**
  ```powershell
  .\scripts\start-server.ps1
  ```
  *(Se der erro `Errno 10048` de porta 8000 ocupada, finalize o processo antigo antes:
  `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`.)*

- **Terminal 3 (Cliente 1):**
  ```powershell
  .\scripts\start-client.ps1
  ```
  Clique em **Conectar** e use os botões do rodapé: **Iniciar Aula (Opus)**, **Iniciar Aula
  (PCM)** ou **Enviar Outro Áudio...** (por exemplo, `data/reference/palestra.mp3` ou qualquer
  `.mp3`/`.wav`). Com o Ollama ligado, o painel de resumo mostrará `ollama:qwen2.5:1.5b`.

- **Terminal 4 (Cliente 2 — múltiplos ouvintes e entrada tardia):**
  Com a transmissão já tocando há alguns segundos, abra outro cliente em outra porta UDP:
  ```powershell
  .\scripts\start-client.ps1 -UdpPort 5002
  ```
  Ao clicar em **Conectar**, o segundo ouvinte recebe o áudio ao vivo e já carrega na tela o
  último resumo confirmado até aquele instante.

- **Testar integridade Ed25519:**
  Clique em **Simular Adulteração** na janela para enviar uma legenda alterada e confirmar que o
  cliente detecta a assinatura inválida e bloqueia o texto.

## Como executar no Linux

- **Terminal 1 (opcional - IA do resumo):**
  ```bash
  ollama serve
  ```
  Se o Ollama estiver instalado como serviço e já estiver ativo, não execute outra instância.

- **Terminal 2 (servidor):**
  ```bash
  bash scripts/start-server.sh
  ```

- **Terminal 3 (cliente principal):**
  ```bash
  bash scripts/start-client.sh
  ```

- **Terminal 4 (segundo cliente):**
  ```bash
  bash scripts/start-client.sh --udp-port 5002
  ```

Para conectar um cliente Linux a um servidor em outra máquina, informe o IP acessível na rede:

```bash
bash scripts/start-client.sh --server 192.168.1.10 --server-port 8000 --udp-port 5001
```

Libere no firewall do servidor a porta TCP `8000` (HTTP/WebSocket) e, entre servidor e cada
cliente, a porta UDP informada pelo cliente. Em uma mesma máquina, cada cliente precisa de uma
porta UDP diferente. Para interromper servidor ou cliente no terminal, use `Ctrl+C`.

## Endpoints HTTP principais

| Rota | Função |
| :--- | :--- |
| `GET /health` | Status do servidor e quantidade de clientes conectados |
| `GET /api/v1/session` | Clientes ativos, chave pública Ed25519 e resumo atual |
| `POST /api/v1/stream/start` | Inicia transmissão de arquivo (padrão `data/reference/aula_redes.wav`) |
| `POST /api/v1/stream/upload` | Recebe áudio enviado pelo cliente (`?filename=...&codec=opus`) e transmite |
| `POST /api/v1/stream/stop` | Interrompe a transmissão ativa |
| `POST /api/v1/demo/start` | Envia tom PCM de 440 Hz por 3 s para teste rápido de transporte |
| `POST /api/v1/demo/tamper` | Envia legenda adulterada para teste da verificação Ed25519 |

## Variáveis de ambiente (`REDES_*`)

Veja `.env.example` para sobrescrever padrões via `.env` ou ambiente:

- `REDES_HOST` (`0.0.0.0`), `REDES_PORT` (`8000`)
- `REDES_SAMPLE_RATE` (`16000`), `REDES_FRAME_DURATION_MS` (`20`)
- `REDES_WHISPER_MODEL` (`base`), `REDES_WHISPER_LANGUAGE` (`pt`), `REDES_TRANSCRIPTION_WINDOW_SECONDS` (`1.5`)
- `REDES_SUMMARY_BACKEND` (`auto`, `ollama` ou `extractive`), `REDES_SUMMARY_MIN_CHARS` (`80`)
- `REDES_OLLAMA_URL` (`http://127.0.0.1:11434`), `REDES_OLLAMA_MODEL` (`qwen2.5:1.5b`)

Se o servidor usar outra porta HTTP/WebSocket, inicie o cliente com `-ServerPort <porta>` no
PowerShell ou `--server-port <porta>` no Linux. A porta UDP continua sendo configurada
separadamente.

## Experimento obrigatório no Linux / WSL2

No Linux ou WSL2 (com Python 3.11 em ambiente virtual e permissão `sudo` para `tc`):

```bash
bash scripts/run-experiment.sh --wav data/reference/aula_redes_exp.wav
```

- Use `--wav data/reference/palestra.mp3` (ou outro arquivo) para avaliar outro áudio.
- O runner aplica `tc netem` com perda de **0%, 1%, 5%, 10% e 20%** em **PCM** e **Opus**
  (3 repetições cada = 30 execuções) e salva métricas e WER (`jiwer`) em
  `experiments/results/results.csv`.
- O plotter gera 4 gráficos PNG em `experiments/results/`: `wer_vs_loss.png`,
  `bandwidth_comparison.png`, `loss_validation.png` e `latency_budget.png`.

### Resultados obtidos

A matriz completa de 30 execuções foi realizada no WSL2 com `tc netem` real e Whisper
`tiny/int8`. Os arquivos reproduzíveis estão em `experiments/results/`.

| Codec | Perda | Perda observada média | WER médio |
| --- | ---: | ---: | ---: |
| PCM | 0% | 0,00% | 0,00% |
| PCM | 5% | 5,13% | 7,84% |
| PCM | 10% | 9,20% | 13,72% |
| PCM | 20% | 19,64% | 30,72% |
| Opus | 0% | 0,00% | 0,00% |
| Opus | 5% | 4,84% | 9,15% |
| Opus | 10% | 10,13% | 29,41% |
| Opus | 20% | 19,85% | 34,64% |

Na média de todas as condições, PCM consumiu 255,4 kbps e Opus 36,5 kbps, incluindo
cabeçalhos. O relatório final em `output/pdf/relatorio-final-projeto-2-redes.pdf` apresenta
gráficos, orçamento de latência, limitações e a resposta à pergunta-desafio.

## Verificar qualidade

No Windows:

```powershell
.\scripts\check.ps1
```

No Linux:

```bash
bash scripts/check.sh
```

Executa o lint (`ruff check .`) e a suíte de 25 testes (`pytest`) sem abrir a interface.

## Estrutura

```text
data/reference/        # áudios de referência e gabaritos para demo e experimento
docs/                  # decisões de arquitetura
experiments/           # run_matrix.py, plot_results.py e results/ (ignorado no Git)
scripts/               # setup, execução e verificação no Windows (.ps1) e Linux (.sh)
src/redes_audio/
├── shared/            # protocolo binário, codec PCM/Opus e assinatura Ed25519
├── core/              # jitter buffer e métricas, sem dependência de GUI
├── server/            # FastAPI, registro, broadcaster UDP, Whisper e resumo
└── client/            # workers Qt, áudio em anel e janela PySide6
tests/                 # testes automatizados (protocolo, codec, Ed25519, jitter, servidor, resumo)
tools/                 # geração de áudios de referência e PDFs de planejamento
```

## Princípios

1. A GUI apresenta estado; o núcleo toma decisões.
2. O áudio nunca é bloqueado pela transcrição ou pelo resumo.
3. Toda medição deve ser reproduzível e exportável.
4. Erros de rede devem ser observáveis e compreensíveis.
5. Código e contratos ficam em inglês; documentação e interface ficam em português.

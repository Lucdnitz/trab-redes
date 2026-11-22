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

- Python **3.11 ou 3.12 estável** (`>=3.11,<3.13`) — os scripts de instalação baixam um Python 3.11 portátil dentro do projeto (`.venv-tools/`) automaticamente caso o sistema tenha outra versão (como 3.10 ou 3.13).
- Windows 10/11 ou Linux/WSL2, com dispositivo de saída de áudio para o cliente.
- **Opcional (recomendado para o resumo com IA):** Ollama local com o modelo `qwen2.5:1.5b`.

## Instalação rápida

### Linux / WSL2 (Ubuntu, Debian, etc.)

Na raiz do repositório, rode apenas:

```bash
bash scripts/setup.sh
bash scripts/check.sh
```

O `setup.sh` usa Python 3.11/3.12 do sistema se já estiver instalado; caso contrário (como no
Ubuntu 22.04 com Python 3.10), ele baixa automaticamente um Python 3.11 portátil isolado em
`.venv-tools/` e cria `.venv-linux/` **sem precisar de `sudo` nem instalar nada no sistema**.

> **Somente se o Linux mínimo reclamar de biblioteca faltando** (ex.: sem `tc` para o experimento
> ou sem biblioteca gráfica/áudio ao abrir a janela PySide6):
> ```bash
> sudo apt update
> sudo apt install -y iproute2 libportaudio2 libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0
> ```

### Windows

> **Dica:** coloque o repositório em um caminho curto (por exemplo, `C:\trab-redes`) para
> evitar o limite de 260 caracteres do Windows ao instalar o `PySide6`.

```powershell
.\scripts\setup.ps1
.\scripts\check.ps1
```

Assim como no Linux, o `setup.ps1` usa Python 3.11/3.12 se existir no Windows ou baixa um Python
3.11 portátil isolado dentro de `.venv-tools\` automaticamente.

*(Nos dois sistemas, o `check` roda o lint `ruff` e os **25 testes** automatizados sem abrir a GUI.)*

## Ollama (opcional — Windows e Linux)

Sem o Ollama, o servidor funciona normalmente usando um resumo extrativo simples em Python.
Com o Ollama ligado, o resumo é gerado por IA (`ollama:qwen2.5:1.5b`):

- **Windows:** `winget install -e --id Ollama.Ollama` *(para remover depois: `winget uninstall Ollama.Ollama`)*
- **Linux / WSL2:** `curl -fsSL https://ollama.com/install.sh | sh` (ou via [página oficial do Ollama para Linux](https://ollama.com/download/linux))

Depois de instalar, prepare uma única vez nos dois sistemas:

1. Inicie o serviço do Ollama em um terminal (ou abra o app no Windows):

```bash
ollama serve
```

2. Em outro terminal, baixe o modelo leve `qwen2.5:1.5b` (~1,1 GB, roda em CPU sem GPU):

```bash
ollama pull qwen2.5:1.5b
```

*(Se o registro padrão do Ollama der timeout de rede/IPv6, baixe o mesmo modelo direto pelo
HuggingFace e crie o alias:)*

```bash
ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
ollama cp hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M qwen2.5:1.5b
```

3. Confirme que o serviço está respondendo na porta `11434`:
   - Windows: `Invoke-RestMethod http://127.0.0.1:11434/api/tags`
   - Linux/WSL2: `curl --fail http://127.0.0.1:11434/api/tags`

## Como executar e demonstrar

### No Windows

- **Terminal 1 (opcional — IA do resumo):** `ollama serve` *(se já estiver na bandeja do Windows, não precisa rodar de novo)*
- **Terminal 2 (servidor):**
  ```powershell
  .\scripts\start-server.ps1
  ```
  *(Se der erro `Errno 10048` de porta 8000 ocupada: `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`.)*
- **Terminal 3 (Cliente 1):**
  ```powershell
  .\scripts\start-client.ps1
  ```
  Clique em **Conectar** e use os botões do rodapé: **Iniciar Aula (Opus)**, **Iniciar Aula (PCM)** ou **Enviar Outro Áudio...** (ex.: `data/reference/palestra.mp3`).
- **Terminal 4 (Cliente 2 — múltiplos ouvintes e entrada tardia):**
  Com a aula tocando há alguns segundos, abra outro cliente em outra porta UDP:
  ```powershell
  .\scripts\start-client.ps1 -UdpPort 5002
  ```
  Ao clicar em **Conectar**, o segundo ouvinte recebe o áudio ao vivo e já carrega o resumo acumulado.
- **Testar integridade Ed25519:** clique em **Simular Adulteração** na janela para ver a rejeição imediata da legenda alterada.

### No Linux / WSL2

- **Terminal 1 (opcional):** `ollama serve` *(se não houver serviço ativo)*
- **Terminal 2 (servidor):** `bash scripts/start-server.sh`
- **Terminal 3 (Cliente 1):** `bash scripts/start-client.sh`
- **Terminal 4 (Cliente 2):** `bash scripts/start-client.sh --udp-port 5002`

Para conectar a um servidor em outra máquina:

```bash
bash scripts/start-client.sh --server 192.168.1.10 --server-port 8000 --udp-port 5001
```

Libere no firewall do servidor a porta TCP `8000` (HTTP/WebSocket) e, entre servidor e cada
cliente, a porta UDP informada pelo cliente. Em uma mesma máquina, cada cliente precisa de uma
porta UDP diferente. Para interromper no terminal, use `Ctrl+C`.

## Endpoints HTTP principais

| Rota | Função |
| :--- | :--- |
| `GET /health` | Status do servidor e quantidade de clientes conectados |
| `GET /api/v1/session` | Clientes ativos, chave pública Ed25519 e resumo atual |
| `POST /api/v1/stream/start` | Inicia transmissão de arquivo (padrão `data/reference/aula tecnologia.mp3`) |
| `POST /api/v1/stream/upload` | Recebe áudio enviado pelo cliente (`?filename=...&codec=opus`) e transmite |
| `POST /api/v1/stream/stop` | Interrompe a transmissão ativa |
| `POST /api/v1/demo/start` | Envia tom PCM de 440 Hz por 3 s para teste rápido de transporte |
| `POST /api/v1/demo/tamper` | Envia legenda adulterada para teste da verificação Ed25519 |

## Variáveis de ambiente (`REDES_*`)

Veja `.env.example` para sobrescrever padrões via `.env` ou ambiente:

- `REDES_HOST` (`0.0.0.0`), `REDES_PORT` (`8000`), `REDES_DEFAULT_JITTER_MS` (`100`)
- `REDES_SAMPLE_RATE` (`16000`), `REDES_FRAME_DURATION_MS` (`20`)
- `REDES_WHISPER_MODEL` (`base`), `REDES_WHISPER_LANGUAGE` (`pt`), `REDES_TRANSCRIPTION_WINDOW_SECONDS` (`1.5`)
- `REDES_SUMMARY_BACKEND` (`auto`, `ollama` ou `extractive`), `REDES_SUMMARY_MIN_CHARS` (`80`)
- `REDES_OLLAMA_URL` (`http://127.0.0.1:11434`), `REDES_OLLAMA_MODEL` (`qwen2.5:1.5b`)

Se o servidor usar outra porta HTTP/WebSocket (`REDES_PORT`), inicie o cliente com
`-ServerPort <porta>` no PowerShell ou `--server-port <porta>` no Linux.

## Experimento obrigatório no Linux / WSL2

No Linux ou WSL2 (após `bash scripts/setup.sh`, com permissão `sudo` para `tc`):

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

- Windows: `.\scripts\check.ps1`
- Linux / WSL2: `bash scripts/check.sh`

Executa o lint (`ruff check .`) e a suíte de **25 testes** (`pytest`) sem abrir a interface.

## Estrutura

```text
data/reference/        # áudios de referência e gabaritos para demo e experimento
docs/                  # decisões de arquitetura (architecture.md) e roteiro (demo.md)
experiments/           # run_matrix.py, plot_results.py e results/
output/pdf/            # planejamento e relatório final (relatorio-final-projeto-2-redes.pdf)
scripts/               # setup, execução e verificação no Windows (.ps1) e Linux (.sh)
src/redes_audio/
├── shared/            # protocolo binário, codec PCM/Opus, áudio e assinatura Ed25519
├── core/              # jitter buffer e métricas, sem dependência de GUI
├── server/            # FastAPI, registro, broadcaster UDP, Whisper e resumo
└── client/            # workers Qt, áudio em anel e janela PySide6
tests/                 # 25 testes automatizados (protocolo, codec, Ed25519, jitter, servidor, resumo)
tools/                 # geração de áudios de referência e scripts dos PDFs
```

## Princípios

1. A GUI apresenta estado; o núcleo toma decisões.
2. O áudio nunca é bloqueado pela transcrição ou pelo resumo.
3. Toda medição deve ser reproduzível e exportável.
4. Erros de rede devem ser observáveis e compreensíveis.
5. Código e contratos ficam em inglês; documentação e interface ficam em português.

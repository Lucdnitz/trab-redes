# Áudio ao vivo com transcrição e checagem de fatos

Projeto 2 da disciplina de Redes de Computadores da UFES. O sistema transmite áudio em
pacotes UDP para múltiplos clientes, mantém um canal WebSocket separado para texto e
controle e instrumenta perda, atraso, jitter e latência.

O cliente é uma aplicação desktop PySide6. O núcleo de rede não depende da interface e é
reutilizado pelo modo headless dos experimentos.

## Estado atual

Este primeiro marco contém:

- contrato binário versionado para pacotes de áudio;
- servidor FastAPI com healthcheck, registro WebSocket e gerador UDP de demonstração;
- cliente PySide6 com receptor UDP, jitter buffer, reprodução PCM e métricas;
- testes unitários do protocolo, jitter buffer e API;
- scripts PowerShell para configuração, execução e verificação;
- planejamento acadêmico em `output/pdf/`.

Transcrição, RAG, Opus e automação com `tc netem` estão isolados como próximos módulos.

## Arquitetura

```text
Servidor Python / FastAPI
├── UDP: áudio PCM/Opus com sequência e timestamp
└── WebSocket: registro, legendas, fatos e controle
                │
                ▼
Cliente desktop PySide6
├── receptor UDP
├── jitter buffer
├── reprodução de áudio
├── legendas e checagem de fatos
└── métricas e controles
```

## Requisitos

- Python 3.11
- Windows 10/11 ou Linux
- dispositivo de saída de áudio para reprodução
- Linux/WSL2 para os experimentos com `tc netem`

## Configuração no Windows

```powershell
.\scripts\setup.ps1
```

O script cria `.venv` e instala o servidor, o cliente e as ferramentas de desenvolvimento.

## Executar

Terminal 1:

```powershell
.\scripts\start-server.ps1
```

Terminal 2:

```powershell
.\scripts\start-client.ps1
```

Depois de conectar o cliente, inicie um tom PCM de demonstração:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/demo/start
```

O endpoint envia três segundos de áudio para todos os clientes registrados. O objetivo é
validar transporte, sequência, jitter buffer e reprodução antes de integrar arquivos WAV.

## Verificar qualidade

```powershell
.\scripts\check.ps1
```

Esse comando executa lint e testes. O núcleo pode ser testado sem abrir a interface.

## Estrutura

```text
src/redes_audio/
├── shared/       # protocolo e eventos comuns
├── core/         # jitter buffer e métricas, sem dependência de GUI
├── server/       # FastAPI, registro e transmissão UDP
└── client/       # workers, áudio e interface PySide6
tests/            # testes automatizados
experiments/      # runners e resultados experimentais
scripts/          # instalação e execução
docs/             # decisões e contratos
```

## Princípios

1. A GUI apresenta estado; o núcleo toma decisões.
2. O áudio nunca é bloqueado pela transcrição ou pelo RAG.
3. Toda medição deve ser reproduzível e exportável.
4. Erros de rede devem ser observáveis e compreensíveis.
5. Código e contratos ficam em inglês; documentação e interface ficam em português.

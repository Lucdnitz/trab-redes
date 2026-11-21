# Decisões de arquitetura

## Separação dos fluxos

O áudio usa UDP porque prioriza continuidade e baixa latência. Texto e controle usam
WebSocket porque toleram atraso, mas precisam de entrega ordenada e confiável.

## Cliente desktop

O navegador não oferece socket UDP bruto. O cliente PySide6 reúne listener e painel em um
único processo, evitando uma ponte local adicional. A interface não implementa regras de
rede: ela recebe sinais produzidos pelos workers.

## Protocolo de áudio

Cabeçalho em ordem de rede:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| magic | 2 bytes | Identificador `RA` |
| version | uint8 | Versão do protocolo |
| codec | uint8 | PCM=1, OPUS=2 |
| sequence | uint32 | Sequência monotônica |
| timestamp_samples | uint64 | Posição do quadro em amostras |
| payload_length | uint16 | Tamanho do payload |

O formato inicial é PCM signed 16-bit little-endian, mono, 16 kHz e quadros de 20 ms.

## Concorrência

- thread principal: somente PySide6 e reação a sinais;
- worker de rede: UDP e WebSocket;
- worker de reprodução: consumo periódico do jitter buffer;
- tarefas futuras de ASR/RAG: servidor, fora do caminho crítico do áudio.

## Modo headless

Os experimentos reutilizarão `AudioPacket` e `JitterBuffer`. A única diferença será a saída:
em vez de dispositivo de áudio e widgets, o runner gravará WAV e CSV.

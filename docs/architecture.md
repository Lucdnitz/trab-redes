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
- tarefas de ASR/resumo: servidor, fora do caminho crítico do áudio.

## Resumo incremental

O servidor acumula segmentos finalizados da transcrição e atualiza um resumo curto em
intervalos maiores que os do áudio. O resumo anterior e somente os trechos novos formam a
entrada da atualização, evitando reprocessar toda a sessão.

Um cliente que entra no meio recebe imediatamente o último resumo confirmado e passa a
acompanhar as novas legendas. A atualização do resumo é assíncrona e nunca bloqueia UDP,
reprodução ou envio de legendas.

## Modo headless

Os experimentos reutilizam `AudioPacket`, codecs e `JitterBuffer`. A única diferença é a
saída: em vez de dispositivo de áudio e widgets, o runner grava WAV e CSV.

## Integridade e modelo de ameaça

Cada legenda final é assinada com Ed25519 sobre sessão, sequência, intervalo temporal e
texto. O cliente rejeita qualquer alteração posterior a essa assinatura. A chave pública é
recebida no canal WebSocket; portanto, a demonstração assume que esse primeiro canal é
autêntico. A solução detecta adulteração em trânsito após a distribuição da chave, mas não
pretende substituir TLS nem autenticação do servidor.

## Troca de transmissão

Somente uma transmissão pode ficar ativa. Iniciar outro arquivo ou tom cancela o anterior,
emite `stream_ended`, zera o jitter buffer e inicia uma nova sessão a partir da sequência zero.
Uma lacuna após o prefill ocupa um quadro de silêncio, preservando timestamps e sincronização.

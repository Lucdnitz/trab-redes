# Roteiro de demonstração - 5 minutos

## Preparação

1. Executar `scripts/check.ps1` no Windows ou `bash scripts/check.sh` no Linux.
2. Iniciar o servidor com `scripts/start-server.ps1` no Windows ou
   `bash scripts/start-server.sh` no Linux.
3. Abrir dois clientes nas portas UDP 5001 e 5002.
4. Confirmar que o áudio de referência e os quatro gráficos estão presentes.
5. Deixar o Ollama ativo; se ele não responder, explicar o fallback extrativo.

## Sequência cronometrada

| Tempo | Demonstração | Conceito observado |
| --- | --- | --- |
| 0:00-0:35 | Mostrar arquitetura e cabeçalho do pacote. | UDP para áudio; WebSocket para texto e controle. |
| 0:35-1:20 | Conectar o primeiro cliente e iniciar PCM. | Sequência, timestamp, jitter buffer e métricas. |
| 1:20-1:55 | Pausar e continuar localmente; parar no servidor. | Controle de reprodução e troca limpa de sessão. |
| 1:55-2:35 | Iniciar Opus e comparar a contagem de KB. | Codec e economia de banda. |
| 2:35-3:20 | Conectar o segundo cliente durante a fala. | Entrada tardia e resumo incremental. |
| 3:20-3:50 | Acionar “Simular Adulteração”. | Assinatura Ed25519 e rejeição da legenda alterada. |
| 3:50-4:30 | Mostrar CSV, WER x perda e PCM x Opus. | Hipótese, repetições e evidência experimental. |
| 4:30-5:00 | Responder onde executar a transcrição. | Qualidade, latência, banda, privacidade e escala. |

## Evidências que devem aparecer

- dois clientes registrados e recebendo o mesmo fluxo;
- pacotes recebidos, perdidos, atrasados e bytes acumulados;
- legenda com intervalo temporal e indicador de integridade;
- resumo disponível para o segundo cliente;
- alerta de legenda adulterada;
- 30 linhas no CSV e gráficos versionados;
- resposta final sustentada pelos valores medidos.

## Contingências

- Sem dispositivo de áudio: demonstrar recepção, métricas e WAV reconstruído no experimento.
- Sem Ollama: usar o fallback extrativo e mostrar o backend no painel.
- Sem modelo Whisper já baixado: usar o cache preparado antes da apresentação.
- Porta 8000 ocupada: iniciar o servidor em outra `REDES_PORT` e passar `-ServerPort` ao cliente.
- Linux sem áudio: confirmar `libportaudio2`, a saída PipeWire/PulseAudio/ALSA e a sessão gráfica;
  o servidor e os testes continuam funcionando sem GUI.

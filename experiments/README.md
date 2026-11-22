# Experimento obrigatório

O runner headless executa a matriz definida no enunciado:

- codecs: PCM e Opus;
- perdas: 0%, 1%, 5%, 10% e 20%;
- repetições: 3 por combinação;
- total: 30 execuções.

O comando recomendado no Linux/WSL2 é:

```bash
bash scripts/setup.sh
bash scripts/run-experiment.sh --wav data/reference/aula_redes_exp.wav
```

O sistema precisa do comando `tc`, fornecido pelo pacote `iproute2`. O runner solicita `sudo`
apenas para configurar e remover o qdisc; o restante da aplicação não precisa executar como root.

O `tc netem` é aplicado à interface `lo` antes de cada grupo e removido em um bloco `finally`.
O WAV reconstruído sempre mantém a duração original: perdas iniciais, intermediárias e finais
são representadas por quadros silenciosos. A comparação principal usa a transcrição limpa do
mesmo áudio como referência, isolando o efeito da rede; `wer_vs_gt` registra também o gabarito
humano.

São versionados o CSV, os quatro gráficos e os metadados. Os WAVs intermediários permanecem
ignorados por ocuparem mais espaço e poderem ser regenerados.

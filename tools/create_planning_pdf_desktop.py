from __future__ import annotations

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

from create_planning_pdf import (
    AMBER,
    AMBER_LIGHT,
    BLUE_LIGHT,
    CONTENT_W,
    GREEN,
    GREEN_LIGHT,
    INK,
    LINE,
    MUTED,
    NAVY,
    NAVY_2,
    PAPER,
    RED,
    RED_LIGHT,
    ROOT,
    TEAL,
    TEAL_LIGHT,
    WHITE,
    PlanningDocTemplate,
    bullet,
    card,
    heading,
    metric_card,
    p,
    styles,
    styled_table,
)


OUTPUT = ROOT / "output" / "pdf" / "planejamento-projeto-2-redes-pyside6.pdf"


def arrow(d: Drawing, x1, y1, x2, y2, color=TEAL, width=1.5):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    size = 5
    d.add(
        Polygon(
            [x2, y2, x2 - size, y2 + size / 2, x2 - size, y2 - size / 2],
            fillColor=color,
            strokeColor=color,
        )
    )


def architecture_diagram() -> Drawing:
    width = CONTENT_W
    height = 230
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, rx=8, ry=8, fillColor=PAPER, strokeColor=LINE, strokeWidth=0.7))

    boxes = [
        (12, 156, 88, 48, "FONTE", "WAV ou microfone", AMBER_LIGHT, AMBER),
        (124, 140, 130, 80, "SERVIDOR PYTHON", "FastAPI + UDP\nWhisper + RAG\nWebSocket", BLUE_LIGHT, TEAL),
        (298, 132, 188, 96, "CLIENTE DESKTOP PYSIDE6", "UDP + jitter buffer + codec\náudio + legendas + fatos\ncontroles + métricas", GREEN_LIGHT, GREEN),
        (124, 38, 130, 56, "NÚCLEO HEADLESS", "mesmos módulos sem GUI\npara testes e experimento", WHITE, NAVY_2),
        (298, 38, 188, 56, "EVIDÊNCIAS", "CSV + WAV reconstruído + gráficos\nWER, perda, banda e latência", WHITE, NAVY_2),
    ]

    for x, y, bw, bh, title, body, fill, stroke in boxes:
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=stroke, strokeWidth=1.0))
        d.add(String(x + 8, y + bh - 16, title, fontName="Arial-Bold", fontSize=7.7, fillColor=stroke))
        for idx, line in enumerate(body.split("\n")):
            d.add(String(x + 8, y + bh - 31 - idx * 12, line, fontName="Arial", fontSize=7.3, fillColor=INK))

    arrow(d, 100, 180, 124, 180, AMBER)
    arrow(d, 254, 180, 298, 180, TEAL)
    arrow(d, 189, 140, 189, 94, NAVY_2)
    arrow(d, 254, 66, 298, 66, NAVY_2)

    d.add(String(260, 192, "UDP: áudio", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(260, 166, "WS: texto/controle", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(200, 111, "reuso", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(262, 77, "resultados", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    return d


def module_tree() -> Table:
    left = (
        "<b>server/</b><br/>"
        "├─ api/health.py<br/>"
        "├─ media/broadcaster.py<br/>"
        "├─ realtime/websocket.py<br/>"
        "├─ transcription/whisper.py<br/>"
        "└─ factcheck/rag.py"
    )
    middle = (
        "<b>client/</b><br/>"
        "├─ core/udp_receiver.py<br/>"
        "├─ core/jitter_buffer.py<br/>"
        "├─ core/audio_player.py<br/>"
        "├─ workers/network_worker.py<br/>"
        "└─ ui/main_window.py"
    )
    right = (
        "<b>experiments/</b><br/>"
        "├─ run_matrix.py<br/>"
        "├─ transcribe_received.py<br/>"
        "├─ calculate_wer.py<br/>"
        "└─ plot_results.py<br/><br/>"
        "<b>shared/</b> protocol.py, events.py"
    )
    table = Table(
        [[p(left, "CardBody"), p(middle, "CardBody"), p(right, "CardBody")]],
        colWidths=[CONTENT_W / 3] * 3,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), BLUE_LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), TEAL_LIGHT),
                ("BACKGROUND", (2, 0), (2, 0), GREEN_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def build_story() -> list:
    story: list = []

    # 1. Capa
    story += [
        Spacer(1, 31 * mm),
        p("PLANO OPERACIONAL V2.0 • ENTREGA EM 22/11/2026", "CoverKicker"),
        p("Áudio ao vivo com<br/>cliente desktop PySide6", "CoverTitle"),
        p(
            "Projeto 2 de Redes de Computadores<br/>FastAPI no servidor • PySide6 no cliente • UDP + WebSocket",
            "CoverSub",
        ),
        Spacer(1, 13 * mm),
    ]
    cover_cards = Table(
        [
            [p("NOVA DECISÃO", "CardTitle"), p("GANHO PRINCIPAL", "CardTitle")],
            [
                p(
                    "O listener e o painel passam a formar uma única aplicação desktop Python. Não há navegador, React ou ponte WebSocket local.",
                    "CardBody",
                ),
                p(
                    "A interface acessa diretamente o núcleo UDP, enquanto os mesmos módulos funcionam sem GUI nos experimentos.",
                    "CardBody",
                ),
            ],
        ],
        colWidths=[CONTENT_W / 2 - 5, CONTENT_W / 2 - 5],
    )
    cover_cards.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EAF2F8")),
                ("BOX", (0, 0), (-1, -1), 0.8, HexColor("#8ED8DD")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#B8D3E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [cover_cards, Spacer(1, 17 * mm)]
    story.append(
        Table(
            [[
                metric_card("2", "integrantes", TEAL_LIGHT),
                metric_card("2", "transportes", TEAL_LIGHT),
                metric_card("30", "execuções mínimas", TEAL_LIGHT),
                metric_card("1", "aplicação cliente", TEAL_LIGHT),
            ]],
            colWidths=[CONTENT_W / 4] * 4,
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ],
        )
    )
    story += [Spacer(1, 14 * mm), p("Versão 2.0 • Arquitetura desktop modular", "CoverSub"), PageBreak()]

    # 2. Decisão e stack
    story += heading(
        "1. Decisão executiva e stack",
        "O cliente desktop elimina a duplicação entre listener e painel. A solução continua simples de explicar, testável e diretamente ligada aos conceitos avaliados.",
    )
    story += [
        card(
            "RECOMENDAÇÃO FINAL",
            "Usar <b>FastAPI/Python</b> no servidor e <b>PySide6</b> no cliente. A GUI recebe eventos do núcleo por sinais, mas não contém regras de rede. O experimento executa o mesmo núcleo em modo headless.",
            TEAL_LIGHT,
            TEAL,
        ),
        Spacer(1, 8),
    ]
    stack = [
        [p("Camada", "TableHeader"), p("Tecnologia", "TableHeader"), p("Responsabilidade", "TableHeader")],
        [p("Servidor", "TableCellBold"), p("FastAPI + asyncio", "TableCell"), p("Sessões, registro dos clientes, áudio UDP e eventos WebSocket.", "TableCell")],
        [p("Cliente desktop", "TableCellBold"), p("PySide6 Widgets", "TableCell"), p("Conexão, reprodução, legendas, fatos, controles e métricas.", "TableCell")],
        [p("Áudio", "TableCellBold"), p("sounddevice + NumPy", "TableCell"), p("Entrada/saída PCM e integração com o jitter buffer.", "TableCell")],
        [p("Codec", "TableCellBold"), p("PCM + Opus", "TableCell"), p("Abstração encode/decode comum para demonstração e experimento.", "TableCell")],
        [p("Transcrição", "TableCellBold"), p("faster-whisper", "TableCell"), p("ASR local no servidor, modelo base/int8 como ponto inicial.", "TableCell")],
        [p("Checagem", "TableCellBold"), p("TF-IDF + Ollama", "TableCell"), p("Recuperação, veredito e fonte consultada.", "TableCell")],
        [p("Evidências", "TableCellBold"), p("jiwer + pandas + matplotlib", "TableCell"), p("WER, CSV, agregação e gráficos reproduzíveis.", "TableCell")],
        [p("Distribuição", "TableCellBold"), p("Scripts; PyInstaller opcional", "TableCell"), p("Um comando no desenvolvimento e executável se houver tempo.", "TableCell")],
    ]
    story += [styled_table(stack, [37 * mm, 52 * mm, 89 * mm]), Spacer(1, 8)]
    story += [
        p("POR QUE NÃO USAR BROWSER", "Section"),
        bullet("O navegador não expõe um socket UDP bruto; seria necessário manter um processo listener de qualquer forma."),
        bullet("PySide6 reúne áudio, rede e apresentação sem introduzir Node, React ou uma ponte localhost."),
        bullet("Signals/slots permitem atualizar a janela a partir de workers sem travar a interface."),
        bullet("O núcleo independente da GUI mantém a clareza acadêmica e viabiliza testes automatizados."),
        Spacer(1, 6),
        card(
            "PRINCÍPIO DE PROJETO",
            "A GUI apresenta estado; o núcleo toma decisões. Nenhuma regra de pacote, jitter, codec ou métrica deve ficar em widgets.",
            AMBER_LIGHT,
            AMBER,
        ),
        PageBreak(),
    ]

    # 3. Arquitetura e fluxos
    story += heading(
        "2. Arquitetura e fluxos",
        "Dois canais com propriedades distintas: o áudio usa UDP e aceita perda; texto e controle usam WebSocket e preservam ordem e entrega.",
    )
    story += [architecture_diagram(), Spacer(1, 8)]
    flows = [
        [p("Fluxo", "TableHeader"), p("Transporte", "TableHeader"), p("Conteúdo", "TableHeader"), p("Comportamento", "TableHeader")],
        [p("Áudio", "TableCellBold"), p("UDP", "TableCell"), p("PCM/Opus + sequência + timestamp", "TableCell"), p("Baixa latência, perda observável, sem retransmissão.", "TableCell")],
        [p("Texto", "TableCellBold"), p("WebSocket", "TableCell"), p("Legendas, fatos e assinaturas", "TableCell"), p("Ordenado e confiável; pode chegar depois do áudio.", "TableCell")],
        [p("Controle", "TableCellBold"), p("WebSocket", "TableCell"), p("Registro, pausa, continuar e parar", "TableCell"), p("Estado explícito da sessão e do cliente.", "TableCell")],
        [p("Experimento", "TableCellBold"), p("Headless", "TableCell"), p("Mesmo receptor, jitter e codecs", "TableCell"), p("Substitui GUI por captura WAV e CSV.", "TableCell")],
    ]
    story += [styled_table(flows, [30 * mm, 31 * mm, 62 * mm, 55 * mm]), Spacer(1, 8)]
    story += [p("CONTRATO DO PACOTE", "Section")]
    packet = Table(
        [[
            p("versão", "TableCellBold"),
            p("codec", "TableCellBold"),
            p("sequência", "TableCellBold"),
            p("timestamp_samples", "TableCellBold"),
            p("payload_len", "TableCellBold"),
            p("payload", "TableCellBold"),
        ]],
        colWidths=[22 * mm, 22 * mm, 29 * mm, 43 * mm, 29 * mm, 33 * mm],
    )
    packet.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), TEAL_LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), BLUE_LIGHT),
                ("BACKGROUND", (2, 0), (4, 0), AMBER_LIGHT),
                ("BACKGROUND", (5, 0), (5, 0), GREEN_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.6, NAVY_2),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story += [packet, Spacer(1, 7)]
    story += [
        bullet("Mono, 16 kHz, 16 bits e quadros de 20 ms: 320 amostras e 640 bytes no PCM."),
        bullet("Timestamp em amostras cria um único eixo para áudio e legenda, sem depender do relógio de parede."),
        bullet("O cliente envia registro UDP a partir do mesmo socket que receberá o fluxo; o servidor guarda o endpoint observado."),
        bullet("A GUI exibe estado por sinais; workers de rede e áudio nunca executam no thread principal."),
        Spacer(1, 6),
        card(
            "TRANSCRIÇÃO E PERGUNTA-DESAFIO",
            "Ao vivo, o servidor transcreve o áudio limpo. No experimento, o modo headless salva o áudio recebido e o transcreve depois. A diferença de WER sustenta a discussão sobre servidor versus cliente.",
            BLUE_LIGHT,
            NAVY_2,
        ),
        PageBreak(),
    ]

    # 4. Modularidade e dupla
    story += heading(
        "3. Modularidade e divisão da dupla",
        "A organização separa domínio, infraestrutura e apresentação. Isso permite desenvolvimento paralelo sem duplicar regras de negócio ou código experimental.",
    )
    story += [module_tree(), Spacer(1, 9)]
    story += [
        card(
            "DEPENDÊNCIA PERMITIDA",
            "ui → workers → core → shared. O sentido inverso é proibido: core não importa PySide6, widgets ou componentes da GUI.",
            GREEN_LIGHT,
            GREEN,
        ),
        Spacer(1, 8),
    ]
    roles = Table(
        [
            [p("INTEGRANTE A • SERVIDOR E EXPERIMENTO", "CardTitle"), p("INTEGRANTE B • CLIENTE E INTELIGÊNCIA", "CardTitle")],
            [
                p("Protocolo; broadcaster UDP; sessão WebSocket; PCM/Opus; netem; captura headless; CSV; WER; gráficos e orçamento de latência.", "CardBody"),
                p("PySide6; workers e sinais; áudio; legendas; controles; faster-whisper; RAG/Ollama; Ed25519 e experiência da demonstração.", "CardBody"),
            ],
            [p("Revisa: sincronização, IA e roteiro.", "CardBody"), p("Revisa: pacote, métricas e reprodutibilidade.", "CardBody")],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    roles.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BLUE_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), TEAL_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [roles, Spacer(1, 9), p("MARCOS DE INTEGRAÇÃO", "Section")]
    milestones = [
        [p("Marco", "TableHeader"), p("Entrada", "TableHeader"), p("Critério de aceite conjunto", "TableHeader")],
        [p("M1 • Transporte", "TableCellBold"), p("Servidor UDP + cliente core", "TableCell"), p("Dois processos recebem e ordenam o mesmo áudio.", "TableCell")],
        [p("M2 • Aplicação", "TableCellBold"), p("Core + PySide6", "TableCell"), p("Conectar, tocar, pausar e mostrar métricas sem travar a UI.", "TableCell")],
        [p("M3 • Inteligência", "TableCellBold"), p("WebSocket + ASR/RAG", "TableCell"), p("Legenda temporal, selo, fonte e assinatura válida.", "TableCell")],
        [p("M4 • Evidência", "TableCellBold"), p("Core headless + netem", "TableCell"), p("30 linhas válidas em CSV e gráficos reproduzíveis.", "TableCell")],
    ]
    story += [styled_table(milestones, [38 * mm, 56 * mm, 84 * mm]), Spacer(1, 7)]
    story += [
        bullet("Checkpoints a cada 2-3 horas; ambos executam a aplicação a partir de um ambiente limpo."),
        bullet("Mocks de pacote e legenda liberam o trabalho da GUI antes de o servidor estar completo."),
        bullet("Todo módulo público possui tipo, docstring curta, teste essencial e erro compreensível."),
        PageBreak(),
    ]

    # 5. Cronograma
    story += heading(
        "4. Cronograma crítico da implementação",
        "O núcleo vem antes da interface. PyInstaller é acabamento opcional e não pode consumir o tempo reservado ao experimento ou ao relatório.",
    )
    schedule = [
        [p("Janela", "TableHeader"), p("Integrante A", "TableHeader"), p("Integrante B", "TableHeader"), p("Marco", "TableHeader")],
        [p("21/11 • 16:00-17:00", "TableCellBold"), p("Estrutura, protocolo e áudio de teste.", "TableCell"), p("Estrutura cliente, janela e eventos simulados.", "TableCell"), p("M0: instalação e testes básicos.", "TableCell")],
        [p("17:00-20:00", "TableCellBold"), p("Broadcaster UDP + contratos WebSocket.", "TableCell"), p("Receiver + jitter + playback PCM.", "TableCell"), p("M1: áudio em dois clientes core.", "TableCell")],
        [p("20:00-21:00", "TableCellBold"), p("Integração e revisão", "TableCell"), p("Integração e revisão", "TableCell"), p("Protocolo congelado; primeira demo gravada.", "TableCell")],
        [p("21:00-23:30", "TableCellBold"), p("Métricas, controles e captura headless.", "TableCell"), p("PySide6, workers, sinais e legenda.", "TableCell"), p("M2: cliente desktop funcional.", "TableCell")],
        [p("22/11 • 08:00-10:30", "TableCellBold"), p("Opus + automação netem.", "TableCell"), p("Whisper + RAG + Ed25519.", "TableCell"), p("M3: incrementos isolados funcionando.", "TableCell")],
        [p("10:30-13:30", "TableCellBold"), p("Executar matriz de 30 testes.", "TableCell"), p("30 afirmações e acabamento da GUI.", "TableCell"), p("M4: CSV e avaliação da inteligência.", "TableCell")],
        [p("13:30-15:30", "TableCellBold"), p("Gráficos e latência.", "TableCell"), p("Análise, fontes e pergunta-desafio.", "TableCell"), p("M5: figuras finais aprovadas.", "TableCell")],
        [p("15:30-18:00", "TableCellBold"), p("README e reprodução limpa.", "TableCell"), p("Relatório e roteiro da demonstração.", "TableCell"), p("M6: entrega candidata congelada.", "TableCell")],
        [p("18:00-19:30", "TableCellBold"), p("Ensaio e correções críticas", "TableCell"), p("Ensaio e correções críticas", "TableCell"), p("M7: backup, upload e confirmação.", "TableCell")],
    ]
    story += [styled_table(schedule, [35 * mm, 47 * mm, 47 * mm, 49 * mm]), Spacer(1, 8)]
    priority = Table(
        [
            [p("1", "BigMetric"), p("2", "BigMetric"), p("3", "BigMetric"), p("4", "BigMetric")],
            [p("UDP + jitter", "MetricLabel"), p("Experimento", "MetricLabel"), p("Legenda + fatos", "MetricLabel"), p("GUI + executável", "MetricLabel")],
        ],
        colWidths=[CONTENT_W / 4] * 4,
    )
    priority.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), GREEN_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), TEAL_LIGHT),
                ("BACKGROUND", (2, 0), (2, -1), BLUE_LIGHT),
                ("BACKGROUND", (3, 0), (3, -1), PAPER),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story += [p("ORDEM DE PRIORIDADE EM CASO DE ATRASO", "Section"), priority, Spacer(1, 8)]
    story += [
        card(
            "CORTE AUTOMÁTICO",
            "Se o empacotamento consumir mais de 45 minutos, entregar com ambiente virtual e script start-client.ps1. O executável não faz parte do núcleo avaliado.",
            RED_LIGHT,
            RED,
        ),
        PageBreak(),
    ]

    # 6. Experimento
    story += heading(
        "5. Experimento obrigatório",
        "A GUI não participa da coleta. O runner headless reutiliza receptor, jitter buffer e codecs do cliente desktop, garantindo equivalência entre demonstração e medição.",
    )
    story += [
        card(
            "HIPÓTESE",
            "O aumento da perda elevará o WER. Opus reduzirá a banda, enquanto a qualidade sob perda dependerá do codec e da ocultação utilizada. A conclusão será determinada pelos dados.",
            AMBER_LIGHT,
            AMBER,
        ),
        Spacer(1, 8),
    ]
    matrix = [
        [p("Fator", "TableHeader"), p("Valores", "TableHeader"), p("Controle", "TableHeader")],
        [p("Codec", "TableCellBold"), p("PCM e Opus", "TableCell"), p("Mesmo áudio, duração e taxa de amostragem.", "TableCell")],
        [p("Perda", "TableCellBold"), p("0%, 1%, 5%, 10% e 20%", "TableCell"), p("tc netem na mesma interface/namespace.", "TableCell")],
        [p("Repetições", "TableCellBold"), p("3 por combinação = 30", "TableCell"), p("Ordem registrada e execução automatizada.", "TableCell")],
        [p("Jitter buffer", "TableCellBold"), p("100 ms fixos", "TableCell"), p("Não variar no experimento principal.", "TableCell")],
        [p("ASR", "TableCellBold"), p("Mesmo modelo/parâmetros", "TableCell"), p("faster-whisper base, language=pt, int8.", "TableCell")],
    ]
    story += [styled_table(matrix, [43 * mm, 56 * mm, 79 * mm]), Spacer(1, 8)]
    steps = Table(
        [[
            p("1<br/><b>netem</b>", "TableCell"),
            p("2<br/><b>transmitir</b>", "TableCell"),
            p("3<br/><b>reconstruir</b>", "TableCell"),
            p("4<br/><b>transcrever</b>", "TableCell"),
            p("5<br/><b>calcular WER</b>", "TableCell"),
            p("6<br/><b>salvar CSV</b>", "TableCell"),
        ]],
        colWidths=[CONTENT_W / 6] * 6,
    )
    steps.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, TEAL),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [p("PIPELINE DE CADA EXECUÇÃO", "Section"), steps, Spacer(1, 8)]
    story += [
        p("COLUNAS DO CSV", "Section"),
        p(
            "run, codec, loss_pct, packets_sent, packets_received, packets_lost, packets_late, bytes_received, jitter_buffer_ms, wer, capture_to_send_ms, network_ms, buffer_ms, transcription_ms, total_ms",
            "Note",
        ),
        Spacer(1, 7),
        p("GRÁFICOS MÍNIMOS", "Section"),
        bullet("WER médio x perda com uma curva por codec e barras de desvio padrão."),
        bullet("Banda média de PCM x Opus, incluindo cabeçalhos."),
        bullet("Perda configurada x perda observada para validar o ambiente."),
        bullet("Orçamento de latência: captura, envio, rede, jitter, ASR e legenda."),
        Spacer(1, 6),
        card(
            "REPRODUTIBILIDADE",
            "O áudio de referência, a transcrição esperada, os comandos netem, o seed quando aplicável e a configuração do modelo devem ser versionados ou documentados.",
            GREEN_LIGHT,
            GREEN,
        ),
        PageBreak(),
    ]

    # 7. Incrementos e interface
    story += heading(
        "6. Incrementos e experiência do cliente",
        "A dupla cobre Inteligência e Segurança. O painel desktop torna esses resultados visíveis sem bloquear o caminho crítico do áudio.",
    )
    increments = Table(
        [
            [p("INTELIGÊNCIA • FATOS", "CardTitle"), p("SEGURANÇA • INTEGRIDADE", "CardTitle")],
            [
                p("Sentença verificável → recuperação Top-3 → Ollama → selo confirmada, contestada ou sem evidência → fonte real.", "CardBody"),
                p("Ed25519 sobre session_id, sequence, start_ms, end_ms e text. Qualquer alteração invalida o trecho.", "CardBody"),
            ],
            [p("Avaliação: 15 verdadeiras + 15 falsas.", "CardBody"), p("Demonstração: adulterar uma legenda e rejeitá-la.", "CardBody")],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    increments.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), TEAL_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), BLUE_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [increments, Spacer(1, 9)]
    ui = [
        [p("Área da janela", "TableHeader"), p("Informação", "TableHeader"), p("Origem", "TableHeader")],
        [p("Conexão", "TableCellBold"), p("Servidor, porta UDP, jitter e codec.", "TableCell"), p("Configuração do cliente.", "TableCell")],
        [p("Legenda", "TableCellBold"), p("Texto atual, intervalo temporal e integridade.", "TableCell"), p("WebSocket + verificação Ed25519.", "TableCell")],
        [p("Fatos", "TableCellBold"), p("Selo, afirmação, fonte e justificativa curta.", "TableCell"), p("Atualização assíncrona do backend.", "TableCell")],
        [p("Métricas", "TableCellBold"), p("Recebidos, perdidos, atrasados, jitter e latência.", "TableCell"), p("Núcleo UDP/jitter buffer.", "TableCell")],
        [p("Controles", "TableCellBold"), p("Conectar, pausar, continuar e parar.", "TableCell"), p("Máquina de estados do cliente.", "TableCell")],
    ]
    story += [p("PAINEL ÚNICO", "Section"), styled_table(ui, [42 * mm, 78 * mm, 58 * mm]), Spacer(1, 8)]
    story += [
        p("REGRAS DE CONCORRÊNCIA", "Section"),
        bullet("Thread principal: somente widgets e reação a sinais."),
        bullet("Network worker: UDP e WebSocket; publica pacotes, legendas e erros."),
        bullet("Playback worker: consome o jitter buffer no ritmo de 20 ms."),
        bullet("Filas possuem tamanho máximo; IA lenta nunca bloqueia áudio ou interface."),
        Spacer(1, 7),
        card(
            "COMPORTAMENTO ASSÍNCRONO",
            "A legenda aparece quando disponível; o selo factual chega depois como atualização da mesma sequência. A GUI deixa claro quando a checagem ainda está pendente.",
            AMBER_LIGHT,
            AMBER,
        ),
        Spacer(1, 7),
        card(
            "EMPACOTAMENTO",
            "Desenvolvimento: python -m client. Entrega: script de configuração reproduzível. PyInstaller --onedir é preferível a --onefile para reduzir surpresas com bibliotecas de áudio.",
            BLUE_LIGHT,
            NAVY_2,
        ),
        PageBreak(),
    ]

    # 8. Riscos e entrega
    story += heading(
        "7. Riscos, demonstração e entrega",
        "A versão final precisa provar rede, experimento e domínio conceitual. A janela desktop é uma forma de observação, não o objeto principal da avaliação.",
    )
    risks = [
        [p("Risco", "TableHeader"), p("Sinal", "TableHeader"), p("Contingência", "TableHeader")],
        [p("GUI congela", "TableCellBold"), p("Janela para de responder.", "TableCell"), p("Mover rede/áudio para workers; UI só recebe sinais.", "TableCell")],
        [p("Dispositivo de áudio", "TableCellBold"), p("Falha ao abrir saída.", "TableCell"), p("Permitir seleção; fallback para gravar WAV sem tocar.", "TableCell")],
        [p("ASR fica atrasado", "TableCellBold"), p("Fila de janelas cresce.", "TableCell"), p("Modelo tiny/base, int8, janela de 4-5 s; aceitar atraso do texto.", "TableCell")],
        [p("Opus não carrega", "TableCellBold"), p("Binding/libopus ausente.", "TableCell"), p("Resolver cedo no Linux; manter PCM atrás da mesma interface.", "TableCell")],
        [p("PyInstaller falha", "TableCellBold"), p("DLL/plugin Qt ausente.", "TableCell"), p("Entregar venv + script; empacotamento não bloqueia a entrega.", "TableCell")],
    ]
    story += [styled_table(risks, [47 * mm, 49 * mm, 82 * mm]), Spacer(1, 8)]
    story += [p("ROTEIRO DE DEMONSTRAÇÃO • 5 MINUTOS", "Section")]
    demo = [
        [p("0:00-0:40", "TableCellBold"), p("Arquitetura: UDP para áudio, WebSocket para texto e controle.", "TableCell")],
        [p("0:40-1:40", "TableCellBold"), p("Duas janelas clientes recebem o mesmo áudio; mostrar sequência e timestamp.", "TableCell")],
        [p("1:40-2:30", "TableCellBold"), p("Alterar jitter buffer; exibir perda, atraso, pausa e retomada.", "TableCell")],
        [p("2:30-3:30", "TableCellBold"), p("Legenda, selo factual, fonte e detecção de trecho adulterado.", "TableCell")],
        [p("3:30-4:30", "TableCellBold"), p("Gráficos WER x perda, banda PCM/Opus e orçamento de latência.", "TableCell")],
        [p("4:30-5:00", "TableCellBold"), p("Responder onde transcrever usando os próprios resultados.", "TableCell")],
    ]
    story += [styled_table(demo, [33 * mm, 145 * mm], header=False), Spacer(1, 8)]
    checklist = Table(
        [
            [p("CHECKLIST", "CardTitle"), p("RELATÓRIO • ATÉ 6 PÁGINAS", "CardTitle")],
            [
                p(
                    "□ instalação do zero<br/>□ servidor e dois clientes<br/>□ áudio PCM/Opus<br/>□ CSV das 30 execuções<br/>□ gráficos versionados<br/>□ 30 afirmações avaliadas<br/>□ README e comandos<br/>□ backup e upload conferido",
                    "CardBody",
                ),
                p(
                    "1. Problema e arquitetura<br/>2. Protocolo, jitter e GUI<br/>3. Transcrição, RAG e integridade<br/>4. Metodologia experimental<br/>5. Resultados e discussão<br/>6. Pergunta-desafio e conclusão",
                    "CardBody",
                ),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    checklist.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [checklist, Spacer(1, 8), p("FONTES DE REFERÊNCIA", "Section")]
    refs = (
        "Especificação: <i>Projetos de Redes de Computadores - Propostas de Trabalho</i>, Projeto 2. "
        "Cronograma: <i>Redes-2026-02-Cronograma</i>. "
        '<link href="https://doc.qt.io/qtforpython-6/" color="#0E7C86">Qt for Python / PySide6</link> • '
        '<link href="https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html" color="#0E7C86">Signals e slots</link> • '
        '<link href="https://fastapi.tiangolo.com/advanced/websockets/" color="#0E7C86">FastAPI WebSockets</link> • '
        '<link href="https://github.com/SYSTRAN/faster-whisper" color="#0E7C86">faster-whisper</link> • '
        '<link href="https://pyinstaller.org/en/stable/usage.html" color="#0E7C86">PyInstaller</link>.'
    )
    story += [p(refs, "Note"), Spacer(1, 7)]
    story += [
        card(
            "CRITÉRIO FINAL DE SUCESSO",
            "A equipe instala o ambiente, inicia o servidor e dois clientes desktop, demonstra áudio e legendas, reproduz o experimento e explica cada decisão com base nos conceitos da disciplina.",
            TEAL_LIGHT,
            TEAL,
        )
    ]
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = PlanningDocTemplate(str(OUTPUT))
    doc.title = "Planejamento - Projeto 2 de Redes - PySide6"
    doc.subject = "Áudio ao vivo com cliente desktop PySide6"
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()

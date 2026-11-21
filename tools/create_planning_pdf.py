from __future__ import annotations

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "planejamento-projeto-2-redes.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
MARGIN_TOP = 17 * mm
MARGIN_BOTTOM = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

NAVY = HexColor("#102A43")
NAVY_2 = HexColor("#163A5F")
TEAL = HexColor("#0E7C86")
TEAL_LIGHT = HexColor("#E8F4F4")
BLUE_LIGHT = HexColor("#EAF2F8")
AMBER = HexColor("#E5A11A")
AMBER_LIGHT = HexColor("#FFF4D6")
RED = HexColor("#C2413B")
RED_LIGHT = HexColor("#FCEBE9")
GREEN = HexColor("#2E7D5B")
GREEN_LIGHT = HexColor("#E9F5EF")
INK = HexColor("#243B53")
MUTED = HexColor("#627D98")
LINE = HexColor("#D9E2EC")
PAPER = HexColor("#F7F9FC")
WHITE = colors.white


def register_fonts() -> None:
    font_dir = Path(r"C:\Windows\Fonts")
    pdfmetrics.registerFont(TTFont("Arial", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(font_dir / "ariali.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-BoldItalic", str(font_dir / "arialbi.ttf")))
    pdfmetrics.registerFontFamily(
        "Arial",
        normal="Arial",
        bold="Arial-Bold",
        italic="Arial-Italic",
        boldItalic="Arial-BoldItalic",
    )


register_fonts()

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverKicker",
        fontName="Arial-Bold",
        fontSize=9,
        leading=12,
        textColor=HexColor("#8ED8DD"),
        spaceAfter=8,
        tracking=1.2,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName="Arial-Bold",
        fontSize=28,
        leading=33,
        textColor=WHITE,
        spaceAfter=14,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        fontName="Arial",
        fontSize=12,
        leading=18,
        textColor=HexColor("#D9EAF2"),
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="PageTitle",
        fontName="Arial-Bold",
        fontSize=19,
        leading=23,
        textColor=NAVY,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="PageLead",
        fontName="Arial",
        fontSize=9.5,
        leading=14,
        textColor=MUTED,
        spaceAfter=11,
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        fontName="Arial-Bold",
        fontSize=10.2,
        leading=13,
        textColor=TEAL,
        spaceBefore=8,
        spaceAfter=5,
        tracking=0.4,
    )
)
styles.add(
    ParagraphStyle(
        name="BodySmall",
        fontName="Arial",
        fontSize=8.7,
        leading=12.2,
        textColor=INK,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyTiny",
        fontName="Arial",
        fontSize=7.6,
        leading=10.2,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletSmall",
        fontName="Arial",
        fontSize=8.5,
        leading=11.5,
        textColor=INK,
        leftIndent=11,
        firstLineIndent=-7,
        bulletIndent=0,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="CardTitle",
        fontName="Arial-Bold",
        fontSize=9,
        leading=11,
        textColor=NAVY,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="CardBody",
        fontName="Arial",
        fontSize=7.8,
        leading=10.4,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHeader",
        fontName="Arial-Bold",
        fontSize=7.4,
        leading=9,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        fontName="Arial",
        fontSize=7.25,
        leading=9.3,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCellBold",
        fontName="Arial-Bold",
        fontSize=7.25,
        leading=9.3,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="Note",
        fontName="Arial-Italic",
        fontSize=7.8,
        leading=10.4,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="BigMetric",
        fontName="Arial-Bold",
        fontSize=20,
        leading=21,
        textColor=NAVY,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="MetricLabel",
        fontName="Arial",
        fontSize=7.6,
        leading=9.5,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)


def p(text: str, style: str = "BodySmall") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", styles["BulletSmall"])


def heading(title: str, lead: str) -> list:
    return [p(title, "PageTitle"), p(lead, "PageLead")]


def card(title: str, body: str, bg=BLUE_LIGHT, accent=TEAL, width=None) -> Table:
    width = width or CONTENT_W
    data = [[p(title, "CardTitle")], [p(body, "CardBody")]]
    t = Table(data, colWidths=[width], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.6, accent),
                ("LINEBEFORE", (0, 0), (0, -1), 3.2, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]
        )
    )
    return t


def styled_table(data, col_widths, header=True, font_size=None, row_bgs=True) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ]
    if row_bgs:
        for idx in range(1 if header else 0, len(data)):
            commands.append(("BACKGROUND", (0, idx), (-1, idx), WHITE if idx % 2 else PAPER))
    if font_size:
        commands.append(("FONTSIZE", (0, 0), (-1, -1), font_size))
    t.setStyle(TableStyle(commands))
    return t


def metric_card(value: str, label: str, bg=WHITE) -> Table:
    t = Table([[p(value, "BigMetric")], [p(label, "MetricLabel")]], colWidths=[CONTENT_W / 4 - 5])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]
        )
    )
    return t


def arrow(d: Drawing, x1, y1, x2, y2, color=TEAL, width=1.5):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    size = 5
    d.add(Polygon([x2, y2, x2 - size, y2 + size / 2, x2 - size, y2 - size / 2], fillColor=color, strokeColor=color))


def architecture_diagram() -> Drawing:
    w = CONTENT_W
    h = 225
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, rx=8, ry=8, fillColor=PAPER, strokeColor=LINE, strokeWidth=0.7))

    boxes = [
        (12, 148, 92, 48, "FONTE", "WAV ou microfone", AMBER_LIGHT, AMBER),
        (124, 135, 122, 74, "FASTAPI / PYTHON", "UDP + WebSocket\ntranscrição + RAG", BLUE_LIGHT, TEAL),
        (284, 148, 110, 48, "LISTENER AGENT", "UDP + jitter + Opus", GREEN_LIGHT, GREEN),
        (422, 148, 76, 48, "NEXT.JS", "painel web", TEAL_LIGHT, TEAL),
        (124, 42, 122, 52, "FASTER-WHISPER", "modelo base / int8", WHITE, NAVY_2),
        (284, 42, 110, 52, "RAG + OLLAMA", "fontes + veredito", WHITE, NAVY_2),
        (422, 42, 76, 52, "MÉTRICAS", "CSV + gráficos", WHITE, NAVY_2),
    ]
    for x, y, bw, bh, title, body, fill, stroke in boxes:
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=stroke, strokeWidth=1.0))
        d.add(String(x + 7, y + bh - 15, title, fontName="Arial-Bold", fontSize=7.6, fillColor=stroke))
        for idx, line in enumerate(body.split("\n")):
            d.add(String(x + 7, y + bh - 29 - idx * 11, line, fontName="Arial", fontSize=7.2, fillColor=INK))

    arrow(d, 104, 172, 124, 172, AMBER)
    arrow(d, 246, 172, 284, 172, TEAL)
    arrow(d, 394, 172, 422, 172, TEAL)
    arrow(d, 185, 135, 185, 94, NAVY_2)
    arrow(d, 246, 69, 284, 69, NAVY_2)
    arrow(d, 394, 69, 422, 69, NAVY_2)

    d.add(String(255, 184, "UDP / áudio", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(396, 184, "WS local", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(198, 110, "áudio limpo", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(254, 79, "texto", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    d.add(String(397, 79, "eventos", fontName="Arial-Italic", fontSize=7, fillColor=MUTED))
    return d


def cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(HexColor("#315B7A"))
    canvas.setLineWidth(0.8)
    for offset in range(0, 7):
        y = 54 * mm + offset * 5 * mm
        canvas.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)
    canvas.setFillColor(HexColor("#8ED8DD"))
    canvas.circle(PAGE_W - 31 * mm, 27 * mm, 7 * mm, stroke=0, fill=1)
    canvas.setFillColor(WHITE)
    canvas.setFont("Arial-Bold", 8)
    canvas.drawCentredString(PAGE_W - 31 * mm, 25.8 * mm, "P2")
    canvas.setFont("Arial", 7.5)
    canvas.setFillColor(HexColor("#C9DCE8"))
    canvas.drawString(MARGIN_X, 17 * mm, "Plano operacional • Redes de Computadores • UFES")
    canvas.restoreState()


def later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(WHITE)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN_X, PAGE_H - 12 * mm, PAGE_W - MARGIN_X, PAGE_H - 12 * mm)
    canvas.setFont("Arial-Bold", 7.2)
    canvas.setFillColor(TEAL)
    canvas.drawString(MARGIN_X, PAGE_H - 8.5 * mm, "PROJETO 2 • ÁUDIO AO VIVO")
    canvas.setFont("Arial", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 8.5 * mm, "Plano de execução para dupla")
    canvas.line(MARGIN_X, 11 * mm, PAGE_W - MARGIN_X, 11 * mm)
    canvas.setFont("Arial", 7.2)
    canvas.drawString(MARGIN_X, 7 * mm, "21 de novembro de 2026")
    canvas.drawRightString(PAGE_W - MARGIN_X, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def all_pages(canvas, doc):
    if doc.page == 1:
        cover_page(canvas, doc)
    else:
        later_pages(canvas, doc)


class PlanningDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Planejamento - Projeto 2 de Redes",
            author="Equipe do Projeto 2",
            subject="Áudio ao vivo com transcrição e checagem de fatos",
        )
        frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            CONTENT_W,
            PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
            id="main_frame",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="Main", frames=[frame], onPage=all_pages)])


def build_story() -> list:
    s: list = []

    # 1. Cover
    s += [
        Spacer(1, 31 * mm),
        p("PLANO OPERACIONAL • ENTREGA EM 22/11/2026", "CoverKicker"),
        p("Áudio ao vivo com<br/>transcrição e checagem de fatos", "CoverTitle"),
        p(
            "Projeto 2 de Redes de Computadores<br/>Arquitetura Python + FastAPI + Next.js + listener agent",
            "CoverSub",
        ),
        Spacer(1, 13 * mm),
    ]
    cover_cards = Table(
        [
            [p("DECISÃO DE STACK", "CardTitle"), p("ESTRATÉGIA DE ENTREGA", "CardTitle")],
            [
                p(
                    "Python concentra UDP, jitter, transcrição, RAG e métricas. Next.js entrega a interface sem esconder os mecanismos de rede.",
                    "CardBody",
                ),
                p(
                    "Priorizar núcleo, experimento e evidências. Congelar escopo antes dos refinamentos visuais.",
                    "CardBody",
                ),
            ],
        ],
        colWidths=[CONTENT_W / 2 - 5, CONTENT_W / 2 - 5],
        hAlign="LEFT",
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
    s += [cover_cards, Spacer(1, 17 * mm)]
    s.append(
        Table(
            [[metric_card("2", "integrantes", TEAL_LIGHT), metric_card("2", "fluxos de rede", TEAL_LIGHT), metric_card("30", "execuções mínimas", TEAL_LIGHT), metric_card("1", "dia até a entrega", TEAL_LIGHT)]],
            colWidths=[CONTENT_W / 4] * 4,
            style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)],
        )
    )
    s += [Spacer(1, 14 * mm), p("Versão 1.0 • Planejamento para execução imediata", "CoverSub"), PageBreak()]

    # 2. Executive scope
    s += heading(
        "1. Decisão executiva e escopo",
        "A meta não é construir uma plataforma completa: é demonstrar os conceitos de Redes, produzir dados repetíveis e sustentar a análise com evidências.",
    )
    s += [
        card(
            "RECOMENDAÇÃO FINAL",
            "Usar <b>FastAPI/Python</b> como backend central, um <b>listener agent Python</b> por ouvinte e <b>Next.js</b> como painel. NestJS permanece tecnicamente válido, mas foi retirado do caminho crítico por exigir integração adicional com o ecossistema Python de áudio, ASR e métricas.",
            TEAL_LIGHT,
            TEAL,
        ),
        Spacer(1, 8),
        p("O QUE PRECISA EXISTIR NA ENTREGA", "Section"),
    ]
    req_data = [
        [p("Bloco", "TableHeader"), p("Entrega verificável", "TableHeader"), p("Critério de aceite", "TableHeader")],
        [p("Núcleo de rede", "TableCellBold"), p("Áudio em pacotes UDP para dois clientes, com sequência e timestamp.", "TableCell"), p("Dois listeners recebem o mesmo fluxo e registram métricas independentes.", "TableCell")],
        [p("Jitter buffer", "TableCellBold"), p("Buffer configurável, perda e atraso contabilizados.", "TableCell"), p("Execução com 60, 100 ou 200 ms e reprodução contínua.", "TableCell")],
        [p("Canal de texto", "TableCellBold"), p("Legenda por WebSocket, separada do áudio.", "TableCell"), p("Cada segmento possui start_ms/end_ms e aparece na ordem correta.", "TableCell")],
        [p("Inteligência", "TableCellBold"), p("RAG local com selo e fonte para afirmações verificáveis.", "TableCell"), p("30 afirmações: 15 verdadeiras, 15 falsas; precisão e revocação.", "TableCell")],
        [p("Segurança", "TableCellBold"), p("Assinatura Ed25519 de cada trecho transcrito.", "TableCell"), p("Cliente detecta alteração em texto, timestamp ou sequência.", "TableCell")],
        [p("Experimento", "TableCellBold"), p("PCM x Opus sob cinco níveis de perda.", "TableCell"), p("3 repetições por combinação, CSV, médias, desvio padrão e gráficos.", "TableCell")],
    ]
    s += [styled_table(req_data, [36 * mm, 78 * mm, 64 * mm]), Spacer(1, 8)]
    s += [
        p("POR QUE ESSA STACK", "Section"),
        bullet("Python reduz a distância entre rede, áudio, faster-whisper, RAG, WER e geração de gráficos."),
        bullet("Next.js melhora a demonstração sem assumir funções que o navegador não pode cumprir, como abrir um socket UDP bruto."),
        bullet("O listener agent preserva o valor acadêmico: jitter, perdas, codec e reprodução continuam explícitos no código da equipe."),
        bullet("A dupla trabalha em paralelo, mas integra em checkpoints fixos para evitar dois projetos isolados."),
        Spacer(1, 6),
        card(
            "REGRA DE CORTE",
            "Se uma funcionalidade não melhora o núcleo, o experimento ou a explicação da pergunta-desafio, ela fica fora da versão de entrega.",
            AMBER_LIGHT,
            AMBER,
        ),
        PageBreak(),
    ]

    # 3. Architecture
    s += heading(
        "2. Arquitetura e contratos",
        "Três processos claros evitam misturar mídia, inteligência e interface. O backend coordena; o listener mede e reproduz; o Next apresenta.",
    )
    s += [architecture_diagram(), Spacer(1, 8)]
    flow_data = [
        [p("Fluxo", "TableHeader"), p("Transporte", "TableHeader"), p("Conteúdo", "TableHeader"), p("Responsabilidade", "TableHeader")],
        [p("Áudio", "TableCellBold"), p("UDP", "TableCell"), p("Quadros PCM/Opus + seq + timestamp", "TableCell"), p("Baixa latência; perda mensurável; sem retransmissão.", "TableCell")],
        [p("Texto/controle", "TableCellBold"), p("WebSocket", "TableCell"), p("Legenda, fatos, registro e estado", "TableCell"), p("Entrega ordenada e confiável; tolera atraso.", "TableCell")],
        [p("UI local", "TableCellBold"), p("WebSocket local", "TableCell"), p("Métricas, posição e comandos", "TableCell"), p("Conecta o Next ao listener sem converter o áudio de rede em WebSocket.", "TableCell")],
    ]
    s += [styled_table(flow_data, [31 * mm, 28 * mm, 64 * mm, 55 * mm]), Spacer(1, 8)]
    s += [p("CONTRATO DO PACOTE DE ÁUDIO", "Section")]
    packet = Table(
        [[p("versão", "TableCellBold"), p("codec", "TableCellBold"), p("sequência", "TableCellBold"), p("timestamp_samples", "TableCellBold"), p("payload_len", "TableCellBold"), p("payload", "TableCellBold")]],
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
    s += [packet, Spacer(1, 7)]
    s += [
        bullet("Formato de áudio: mono, 16 kHz, 16 bits, quadros de 20 ms (320 amostras; 640 bytes em PCM)."),
        bullet("O timestamp representa posição no áudio, não horário de parede. Legendas usam o mesmo eixo temporal."),
        bullet("O WebSocket registra IP/porta UDP, distribui transcrições e transporta controles de sessão."),
        bullet("Pausa interrompe a saída e limita o buffer; continuar retorna ao ponto ao vivo; parar encerra os sockets."),
        Spacer(1, 6),
        card(
            "DECISÃO SOBRE TRANSCRIÇÃO",
            "Na demonstração, o servidor transcreve o áudio limpo. No experimento, o cliente grava o áudio reconstruído e o transcreve ao final. Isso permite medir o WER causado pela rede e responder à pergunta-desafio com dados.",
            BLUE_LIGHT,
            NAVY_2,
        ),
        PageBreak(),
    ]

    # 4. Work split
    s += heading(
        "3. Divisão de trabalho da dupla",
        "Cada frente possui um líder e um revisor. Nenhum módulo é considerado pronto antes de passar por uma integração executável.",
    )
    role_table = Table(
        [
            [
                p("INTEGRANTE A • MÍDIA E REDE", "CardTitle"),
                p("INTEGRANTE B • IA E EXPERIÊNCIA", "CardTitle"),
            ],
            [
                p("Protocolo UDP; broadcaster; listener; jitter buffer; PCM/Opus; reprodução; netem; coleta de métricas e execução experimental.", "CardBody"),
                p("FastAPI e WebSocket; faster-whisper; RAG/Ollama; assinatura Ed25519; Next.js; avaliação das 30 afirmações; narrativa e demonstração.", "CardBody"),
            ],
            [
                p("Revisa: timestamp, sincronização e gráficos.", "CardBody"),
                p("Revisa: contratos, logs e reprodutibilidade.", "CardBody"),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    role_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BLUE_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    s += [role_table, Spacer(1, 9), p("MATRIZ DE RESPONSABILIDADE", "Section")]
    raci = [
        [p("Entregável", "TableHeader"), p("Líder", "TableHeader"), p("Revisor", "TableHeader"), p("Saída esperada", "TableHeader")],
        [p("Contrato de protocolo", "TableCellBold"), p("A", "TableCell"), p("B", "TableCell"), p("protocol.py + exemplos de pacote", "TableCell")],
        [p("UDP e jitter", "TableCellBold"), p("A", "TableCell"), p("B", "TableCell"), p("Dois clientes + métricas", "TableCell")],
        [p("WebSocket e ASR", "TableCellBold"), p("B", "TableCell"), p("A", "TableCell"), p("Legenda temporal no cliente", "TableCell")],
        [p("RAG e assinatura", "TableCellBold"), p("B", "TableCell"), p("A", "TableCell"), p("Selo, fonte e verificação", "TableCell")],
        [p("Opus e netem", "TableCellBold"), p("A", "TableCell"), p("B", "TableCell"), p("30 execuções em CSV", "TableCell")],
        [p("Next.js", "TableCellBold"), p("B", "TableCell"), p("A", "TableCell"), p("Painel funcional, uma página", "TableCell")],
        [p("Relatório e apresentação", "TableCellBold"), p("Ambos", "TableCell"), p("Ambos", "TableCell"), p("Texto, gráficos e roteiro ensaiado", "TableCell")],
    ]
    s += [styled_table(raci, [57 * mm, 24 * mm, 24 * mm, 73 * mm]), Spacer(1, 8)]
    s += [
        p("PROTOCOLO DE COLABORAÇÃO", "Section"),
        bullet("Branches curtas por módulo; integração na branch principal apenas com comando de reprodução documentado."),
        bullet("Checkpoint obrigatório a cada 2-3 horas: ambos executam a mesma demonstração do zero."),
        bullet("Todo evento de rede possui log estruturado; evitar depuração apenas por prints soltos."),
        bullet("Um integrante não espera o outro: mocks de legenda e de pacotes permitem desenvolvimento paralelo."),
        Spacer(1, 6),
        card(
            "DEFINIÇÃO DE PRONTO",
            "Código executa em uma máquina limpa, produz evidência observável, tem falha compreensível e está descrito no README. 'Funcionou uma vez' não conta como pronto.",
            GREEN_LIGHT,
            GREEN,
        ),
        PageBreak(),
    ]

    # 5. Schedule
    s += heading(
        "4. Cronograma crítico: 21 e 22 de novembro",
        "O cronograma assume entrega no fim do dia 22/11. Se o horário oficial for anterior, antecipar o congelamento mantendo a mesma ordem de prioridades.",
    )
    schedule = [
        [p("Janela", "TableHeader"), p("Integrante A", "TableHeader"), p("Integrante B", "TableHeader"), p("Marco de integração", "TableHeader")],
        [p("21/11 • 16:00-17:00", "TableCellBold"), p("Contrato UDP, amostra WAV e estrutura do repo.", "TableCell"), p("FastAPI, Next e contratos WebSocket.", "TableCell"), p("M0: projeto sobe e healthcheck responde.", "TableCell")],
        [p("17:00-20:00", "TableCellBold"), p("Broadcaster + listener + jitter PCM.", "TableCell"), p("WebSocket + tela com eventos simulados.", "TableCell"), p("M1: dois clientes recebem áudio e a UI conecta.", "TableCell")],
        [p("20:00-21:00", "TableCellBold"), p("Revisão conjunta", "TableCell"), p("Revisão conjunta", "TableCell"), p("Corrigir protocolo; registrar primeira demo.", "TableCell")],
        [p("21:00-23:30", "TableCellBold"), p("Playback, perdas, atraso e controles.", "TableCell"), p("faster-whisper e legenda temporal.", "TableCell"), p("M2: áudio + legenda sincronizados.", "TableCell")],
        [p("23:30-00:00", "TableCellBold"), p("Commit estável", "TableCell"), p("Commit estável", "TableCell"), p("Backup e lista de bloqueios para o dia 22.", "TableCell")],
        [p("22/11 • 08:00-10:30", "TableCellBold"), p("Opus + captura do áudio reconstruído.", "TableCell"), p("RAG, 30 afirmações e Ed25519.", "TableCell"), p("M3: incrementos demonstráveis isoladamente.", "TableCell")],
        [p("10:30-13:30", "TableCellBold"), p("Automação netem e 30 execuções.", "TableCell"), p("Next final + avaliação de fatos.", "TableCell"), p("M4: CSV completo e resultados da IA.", "TableCell")],
        [p("13:30-15:30", "TableCellBold"), p("Gráficos e orçamento de latência.", "TableCell"), p("Análise, pergunta-desafio e fontes.", "TableCell"), p("M5: figuras finais revisadas pelos dois.", "TableCell")],
        [p("15:30-18:00", "TableCellBold"), p("README e reprodução limpa.", "TableCell"), p("Relatório e slides/roteiro.", "TableCell"), p("M6: entrega candidata congelada.", "TableCell")],
        [p("18:00-19:30", "TableCellBold"), p("Ensaio e correções críticas", "TableCell"), p("Ensaio e correções críticas", "TableCell"), p("M7: upload, hash/backup e confirmação.", "TableCell")],
    ]
    s += [styled_table(schedule, [35 * mm, 47 * mm, 47 * mm, 49 * mm]), Spacer(1, 8)]
    s += [
        p("ORDEM DE PRIORIDADE EM CASO DE ATRASO", "Section"),
    ]
    priority = Table(
        [
            [p("1", "BigMetric"), p("2", "BigMetric"), p("3", "BigMetric"), p("4", "BigMetric")],
            [p("Núcleo UDP + jitter", "MetricLabel"), p("Experimento + CSV", "MetricLabel"), p("Legenda + fatos", "MetricLabel"), p("Interface e acabamento", "MetricLabel")],
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
    s += [priority, Spacer(1, 8)]
    s += [
        card(
            "CONGELAMENTO DE ESCOPO",
            "Após M6, somente erros que impedem execução, corrompem métricas ou invalidam a demonstração podem entrar. Melhorias visuais e refatorações ficam proibidas.",
            RED_LIGHT,
            RED,
        ),
        PageBreak(),
    ]

    # 6. Experiment
    s += heading(
        "5. Plano experimental obrigatório",
        "O experimento precisa ser reproduzível, ter variável controlada, repetições e gráficos. A transcrição do cliente é feita sobre o áudio que realmente atravessou a rede.",
    )
    s += [
        card(
            "HIPÓTESE",
            "O aumento da perda elevará o WER. Opus reduzirá fortemente a banda; o efeito relativo sobre o WER dependerá do codec e da ocultação aplicada. A conclusão será baseada nas medições, não em expectativa prévia.",
            AMBER_LIGHT,
            AMBER,
        ),
        Spacer(1, 8),
    ]
    exp_matrix = [
        [p("Fator", "TableHeader"), p("Valores", "TableHeader"), p("Controle", "TableHeader")],
        [p("Codec", "TableCellBold"), p("PCM e Opus", "TableCell"), p("Mesmo áudio, taxa de amostragem e duração.", "TableCell")],
        [p("Perda configurada", "TableCellBold"), p("0%, 1%, 5%, 10% e 20%", "TableCell"), p("tc netem no mesmo enlace/interface.", "TableCell")],
        [p("Repetições", "TableCellBold"), p("3 por combinação = 30 execuções", "TableCell"), p("Ordem registrada; idealmente alternar codecs.", "TableCell")],
        [p("Jitter buffer", "TableCellBold"), p("100 ms fixos", "TableCell"), p("Não variar dentro do experimento principal.", "TableCell")],
        [p("ASR", "TableCellBold"), p("Mesmo modelo e parâmetros", "TableCell"), p("faster-whisper base, language=pt, int8.", "TableCell")],
    ]
    s += [styled_table(exp_matrix, [43 * mm, 56 * mm, 79 * mm]), Spacer(1, 8)]
    s += [p("PIPELINE DE UMA EXECUÇÃO", "Section")]
    run_steps = Table(
        [[
            p("1<br/><b>Aplicar netem</b>", "TableCell"),
            p("2<br/><b>Transmitir áudio</b>", "TableCell"),
            p("3<br/><b>Salvar reconstruído</b>", "TableCell"),
            p("4<br/><b>Transcrever cliente</b>", "TableCell"),
            p("5<br/><b>Calcular WER</b>", "TableCell"),
            p("6<br/><b>Acrescentar CSV</b>", "TableCell"),
        ]],
        colWidths=[CONTENT_W / 6] * 6,
    )
    run_steps.setStyle(
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
    s += [run_steps, Spacer(1, 8), p("COLUNAS DO CSV", "Section")]
    s += [
        p(
            "run, codec, loss_pct, packets_sent, packets_received, packets_lost, packets_late, bytes_received, jitter_buffer_ms, wer, capture_to_send_ms, network_ms, buffer_ms, transcription_ms, total_ms",
            "Note",
        ),
        Spacer(1, 7),
        p("GRÁFICOS MÍNIMOS", "Section"),
        bullet("WER médio x perda, uma curva por codec, com barras de desvio padrão."),
        bullet("Banda média de PCM x Opus e custo adicional de cabeçalhos."),
        bullet("Perda configurada x perda observada para validar o ambiente."),
        bullet("Orçamento de latência: captura, empacotamento, rede, jitter, ASR e chegada da legenda."),
        Spacer(1, 6),
        card(
            "CUIDADO METODOLÓGICO",
            "Não medir latência entre máquinas subtraindo relógios não sincronizados. Preferir execução na mesma máquina/namespace ou medir durações locais e explicitar a limitação.",
            RED_LIGHT,
            RED,
        ),
        PageBreak(),
    ]

    # 7. AI and security
    s += heading(
        "6. Incrementos: inteligência e segurança",
        "Como o trabalho é em dupla, o plano cobre duas trilhas diferentes: checagem de fatos (Inteligência) e integridade da transcrição (Segurança).",
    )
    columns = Table(
        [
            [p("INTELIGÊNCIA • CHECAGEM DE FATOS", "CardTitle"), p("SEGURANÇA • INTEGRIDADE", "CardTitle")],
            [
                p("Extrair sentenças verificáveis, recuperar trechos da base, pedir veredito ao LLM e exibir selo com a fonte realmente consultada.", "CardBody"),
                p("Assinar cada segmento com Ed25519. Alteração de texto, sequência ou intervalo temporal deve invalidar a assinatura no cliente.", "CardBody"),
            ],
            [
                p("Saída: confirmada, contestada ou sem evidência.", "CardBody"),
                p("Saída: assinatura válida ou legenda adulterada.", "CardBody"),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    columns.setStyle(
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
    s += [columns, Spacer(1, 9), p("PIPELINE DE CHECAGEM", "Section")]
    ai_steps = [
        [p("Etapa", "TableHeader"), p("Implementação mínima", "TableHeader"), p("Proteção contra erro", "TableHeader")],
        [p("1. Seleção", "TableCellBold"), p("LLM marca frases verificáveis; lote pequeno.", "TableCell"), p("Ignorar opinião e comando; JSON estrito.", "TableCell")],
        [p("2. Recuperação", "TableCellBold"), p("TF-IDF/cosseno sobre base curta e versionada.", "TableCell"), p("Top-3 trechos com ID e origem persistidos.", "TableCell")],
        [p("3. Veredito", "TableCellBold"), p("Ollama local, temperatura 0, evidências no prompt.", "TableCell"), p("Sem evidência quando o corpus não sustenta conclusão.", "TableCell")],
        [p("4. Exibição", "TableCellBold"), p("Selo, afirmação, fonte e confiança/justificativa curta.", "TableCell"), p("Fonte vem do retriever, nunca é inventada pelo modelo.", "TableCell")],
    ]
    s += [styled_table(ai_steps, [35 * mm, 73 * mm, 70 * mm]), Spacer(1, 8)]
    s += [p("AVALIAÇÃO DAS 30 AFIRMAÇÕES", "Section")]
    s += [
        bullet("Montar conjunto fixo com 15 verdadeiras e 15 falsas dentro do domínio da base."),
        bullet("Executar o mesmo pipeline usado ao vivo, sem correção manual após ver o resultado."),
        bullet("Considerar 'contestada' como classe positiva para precisão e revocação; apresentar matriz de confusão."),
        bullet("Registrar também respostas 'sem evidência', pois cobertura e exatidão são trade-offs diferentes."),
        Spacer(1, 7),
        p("FORMATO ASSINADO", "Section"),
        card(
            "MENSAGEM CANÔNICA",
            "session_id | sequence | start_ms | end_ms | text. A serialização precisa ser determinística; o cliente verifica a chave pública antes de exibir a legenda como íntegra.",
            GREEN_LIGHT,
            GREEN,
        ),
        Spacer(1, 7),
        card(
            "COMPORTAMENTO ASSÍNCRONO",
            "A legenda aparece primeiro; o selo factual chega depois como atualização do mesmo sequence. A inteligência nunca deve bloquear o envio UDP ou a reprodução.",
            AMBER_LIGHT,
            AMBER,
        ),
        PageBreak(),
    ]

    # 8. Risks, delivery, report and references
    s += heading(
        "7. Riscos, roteiro e checklist de entrega",
        "O fechamento precisa provar funcionamento, reprodutibilidade e domínio conceitual. A interface é apoio; os dados são a evidência principal.",
    )
    risks = [
        [p("Risco", "TableHeader"), p("Sinal de alerta", "TableHeader"), p("Contingência", "TableHeader")],
        [p("ASR não acompanha tempo real", "TableCellBold"), p("Fila cresce continuamente.", "TableCell"), p("Modelo tiny/base, int8, janela de 4-5 s; aceitar atraso textual.", "TableCell")],
        [p("Opus falha no ambiente", "TableCellBold"), p("Binding/libopus não carrega.", "TableCell"), p("Resolver no Linux cedo; manter PCM estável e isolar codec atrás de interface.", "TableCell")],
        [p("Next consome tempo demais", "TableCellBold"), p("Mais de 2 h sem painel conectado.", "TableCell"), p("Uma página, CSS mínimo; demonstrar áudio pelo listener em terminal.", "TableCell")],
        [p("netem afeta outros fluxos", "TableCellBold"), p("WebSocket desconecta ou resultado varia.", "TableCell"), p("Namespace/interface isolada; registrar qdisc e perda observada.", "TableCell")],
        [p("RAG inventa fonte", "TableCellBold"), p("Referência não existe no corpus.", "TableCell"), p("Fonte anexada pelo retriever; LLM não gera identificador livre.", "TableCell")],
    ]
    s += [styled_table(risks, [52 * mm, 50 * mm, 76 * mm]), Spacer(1, 8)]
    s += [p("ROTEIRO DE DEMONSTRAÇÃO • 5 MINUTOS", "Section")]
    demo = [
        [p("0:00-0:40", "TableCellBold"), p("Arquitetura e diferença entre UDP e WebSocket.", "TableCell")],
        [p("0:40-1:40", "TableCellBold"), p("Dois clientes conectados, áudio tocando, sequência e timestamp nos logs.", "TableCell")],
        [p("1:40-2:30", "TableCellBold"), p("Alterar jitter buffer; mostrar perdas/atrasos e controles.", "TableCell")],
        [p("2:30-3:30", "TableCellBold"), p("Legenda sincronizada, selo factual e fonte; adulterar uma legenda e invalidar assinatura.", "TableCell")],
        [p("3:30-4:30", "TableCellBold"), p("Mostrar gráfico WER x perda e comparar PCM/Opus.", "TableCell")],
        [p("4:30-5:00", "TableCellBold"), p("Responder onde a transcrição deve rodar usando os próprios dados.", "TableCell")],
    ]
    s += [styled_table(demo, [33 * mm, 145 * mm], header=False), Spacer(1, 8)]
    checklist = Table(
        [
            [p("CHECKLIST DE ENTREGA", "CardTitle"), p("ESTRUTURA DO RELATÓRIO (ATÉ 6 PÁGINAS)", "CardTitle")],
            [
                p(
                    "□ README do zero<br/>□ requirements/package-lock<br/>□ comando único por processo<br/>□ CSV bruto e scripts<br/>□ gráficos versionados<br/>□ áudio de teste<br/>□ chaves de demonstração<br/>□ backup e upload conferido",
                    "CardBody",
                ),
                p(
                    "1. Problema e arquitetura<br/>2. Protocolo e jitter buffer<br/>3. Transcrição, RAG e integridade<br/>4. Metodologia experimental<br/>5. Resultados e discussão<br/>6. Pergunta-desafio, limitações e conclusão",
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
    s += [checklist, Spacer(1, 8), p("FONTES DE REFERÊNCIA", "Section")]
    refs = (
        "Especificação: <i>Projetos de Redes de Computadores - Propostas de Trabalho</i>, Projeto 2. "
        "Cronograma: <i>Redes-2026-02-Cronograma</i>. "
        '<link href="https://docs.python.org/3/library/asyncio-protocol.html" color="#0E7C86">Python asyncio</link> • '
        '<link href="https://fastapi.tiangolo.com/advanced/websockets/" color="#0E7C86">FastAPI WebSockets</link> • '
        '<link href="https://nextjs.org/docs/app/getting-started/server-and-client-components" color="#0E7C86">Next.js</link> • '
        '<link href="https://github.com/SYSTRAN/faster-whisper" color="#0E7C86">faster-whisper</link> • '
        '<link href="https://docs.ollama.com/capabilities/embeddings" color="#0E7C86">Ollama embeddings/RAG</link>.'
    )
    s += [p(refs, "Note"), Spacer(1, 7)]
    s += [
        card(
            "CRITÉRIO FINAL DE SUCESSO",
            "A equipe consegue clonar, instalar, executar, demonstrar dois ouvintes, reproduzir o experimento e explicar cada gráfico sem depender de correção manual ou serviço externo.",
            TEAL_LIGHT,
            TEAL,
        )
    ]

    return s


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = PlanningDocTemplate(str(OUTPUT))
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()

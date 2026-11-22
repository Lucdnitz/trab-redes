"""Gera o relatório final de até seis páginas a partir dos resultados experimentais."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results"
CSV_PATH = RESULTS / "results.csv"
OUTPUT = ROOT / "output" / "pdf" / "relatorio-final-projeto-2-redes.pdf"

NAVY = colors.HexColor("#102A43")
TEAL = colors.HexColor("#0E7C86")
LIGHT = colors.HexColor("#EAF4F4")
PAPER = colors.HexColor("#F7F9FC")
LINE = colors.HexColor("#CBD5E1")
MUTED = colors.HexColor("#526D82")


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def number(row: dict[str, str], key: str) -> float:
    return float(row.get(key, 0) or 0)


def mean(rows: list[dict[str, str]], key: str) -> float:
    return statistics.fmean(number(row, key) for row in rows)


def std(rows: list[dict[str, str]], key: str) -> float:
    values = [number(row, key) for row in rows]
    return statistics.stdev(values) if len(values) > 1 else 0.0


def pt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEAL,
            spaceBefore=5,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyAcademic",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12.2,
            alignment=TA_JUSTIFY,
            textColor=NAVY,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=9.6,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            "Callout",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY,
            backColor=LIGHT,
            borderColor=TEAL,
            borderWidth=0.7,
            borderPadding=7,
            spaceBefore=5,
            spaceAfter=6,
        )
    )
    return styles


STYLES = build_styles()


def p(text: str, style: str = "BodyAcademic") -> Paragraph:
    return Paragraph(text, STYLES[style])


def table(data, widths, *, header=True, font_size=7.8) -> Table:
    result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
    ]
    if header:
        rules += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    for row in range(1 if header else 0, len(data)):
        if row % 2 == 0:
            rules.append(("BACKGROUND", (0, row), (-1, row), PAPER))
    result.setStyle(TableStyle(rules))
    return result


def footer(canvas, doc) -> None:
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 13 * mm, width - 20 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 8.5 * mm, "Redes de Computadores - UFES - Projeto 2")
    canvas.drawRightString(width - 20 * mm, 8.5 * mm, f"Página {doc.page} de 6")
    canvas.restoreState()


def chart_pair(left: str, right: str, *, height: float = 62 * mm) -> Table:
    items = []
    for name in (left, right):
        path = RESULTS / name
        if not path.exists():
            raise FileNotFoundError(path)
        image = Image(str(path), width=82 * mm, height=height)
        items.append(image)
    result = Table([items], colWidths=[86 * mm, 86 * mm])
    result.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return result


def grouped(rows: list[dict[str, str]]) -> dict[tuple[str, int], list[dict[str, str]]]:
    groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["codec"], int(row["loss_pct"]))].append(row)
    return groups


def build_story(rows: list[dict[str, str]]) -> list:
    groups = grouped(rows)
    duration = number(rows[0], "duration_s")
    pcm_20 = groups[("PCM", 20)]
    opus_20 = groups[("OPUS", 20)]
    clean_gt = mean(groups[("PCM", 0)], "wer_vs_gt")

    story = [Spacer(1, 18 * mm)]
    story += [
        p("UNIVERSIDADE FEDERAL DO ESPÍRITO SANTO", "Subsection"),
        p("Centro Tecnológico - Departamento de Informática", "Small"),
        Spacer(1, 18 * mm),
        p("Áudio ao vivo com transcrição,<br/>resumo incremental e integridade", "CoverTitle"),
        p("Projeto 2 - Redes de Computadores", "Section"),
        Spacer(1, 8 * mm),
        p("Lucas D'Amato Nitz e Victor Dutra", "Callout"),
        p("Professor: Magnos Martinello<br/>Entrega: 22 de novembro de 2026", "Small"),
        Spacer(1, 18 * mm),
        p("RESUMO", "Subsection"),
        p(
            "Este trabalho implementa um serviço cliente-servidor para áudio ao vivo. O áudio "
            "é segmentado em quadros de 20 ms e transmitido por UDP com sequência, timestamp e "
            "codec; legendas e controle usam WebSocket. O cliente desktop mantém jitter buffer "
            "configurável, reprodução e métricas de perda, atraso e banda.",
        ),
        p(
            "A dupla desenvolveu dois incrementos: resumo ao vivo para entrada tardia e "
            "assinatura Ed25519 de cada legenda. O experimento aplica cinco taxas de perda com "
            "tc netem, compara PCM e Opus em 30 execuções e mede WER, banda e latência.",
        ),
        p(
            "Hipótese: o aumento da perda elevará o WER; Opus reduzirá a banda, enquanto a "
            "qualidade sob perda dependerá da decodificação e do padrão de pacotes descartados.",
            "Callout",
        ),
    ]
    story.append(PageBreak())

    story += [p("1. Arquitetura e núcleo obrigatório", "Section")]
    story += [
        p(
            "O projeto separa tráfego sensível a atraso do tráfego sensível a perda. UDP não "
            "retransmite áudio atrasado; WebSocket preserva a ordem de legendas, resumos e "
            "controles. O servidor envia o mesmo fluxo para múltiplos endpoints registrados.",
        ),
        table(
            [
                ["Fluxo", "Transporte", "Conteúdo", "Propriedade"],
                ["Áudio", "UDP", "PCM/Opus + sequência + timestamp", "Baixa latência; perda observável"],
                ["Texto", "WebSocket/TCP", "Legenda, resumo e assinatura", "Ordenado e confiável"],
                ["Controle", "HTTP/WebSocket", "Iniciar, pausar localmente e parar", "Estado explícito"],
            ],
            [25 * mm, 30 * mm, 67 * mm, 50 * mm],
        ),
        p("Cabeçalho estilo RTP", "Subsection"),
        table(
            [
                ["Campo", "Formato", "Função"],
                ["magic/version", "2 B + uint8", "Identificação e evolução do protocolo"],
                ["codec", "uint8", "PCM=1; Opus=2"],
                ["sequence", "uint32", "Ordenação e detecção de perda"],
                ["timestamp_samples", "uint64", "Sincronização entre áudio e legenda"],
                ["payload_len", "uint16", "Validação do datagrama"],
            ],
            [42 * mm, 38 * mm, 92 * mm],
        ),
        p("Jitter buffer e concorrência", "Subsection"),
        p(
            "O receptor aguarda o prefill configurado, reordena por sequência e avança um "
            "quadro a cada 20 ms. Uma lacuna ocupa silêncio no instante correto, preservando a "
            "linha do tempo. Rede, reprodução e interface executam em workers distintos; ASR e "
            "resumo rodam fora do caminho crítico do UDP.",
        ),
        p("Incrementos da dupla", "Subsection"),
        table(
            [
                ["Trilha", "Implementação", "Demonstração"],
                ["Inteligência", "Resumo incremental com Ollama e fallback extrativo", "Cliente tardio recebe o último resumo"],
                ["Segurança", "Ed25519 sobre sessão, sequência, tempo e texto", "Legenda modificada é rejeitada"],
            ],
            [34 * mm, 82 * mm, 56 * mm],
        ),
    ]
    story.append(PageBreak())

    story += [p("2. Metodologia experimental", "Section")]
    story += [
        p(
            f"Foi usado um áudio de referência em português com {pt(duration)} s, mono, 16 kHz "
            "e 16 bits. Para cada codec foram configuradas perdas de 0%, 1%, 5%, 10% e 20%, "
            "com três repetições por condição. O qdisc netem foi instalado na interface "
            "loopback do WSL2 e removido ao final, inclusive em caso de erro.",
        ),
        table(
            [
                ["Elemento", "Definição"],
                ["Variável independente", "Perda configurada no tc netem e codec PCM/Opus"],
                ["Variáveis controladas", "Mesmo áudio, 20 ms, 16 kHz, jitter de 100 ms e Whisper tiny/int8"],
                ["Repetições", "3 por combinação; 30 execuções totais"],
                ["Métrica principal", "WER da transcrição recebida contra a transcrição do áudio limpo"],
                ["Métricas auxiliares", "Perda observada, banda e orçamento de latência"],
            ],
            [48 * mm, 124 * mm],
        ),
        p("Pipeline de cada execução", "Subsection"),
        p(
            "codificar quadro → empacotar → enviar por UDP → aplicar netem → reordenar no jitter "
            "buffer → substituir lacunas por silêncio → decodificar → reconstruir WAV → "
            "transcrever no cliente → calcular WER e salvar CSV.",
            "Callout",
        ),
        p("Validade da comparação", "Subsection"),
        p(
            "O WAV reconstruído conserva exatamente a duração original, inclusive quando os "
            "primeiros ou últimos pacotes se perdem. A referência principal é a transcrição "
            "Whisper do áudio limpo, isolando o efeito da rede. O WER contra o texto humano "
            f"também foi registrado; no áudio limpo ele foi {pt(clean_gt * 100, 1)}%, mostrando "
            "que erros próprios do modelo não devem ser atribuídos ao transporte.",
        ),
        p("Reprodutibilidade", "Subsection"),
        p(
            "O repositório inclui áudio, texto de referência, runner, CSV incremental, metadados "
            "do ambiente e gerador dos gráficos. A largura de banda inclui cabeçalhos IPv4/UDP. "
            "A latência combina valores medidos e parâmetros declarados; não é apresentada como "
            "uma medição de Internet pública.",
        ),
    ]
    story.append(PageBreak())

    story += [p("3. Resultados: perda e qualidade", "Section")]
    result_table = [["Codec", "Perda cfg.", "Perda obs. média", "WER médio", "Desvio WER"]]
    for codec in ("PCM", "OPUS"):
        for loss in (0, 1, 5, 10, 20):
            subset = groups[(codec, loss)]
            result_table.append(
                [
                    codec,
                    f"{loss}%",
                    f"{pt(mean(subset, 'observed_loss_pct'))}%",
                    f"{pt(mean(subset, 'wer') * 100)}%",
                    f"{pt(std(subset, 'wer') * 100)} p.p.",
                ]
            )
    story += [
        table(result_table, [25 * mm, 30 * mm, 42 * mm, 34 * mm, 41 * mm], font_size=7.3),
        Spacer(1, 5),
        chart_pair("wer_vs_loss.png", "loss_validation.png", height=58 * mm),
        p(
            "A curva observada deve ser interpretada com as barras de desvio: netem descarta "
            "pacotes de modo probabilístico, e cada repetição recebe um padrão distinto. A "
            f"20%, o WER médio foi {pt(mean(pcm_20, 'wer') * 100)}% em PCM e "
            f"{pt(mean(opus_20, 'wer') * 100)}% em Opus. Assim, os dados sustentam a hipótese "
            "de degradação da transcrição conforme a perda aumenta.",
        ),
    ]
    story.append(PageBreak())

    story += [p("4. Resultados: banda e latência", "Section")]
    codec_rows = [["Codec", "Banda média", "Codificação", "ASR computação", "Total até legenda"]]
    for codec in ("PCM", "OPUS"):
        subset = [row for row in rows if row["codec"] == codec]
        codec_rows.append(
            [
                codec,
                f"{pt(mean(subset, 'bandwidth_kbps'), 1)} kbps",
                f"{pt(mean(subset, 'capture_to_send_ms'))} ms",
                f"{pt(mean(subset, 'transcription_ms'))} ms",
                f"{pt(mean(subset, 'total_ms'))} ms",
            ]
        )
    story += [
        chart_pair("bandwidth_comparison.png", "latency_budget.png", height=59 * mm),
        Spacer(1, 5),
        table(codec_rows, [27 * mm, 38 * mm, 36 * mm, 36 * mm, 35 * mm]),
        p("Orçamento de latência", "Subsection"),
        p(
            "O orçamento soma: formação do quadro e codificação; trânsito UDP; 100 ms de jitter "
            "buffer; decodificação; 1 s para acumular uma janela de ASR; processamento Whisper; "
            "retorno textual pelo enlace, usado como proxy local; e 16,67 ms para atualização em "
            "uma tela de 60 Hz. Os componentes configurados aparecem separados dos medidos no CSV.",
        ),
        p(
            "PCM mantém aproximadamente 256 kbps de payload antes dos cabeçalhos. Opus reduz "
            "fortemente a banda porque explora redundância temporal, ao custo de codificação e "
            "dependência entre quadros. A janela de fala domina a latência; otimizar apenas a rede "
            "não elimina esse atraso.",
            "Callout",
        ),
    ]
    story.append(PageBreak())

    story += [p("5. Pergunta-desafio e conclusão", "Section")]
    story += [
        p("Onde a transcrição deve rodar?", "Subsection"),
        p(
            "Os dados favorecem a transcrição no servidor para o serviço principal. No servidor, "
            "o Whisper recebe áudio limpo uma única vez e distribui texto leve a todos os clientes. "
            "No cliente, o WER cresce com as perdas medidas e cada ouvinte consome CPU e memória "
            "para executar o modelo. Quanto maior o número de ouvintes, maior a vantagem de "
            "centralizar o ASR.",
        ),
        table(
            [
                ["Critério", "Servidor - áudio limpo", "Cliente - áudio recebido"],
                ["Qualidade", "Independente da perda após o servidor", "Varia com perda, jitter e codec"],
                ["Latência", "ASR único + WebSocket", "Jitter + ASR em cada máquina"],
                ["Banda", "Áudio + texto pequeno", "Somente áudio, mas sem economia relevante de rede"],
                ["Privacidade", "Áudio é processado centralmente", "Pode manter processamento no dispositivo"],
                ["Escala", "Modelo compartilhado; servidor dimensionável", "Custo replicado em todos os clientes"],
            ],
            [29 * mm, 71 * mm, 72 * mm],
            font_size=7.4,
        ),
        p(
            "Recomendação: transcrever no servidor e enviar legendas assinadas por WebSocket. A "
            "transcrição no cliente permanece útil quando privacidade local é requisito superior "
            "à qualidade uniforme ou quando o servidor não deve receber áudio em claro.",
            "Callout",
        ),
        p("Limitações", "Subsection"),
        p(
            "O experimento usa loopback WSL2 e um único áudio sintético; os resultados não "
            "representam todos os sotaques ou enlaces. A chave Ed25519 chega pelo próprio "
            "WebSocket, assumido autêntico; TLS ou pinagem seriam necessários contra substituição "
            "ativa da chave. O orçamento de tela é um limite de agendamento, não instrumentação "
            "do hardware gráfico.",
        ),
        p("Conclusão", "Subsection"),
        p(
            "O núcleo demonstra a diferença entre UDP e transporte confiável, o papel do jitter "
            "buffer e o efeito mensurável da perda. Os incrementos de Inteligência e Segurança "
            "operam fora do caminho crítico. As 30 execuções, com repetição e gráficos, permitem "
            "responder a pergunta conceitual usando evidências do próprio sistema.",
        ),
        p("Referências", "Subsection"),
        p(
            "[1] MARTINELLO, M. Projetos de Redes de Computadores - Propostas de Trabalho, 2026. "
            "[2] KUROSE, J. F.; ROSS, K. W. Redes de computadores e a Internet: uma abordagem "
            "top-down. Pearson, 2013. [3] Código, dados e scripts reproduzíveis do repositório da dupla.",
            "Small",
        ),
    ]
    return story


def main() -> None:
    rows = load_rows()
    if len(rows) != 30:
        raise RuntimeError(f"expected 30 experiment rows, found {len(rows)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Relatório final - Projeto 2 de Redes",
        author="Lucas D'Amato Nitz e Victor Dutra",
        subject="Áudio ao vivo com transcrição, resumo incremental e integridade",
    )
    document.build(build_story(rows), onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()

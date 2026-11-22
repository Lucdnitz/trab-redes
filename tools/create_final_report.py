"""Gera o relatório final do Projeto 2 em formato acadêmico simples."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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

BLACK = colors.HexColor("#111111")
DARK_GRAY = colors.HexColor("#333333")
MID_GRAY = colors.HexColor("#777777")
LIGHT_GRAY = colors.HexColor("#E6E6E6")
ROW_GRAY = colors.HexColor("#F4F4F4")
ACCENT = colors.HexColor("#1F4E79")
LIGHT_ACCENT = colors.HexColor("#EAF2F8")


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
            "CoverInstitution",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=ACCENT,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=24,
            alignment=TA_CENTER,
            textColor=ACCENT,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverInfo",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=BLACK,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=ACCENT,
            spaceBefore=6,
            spaceAfter=6,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=ACCENT,
            spaceBefore=5,
            spaceAfter=3,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.2,
            alignment=TA_JUSTIFY,
            textColor=BLACK,
            spaceAfter=6,
            allowWidows=0,
            allowOrphans=0,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=BLACK,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            "Caption",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=DARK_GRAY,
            spaceBefore=2,
            spaceAfter=6,
        )
    )
    return styles


STYLES = build_styles()


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def make_table(data, widths, *, font_size: float = 8) -> Table:
    normalized = []
    for row_index, row in enumerate(data):
        style = STYLES["TableHeader"] if row_index == 0 else STYLES["Small"]
        normalized.append([Paragraph(str(cell), style) for cell in row])

    result = Table(normalized, colWidths=widths, repeatRows=1, hAlign="LEFT")
    rules = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, MID_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    for row in range(1, len(data)):
        if row % 2 == 0:
            rules.append(("BACKGROUND", (0, row), (-1, row), LIGHT_ACCENT))
    result.setStyle(TableStyle(rules))
    return result


def chart_image(filename: str, *, width: float = 154 * mm, max_height: float = 58 * mm) -> Image:
    source = RESULTS / filename
    if not source.exists():
        raise FileNotFoundError(source)

    chart = Image(str(source), hAlign="CENTER")
    height = width * chart.imageHeight / chart.imageWidth
    if height > max_height:
        height = max_height
        width = height * chart.imageWidth / chart.imageHeight
    chart.drawWidth = width
    chart.drawHeight = height
    return chart


def grouped(rows: list[dict[str, str]]) -> dict[tuple[str, int], list[dict[str, str]]]:
    groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["codec"], int(row["loss_pct"]))].append(row)
    return groups


def first_page(canvas, _doc) -> None:
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(DARK_GRAY)
    canvas.setLineWidth(0.7)
    canvas.line(28 * mm, 18 * mm, width - 28 * mm, 18 * mm)
    canvas.restoreState()


def later_pages(canvas, doc) -> None:
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20 * mm, 9.5 * mm, "Redes de Computadores, Projeto 2")
    canvas.drawRightString(width - 20 * mm, 9.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def build_story(rows: list[dict[str, str]]) -> list:
    groups = grouped(rows)
    duration = number(rows[0], "duration_s")
    pcm_rows = [row for row in rows if row["codec"] == "PCM"]
    opus_rows = [row for row in rows if row["codec"] == "OPUS"]
    bandwidth_reduction = 100 * (
        1 - mean(opus_rows, "bandwidth_kbps") / mean(pcm_rows, "bandwidth_kbps")
    )

    story = [Spacer(1, 30 * mm)]
    story += [
        p("UNIVERSIDADE FEDERAL DO ESPÍRITO SANTO", "CoverInstitution"),
        p("Centro Tecnológico, Departamento de Informática", "CoverInstitution"),
        p("Disciplina de Redes de Computadores", "CoverInstitution"),
        Spacer(1, 30 * mm),
        p("RELATÓRIO FINAL DO PROJETO 2", "CoverTitle"),
        p(
            "Áudio ao vivo com transcrição,<br/>resumo incremental e integridade de legendas",
            "CoverTitle",
        ),
        Spacer(1, 24 * mm),
        p("Lucas D'Amato Nitz<br/>Victor Dutra", "CoverInfo"),
        Spacer(1, 14 * mm),
        p("Professor: Magnos Martinello", "CoverInfo"),
        Spacer(1, 34 * mm),
        p("Vitória, ES<br/>2026", "CoverInfo"),
    ]
    story.append(PageBreak())

    story += [p("1. Introdução", "Section")]
    story += [
        p(
            "O projeto consiste em um sistema de comunicação entre cliente e servidor para transmissão de áudio ao vivo. "
            "O servidor envia o áudio por UDP para um ou mais clientes, enquanto legendas, resumo e "
            "mensagens de controle são enviados por WebSocket. A proposta permite observar, na prática, "
            "como perda de pacotes, atraso e escolha de codec afetam uma aplicação de tempo real."
        ),
        p(
            "A implementação foi feita em Python. O servidor usa FastAPI e o cliente possui interface "
            "desktop em PySide6. Foram implementados os codecs PCM e Opus, um jitter buffer para "
            "reordenar pacotes e uma transcrição feita no servidor. Como incrementos, o sistema também "
            "gera um resumo durante a transmissão e assina as legendas com Ed25519."
        ),
        p("1.1 Objetivos", "Subsection"),
        p(
            "O objetivo principal foi desenvolver uma solução funcional que reunisse conceitos de "
            "redes e programação concorrente. Além de transmitir o áudio, queríamos medir o que acontece "
            "quando a rede perde pacotes e comparar o custo de banda dos dois codecs."
        ),
        make_table(
            [
                ["Item", "O que foi implementado"],
                ["Transporte", "Áudio por UDP, controle, legendas e resumo por WebSocket"],
                ["Clientes", "Vários ouvintes simultâneos, cada um com sua porta UDP"],
                ["Áudio", "PCM e Opus em quadros de 20 ms"],
                ["Transcrição", "Whisper executado no servidor"],
                ["Incrementos", "Resumo incremental e assinatura Ed25519"],
            ],
            [37 * mm, 136 * mm],
        ),
        p("Tabela 1: Visão geral dos recursos entregues.", "Caption"),
        p("2. Arquitetura da solução", "Section"),
        p(
            "O fluxo de áudio e o fluxo de texto foram separados porque possuem necessidades diferentes. "
            "Para o áudio, uma retransmissão pode chegar tarde demais e causar mais atraso. Por isso foi "
            "usado UDP. Já as legendas e os comandos precisam chegar em ordem, o que justifica o uso do "
            "WebSocket sobre TCP."
        ),
        make_table(
            [
                ["Canal", "Conteúdo", "Motivo da escolha"],
                ["UDP", "Quadros PCM ou Opus", "Baixa latência e perda observável"],
                ["WebSocket", "Legendas, resumo, chave e eventos", "Entrega ordenada e confiável"],
                ["HTTP", "Início, parada, sessão e upload", "Operações simples do servidor"],
            ],
            [30 * mm, 65 * mm, 78 * mm],
        ),
        p("Tabela 2: Canais usados pela aplicação.", "Caption"),
    ]
    story.append(PageBreak())

    story += [p("3. Principais escolhas de implementação", "Section")]
    story += [
        p("3.1 Pacotes e jitter buffer", "Subsection"),
        p(
            "Cada datagrama de áudio possui identificação do protocolo, versão, codec, número de "
            "sequência, timestamp em amostras e tamanho do payload. O formato foi inspirado no RTP, "
            "mas reduzido ao necessário para o trabalho. O número de sequência permite detectar perda, "
            "duplicação e chegada fora de ordem."
        ),
        p(
            "No cliente, o jitter buffer espera uma pequena quantidade inicial de pacotes antes de "
            "começar a reprodução. Depois disso, libera um quadro a cada 20 ms. Quando um pacote não "
            "chega a tempo, o cliente insere silêncio naquele trecho e mantém a linha temporal."
        ),
        p("3.2 Concorrência", "Subsection"),
        p(
            "A interface, a recepção da rede e a reprodução não executam na mesma tarefa. O cliente usa "
            "workers separados para evitar que a janela congele enquanto recebe ou toca áudio. No "
            "servidor, transmissão, transcrição e resumo também são separados. Assim, uma chamada lenta "
            "ao modelo de resumo não interrompe o envio UDP."
        ),
        p("3.3 Transcrição, resumo e integridade", "Subsection"),
        p(
            "O Whisper recebe o áudio limpo no servidor e envia as legendas aos clientes. O resumo usa "
            "Ollama quando o serviço está disponível. Caso contrário, o servidor usa um resumo extrativo "
            "local, o que permite demonstrar o projeto mesmo sem o modelo instalado."
        ),
        p(
            "As legendas finalizadas são assinadas com Ed25519. O cliente verifica a assinatura antes "
            "de exibir o texto e sinaliza alterações. Há um comando de demonstração que modifica uma "
            "legenda para comprovar que a verificação está funcionando."
        ),
        p("3.4 Organização do código", "Subsection"),
        make_table(
            [
                ["Pasta", "Responsabilidade"],
                ["shared", "Protocolo, codecs, carregamento de áudio e assinatura"],
                ["core", "Jitter buffer e métricas"],
                ["server", "APIs, registro de clientes, transmissão, Whisper e resumo"],
                ["client", "Rede, reprodução e interface PySide6"],
                ["experiments", "Matriz de testes, CSV e geração dos gráficos"],
            ],
            [38 * mm, 135 * mm],
        ),
        p("Tabela 3: Divisão dos módulos do projeto.", "Caption"),
        p("3.5 Tratamento de erros e testes", "Subsection"),
        p(
            "O código valida cabeçalhos e tamanhos de payload, descarta duplicatas, registra pacotes "
            "atrasados e encerra os workers de forma controlada. O experimento remove a regra do netem "
            "mesmo se ocorrer erro. O projeto possui 25 testes automatizados e verificação com Ruff. "
            "Também foram adicionados scripts equivalentes para Windows e Linux."
        ),
    ]
    story.append(PageBreak())

    story += [p("4. Experimento", "Section")]
    story += [
        p(
            f"Foi usado um áudio de referência em português com {pt(duration)} segundos, mono e 16 kHz. "
            "O mesmo áudio foi transmitido em PCM e Opus com perdas configuradas de 0%, 1%, 5%, 10% e "
            "20%. Cada combinação foi repetida três vezes, totalizando 30 execuções."
        ),
        p(
            "A perda foi aplicada com tc netem na interface de loopback do WSL2. Depois de cada execução, "
            "o áudio recebido foi reconstruído e transcrito. A comparação principal usa o WER, que mede "
            "substituições, exclusões e inserções de palavras em relação à transcrição do áudio sem perda."
        ),
        make_table(
            [
                ["Configuração", "Valor"],
                ["Codecs", "PCM e Opus"],
                ["Perda configurada", "0%, 1%, 5%, 10% e 20%"],
                ["Repetições", "3 por condição"],
                ["Total", "30 execuções"],
                ["Quadro de áudio", "20 ms"],
                ["Jitter buffer", "100 ms"],
                ["Métricas", "WER, perda observada, banda e latência"],
            ],
            [54 * mm, 119 * mm],
        ),
        p("Tabela 4: Configuração do experimento.", "Caption"),
        p("4.1 Resultados numéricos", "Subsection"),
    ]
    result_table = [["Codec", "Perda", "Perda observada", "WER médio", "Desvio do WER"]]
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
        make_table(result_table, [25 * mm, 25 * mm, 42 * mm, 39 * mm, 42 * mm], font_size=7.5),
        p("Tabela 5: Médias das três repetições de cada condição.", "Caption"),
        p(
            "A perda observada ficou próxima do valor configurado. As pequenas diferenças são esperadas, "
            "pois o netem descarta pacotes de forma probabilística. Sem perda, a transcrição reconstruída "
            "foi igual à referência limpa."
        ),
    ]
    story.append(PageBreak())

    story += [p("5. Análise dos resultados", "Section")]
    story += [
        chart_image("wer_vs_loss.png", max_height=61 * mm),
        p("Figura 1: Taxa de erro de palavras em função da perda de pacotes.", "Caption"),
        p(
            "O WER aumentou à medida que a perda cresceu. Em 20% de perda, o valor médio foi de "
            f"{pt(mean(groups[('PCM', 20)], 'wer') * 100)}% para PCM e "
            f"{pt(mean(groups[('OPUS', 20)], 'wer') * 100)}% para Opus. Isso mostra que a perda de "
            "quadros prejudica a transcrição, mesmo quando a reprodução mantém a duração correta."
        ),
        chart_image("loss_validation.png", max_height=61 * mm),
        p("Figura 2: Comparação entre a perda configurada e a perda observada.", "Caption"),
        p(
            "O gráfico também confirma que o ambiente de teste aplicou as perdas esperadas. Como foram "
            "feitas somente três repetições por condição e usado um único áudio, os valores servem para "
            "avaliar este sistema, não para estabelecer uma comparação geral entre todos os codecs."
        ),
    ]
    story.append(PageBreak())

    story += [p("5.1 Banda e latência", "Section")]
    story += [
        chart_image("bandwidth_comparison.png", max_height=50 * mm),
        p("Figura 3: Consumo médio de banda dos codecs.", "Caption"),
        p(
            f"PCM consumiu em média {pt(mean(pcm_rows, 'bandwidth_kbps'), 1)} kbps, enquanto Opus "
            f"consumiu {pt(mean(opus_rows, 'bandwidth_kbps'), 1)} kbps. A redução foi de "
            f"{pt(bandwidth_reduction, 1)}%, o que torna o Opus mais adequado quando a banda é limitada."
        ),
        chart_image("latency_budget.png", max_height=50 * mm),
        p("Figura 4: Componentes do orçamento de latência.", "Caption"),
        p(
            "A maior parte da latência vem da janela acumulada para transcrição e do processamento do "
            "Whisper. O transporte UDP e a codificação representam uma parcela menor. Portanto, reduzir "
            "apenas o atraso da rede não seria suficiente para tornar a legenda imediata."
        ),
        p("6. Conclusão", "Section"),
        p(
            "Para este projeto, a melhor escolha é executar a transcrição no servidor. O servidor recebe "
            "o áudio antes das perdas que afetam cada cliente e executa o Whisper uma única vez. Se a "
            "transcrição fosse feita nos clientes, cada máquina teria um resultado diferente e repetiria "
            "o mesmo custo de processamento."
        ),
        p(
            "O trabalho permitiu aplicar UDP, TCP/WebSocket, concorrência, codecs, jitter buffer e "
            "medições de rede em uma solução completa. Os testes mostraram o aumento do WER com a perda "
            "e a economia de banda obtida com Opus. Como melhorias futuras, seria interessante testar "
            "mais vozes, redes reais, perdas em rajada e medir a latência ponta a ponta com instrumentação."
        ),
        p("Código fonte", "Subsection"),
        p(
            "O código do servidor, do cliente, os testes e os dados do experimento estão disponíveis "
            "no <link href='https://github.com/Lucdnitz/trab-redes' color='#1F4E79'>"
            "<u>repositório do projeto no GitHub</u></link>."
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
        bottomMargin=19 * mm,
        title="Relatório Final do Projeto 2 de Redes",
        author="Lucas D'Amato Nitz e Victor Dutra",
        subject="Áudio ao vivo com transcrição, resumo e integridade de legendas",
    )
    document.build(build_story(rows), onFirstPage=first_page, onLaterPages=later_pages)
    print(OUTPUT)


if __name__ == "__main__":
    main()

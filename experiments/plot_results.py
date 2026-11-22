"""Gera os gráficos do experimento obrigatório a partir de `results.csv`."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "experiments" / "results" / "results.csv"


def plot_all(csv_path: Path, out_dir: Path) -> None:
    df = pd.read_csv(csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    # 1. WER médio x perda com barras de desvio padrão (PCM vs Opus)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for codec, color, marker in (("PCM", "#0E7C86", "o"), ("OPUS", "#D97706", "s")):
        sub = df[df["codec"] == codec]
        grouped = sub.groupby("loss_pct")["wer"].agg(["mean", "std"]).reset_index()
        ax.errorbar(
            grouped["loss_pct"],
            grouped["mean"] * 100.0,
            yerr=grouped["std"].fillna(0.0) * 100.0,
            marker=marker,
            linewidth=2,
            capsize=4,
            label=codec,
            color=color,
        )
    ax.set_title("Taxa de erro de palavras (WER) sob perda de pacotes")
    ax.set_xlabel("Perda configurada no tc netem (%)")
    ax.set_ylabel("WER (%)")
    ax.set_xticks(sorted(df["loss_pct"].unique()))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "wer_vs_loss.png", dpi=180)
    plt.close(fig)

    # 2. Banda média PCM x Opus (incluindo cabeçalhos)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    bw = df.groupby("codec")["bandwidth_kbps"].agg(["mean", "std"]).reindex(["PCM", "OPUS"])
    bars = ax.bar(
        bw.index,
        bw["mean"],
        yerr=bw["std"].fillna(0.0),
        capsize=5,
        color=["#0E7C86", "#D97706"],
        width=0.5,
    )
    for bar, val in zip(bars, bw["mean"], strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 4,
            f"{val:.1f} kbps",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    ax.set_title("Consumo médio de banda na rede (com cabeçalhos)")
    ax.set_ylabel("Vazão recebida (kbps)")
    ax.set_ylim(0, max(bw["mean"]) * 1.18)
    fig.tight_layout()
    fig.savefig(out_dir / "bandwidth_comparison.png", dpi=180)
    plt.close(fig)

    # 3. Perda configurada x perda observada (validação do tc netem)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    obs = df.groupby("loss_pct")["observed_loss_pct"].agg(["mean", "std"]).reset_index()
    ax.plot(obs["loss_pct"], obs["loss_pct"], "--", color="#64748B", label="Ideal (configurada)")
    ax.errorbar(
        obs["loss_pct"],
        obs["mean"],
        yerr=obs["std"].fillna(0.0),
        marker="o",
        linewidth=2,
        capsize=4,
        color="#1D4ED8",
        label="Observada no cliente",
    )
    ax.set_title("Validação do ambiente: perda configurada vs. observada")
    ax.set_xlabel("Perda configurada (%)")
    ax.set_ylabel("Perda observada (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "loss_validation.png", dpi=180)
    plt.close(fig)

    # 4. Orçamento de latência (PCM vs Opus)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    lat = df.groupby("codec")[
        ["capture_to_send_ms", "network_ms", "buffer_ms", "transcription_ms"]
    ].mean().reindex(["PCM", "OPUS"])
    components = [
        ("capture_to_send_ms", "Captura + codificação", "#0E7C86"),
        ("network_ms", "Rede UDP", "#3B82F6"),
        ("buffer_ms", "Jitter buffer", "#F59E0B"),
        ("transcription_ms", "Processamento ASR (janela 4s)", "#EF4444"),
    ]
    bottom = pd.Series([0.0, 0.0], index=lat.index)
    for col, label, color in components:
        ax.bar(lat.index, lat[col], bottom=bottom, label=label, color=color, width=0.45)
        bottom = bottom + lat[col]
    for idx, total in enumerate(bottom):
        ax.text(idx, total + 8, f"{total:.1f} ms", ha="center", fontweight="bold")
    ax.set_title("Orçamento de latência de processamento até a legenda")
    ax.set_ylabel("Latência (ms)")
    ax.set_ylim(0, max(bottom) * 1.18)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_dir / "latency_budget.png", dpi=180)
    plt.close(fig)

    print(f"Gráficos salvos em: {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plota gráficos do experimento.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_CSV.parent)
    args = parser.parse_args()
    plot_all(args.csv, args.out_dir)


if __name__ == "__main__":
    main()

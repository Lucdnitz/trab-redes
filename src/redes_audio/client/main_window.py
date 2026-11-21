"""Janela principal do cliente desktop."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from redes_audio.client.network_worker import NetworkWorker
from redes_audio.client.playback_worker import PlaybackWorker
from redes_audio.core.jitter_buffer import JitterBuffer


class MainWindow(QMainWindow):
    def __init__(self, server_host: str, udp_port: int) -> None:
        super().__init__()
        self.setWindowTitle("Projeto 2 - Áudio ao vivo")
        self.resize(900, 560)

        self.network_worker: NetworkWorker | None = None
        self.playback_worker: PlaybackWorker | None = None
        self.buffer: JitterBuffer | None = None
        self._paused = False

        self.server_input = QLineEdit(server_host)
        self.udp_port_input = QSpinBox()
        self.udp_port_input.setRange(1_024, 65_535)
        self.udp_port_input.setValue(udp_port)
        self.jitter_input = QSpinBox()
        self.jitter_input.setRange(20, 1_000)
        self.jitter_input.setSingleStep(20)
        self.jitter_input.setValue(100)

        self.status_label = QLabel("Desconectado")
        self.status_label.setStyleSheet("font-weight: 700; color: #b42318;")
        self.transcript_label = QLabel("Aguardando legenda...")
        self.transcript_label.setWordWrap(True)
        self.transcript_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.fact_label = QLabel("Checagem ainda não disponível")
        self.fact_label.setWordWrap(True)

        self.metric_labels = {
            name: QLabel("0")
            for name in ("received", "played", "lost", "late", "duplicates", "depth")
        }

        self.connect_button = QPushButton("Conectar")
        self.pause_button = QPushButton("Pausar")
        self.stop_button = QPushButton("Parar")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.connect_button.clicked.connect(self.connect_client)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop_client)

        self.setCentralWidget(self._build_layout())

    def _build_layout(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)

        connection_group = QGroupBox("Conexão")
        connection_form = QFormLayout(connection_group)
        connection_form.addRow("Servidor", self.server_input)
        connection_form.addRow("Porta UDP", self.udp_port_input)
        connection_form.addRow("Jitter buffer (ms)", self.jitter_input)
        connection_form.addRow("Estado", self.status_label)

        content_layout = QHBoxLayout()
        transcript_group = QGroupBox("Legenda e checagem")
        transcript_layout = QVBoxLayout(transcript_group)
        transcript_layout.addWidget(self.transcript_label, 2)
        transcript_layout.addWidget(self.fact_label, 1)

        metrics_group = QGroupBox("Métricas")
        metrics_layout = QGridLayout(metrics_group)
        labels = {
            "received": "Recebidos",
            "played": "Reproduzidos",
            "lost": "Perdidos",
            "late": "Atrasados",
            "duplicates": "Duplicados",
            "depth": "Buffer",
        }
        for row, (key, title) in enumerate(labels.items()):
            metrics_layout.addWidget(QLabel(title), row, 0)
            metrics_layout.addWidget(self.metric_labels[key], row, 1)

        content_layout.addWidget(transcript_group, 2)
        content_layout.addWidget(metrics_group, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()

        layout.addWidget(connection_group)
        layout.addLayout(content_layout, 1)
        layout.addLayout(buttons)
        return root

    def connect_client(self) -> None:
        if self.network_worker and self.network_worker.isRunning():
            return

        prefill = max(1, self.jitter_input.value() // 20)
        self.buffer = JitterBuffer(prefill_frames=prefill, max_frames=max(50, prefill * 5))
        self.network_worker = NetworkWorker(
            self.server_input.text().strip(),
            self.udp_port_input.value(),
            self.buffer,
        )
        self.playback_worker = PlaybackWorker(self.buffer)

        self.network_worker.connected.connect(self._on_connected)
        self.network_worker.event_received.connect(self._on_event)
        self.network_worker.metrics_changed.connect(self._update_metrics)
        self.network_worker.error.connect(self._show_error)
        self.playback_worker.error.connect(self._show_error)

        self.status_label.setText("Conectando...")
        self.network_worker.start()
        self.playback_worker.start()

    def _on_connected(self, event: dict) -> None:
        self.status_label.setText(f"Conectado: {event.get('client_id', '')[:8]}")
        self.status_label.setStyleSheet("font-weight: 700; color: #067647;")
        self.connect_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def _on_event(self, event: dict) -> None:
        if event.get("type") == "transcript":
            self.transcript_label.setText(str(event.get("text", "")))
        elif event.get("type") == "fact":
            self.fact_label.setText(str(event.get("label", "")))

    def _update_metrics(self, metrics: dict) -> None:
        for key, label in self.metric_labels.items():
            label.setText(str(metrics.get(key, 0)))

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Erro: {message}")
        self.status_label.setStyleSheet("font-weight: 700; color: #b42318;")

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if self.playback_worker:
            self.playback_worker.set_paused(self._paused)
        self.pause_button.setText("Continuar" if self._paused else "Pausar")

    def stop_client(self) -> None:
        if self.network_worker:
            self.network_worker.stop()
            self.network_worker.wait(1_000)
        if self.playback_worker:
            self.playback_worker.stop()
            self.playback_worker.wait(1_000)

        self.status_label.setText("Desconectado")
        self.status_label.setStyleSheet("font-weight: 700; color: #b42318;")
        self.connect_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self._paused = False
        self.pause_button.setText("Pausar")

    def closeEvent(self, event) -> None:
        self.stop_client()
        super().closeEvent(event)

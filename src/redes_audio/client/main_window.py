"""Janela principal do cliente desktop."""

from __future__ import annotations

import threading
from pathlib import Path

import httpx
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from redes_audio.client.network_worker import NetworkWorker
from redes_audio.client.playback_worker import PlaybackWorker
from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.shared.signing import TranscriptVerifier


class MainWindow(QMainWindow):
    _control_feedback = Signal(str)

    def __init__(self, server_host: str, server_port: int, udp_port: int) -> None:
        super().__init__()
        self.setWindowTitle("Projeto 2 - Áudio ao vivo")
        self.resize(980, 660)

        self.network_worker: NetworkWorker | None = None
        self.playback_worker: PlaybackWorker | None = None
        self.buffer: JitterBuffer | None = None
        self.verifier: TranscriptVerifier | None = None
        self._paused = False
        self._sample_rate = 16_000
        self._current_samples = 0
        self._active_codec = "-"
        self._verified_count = 0
        self._rejected_count = 0
        self._pending_captions: list[dict] = []

        self.server_input = QLineEdit(server_host)
        self.server_port_input = QSpinBox()
        self.server_port_input.setRange(1, 65_535)
        self.server_port_input.setValue(server_port)
        self.udp_port_input = QSpinBox()
        self.udp_port_input.setRange(1_024, 65_535)
        self.udp_port_input.setValue(udp_port)
        self.jitter_input = QSpinBox()
        self.jitter_input.setRange(20, 1_000)
        self.jitter_input.setSingleStep(20)
        self.jitter_input.setValue(100)

        self.status_label = QLabel("Desconectado")
        self.status_label.setStyleSheet("font-weight: 700; color: #b42318;")

        self.integrity_label = QLabel(
            "Ed25519: aguardando chave pública | Verificadas: 0 | Rejeitadas: 0"
        )
        self.integrity_label.setStyleSheet("color: #475467;")

        self.transcript_box = QTextEdit()
        self.transcript_box.setReadOnly(True)
        self.transcript_box.setPlaceholderText("As legendas sincronizadas aparecerão aqui...")

        self.live_caption_label = QLabel("Ao vivo: aguardando fala...")
        self.live_caption_label.setWordWrap(True)
        self.live_caption_label.setStyleSheet(
            "padding: 6px; background: #F2F4F7; border-radius: 4px; color: #1D2939;"
        )

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setPlaceholderText(
            "Resumo incremental para quem entra no meio da transmissão..."
        )
        self.summary_meta_label = QLabel("Resumo: aguardando conteúdo suficiente")
        self.summary_meta_label.setStyleSheet("color: #475467;")

        self.metric_labels = {
            name: QLabel("0")
            for name in (
                "received",
                "played",
                "lost",
                "late",
                "duplicates",
                "depth",
                "bytes_kb",
                "codec",
            )
        }
        self.metric_labels["codec"].setText("-")

        self.connect_button = QPushButton("Conectar")
        self.pause_button = QPushButton("Pausar")
        self.stop_button = QPushButton("Parar")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.start_pcm_button = QPushButton("Iniciar Aula (PCM)")
        self.start_opus_button = QPushButton("Iniciar Aula (Opus)")
        self.upload_codec_combo = QComboBox()
        self.upload_codec_combo.addItems(["OPUS", "PCM"])
        self.choose_audio_button = QPushButton("Enviar Outro Áudio...")
        self.stop_stream_button = QPushButton("Parar Servidor")
        self.tamper_button = QPushButton("Simular Adulteração")

        self.connect_button.clicked.connect(self.connect_client)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop_client)
        self.start_pcm_button.clicked.connect(
            lambda: self._call_server("/api/v1/stream/start", {"codec": "pcm"})
        )
        self.start_opus_button.clicked.connect(
            lambda: self._call_server("/api/v1/stream/start", {"codec": "opus"})
        )
        self.choose_audio_button.clicked.connect(self._choose_and_upload_audio)
        self.stop_stream_button.clicked.connect(
            lambda: self._call_server("/api/v1/stream/stop", None)
        )
        self.tamper_button.clicked.connect(
            lambda: self._call_server("/api/v1/demo/tamper", None)
        )
        self._control_feedback.connect(self._on_control_feedback)

        self.setCentralWidget(self._build_layout())

    def _build_layout(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)

        connection_group = QGroupBox("Conexão")
        connection_form = QFormLayout(connection_group)
        connection_form.addRow("Servidor", self.server_input)
        connection_form.addRow("Porta HTTP/WS", self.server_port_input)
        connection_form.addRow("Porta UDP", self.udp_port_input)
        connection_form.addRow("Jitter buffer (ms)", self.jitter_input)
        connection_form.addRow("Estado", self.status_label)

        content_layout = QHBoxLayout()
        transcript_group = QGroupBox("Legenda sincronizada e resumo ao vivo")
        transcript_layout = QVBoxLayout(transcript_group)
        transcript_layout.addWidget(self.integrity_label)
        transcript_layout.addWidget(self.transcript_box, 3)
        transcript_layout.addWidget(self.live_caption_label)
        transcript_layout.addWidget(self.summary_meta_label)
        transcript_layout.addWidget(self.summary_box, 2)

        metrics_group = QGroupBox("Métricas de rede")
        metrics_layout = QGridLayout(metrics_group)
        labels = {
            "codec": "Codec",
            "received": "Recebidos",
            "played": "Reproduzidos",
            "lost": "Perdidos",
            "late": "Atrasados",
            "duplicates": "Duplicados",
            "depth": "Buffer (quadros)",
            "bytes_kb": "Recebido (KB)",
        }
        for row, (key, title) in enumerate(labels.items()):
            label_widget = QLabel(title)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
            metrics_layout.addWidget(label_widget, row, 0)
            metrics_layout.addWidget(self.metric_labels[key], row, 1)
        metrics_layout.setRowStretch(len(labels), 1)

        content_layout.addWidget(transcript_group, 3)
        content_layout.addWidget(metrics_group, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()

        demo_group = QGroupBox("Controles da transmissão (servidor)")
        demo_layout = QHBoxLayout(demo_group)
        demo_layout.addWidget(self.start_pcm_button)
        demo_layout.addWidget(self.start_opus_button)
        demo_layout.addWidget(self.upload_codec_combo)
        demo_layout.addWidget(self.choose_audio_button)
        demo_layout.addWidget(self.stop_stream_button)
        demo_layout.addWidget(self.tamper_button)
        demo_layout.addStretch()

        layout.addWidget(connection_group)
        layout.addLayout(content_layout, 1)
        layout.addLayout(buttons)
        layout.addWidget(demo_group)
        return root

    def connect_client(self) -> None:
        if self.network_worker and self.network_worker.isRunning():
            return

        prefill = max(1, self.jitter_input.value() // 20)
        self.buffer = JitterBuffer(prefill_frames=prefill, max_frames=max(50, prefill * 5))
        self.network_worker = NetworkWorker(
            self.server_input.text().strip(),
            self.server_port_input.value(),
            self.udp_port_input.value(),
            self.buffer,
        )
        self.playback_worker = PlaybackWorker(self.buffer)

        self.network_worker.connected.connect(self._on_connected)
        self.network_worker.event_received.connect(self._on_event)
        self.network_worker.metrics_changed.connect(self._update_metrics)
        self.network_worker.error.connect(self._show_error)
        self.playback_worker.error.connect(self._show_error)
        self.playback_worker.position_changed.connect(self._on_playback_position)

        self._verified_count = 0
        self._rejected_count = 0
        self._current_samples = 0
        self._pending_captions.clear()
        self.transcript_box.clear()
        self.summary_box.clear()

        self.status_label.setText("Conectando...")
        self.network_worker.start()
        self.playback_worker.start()

    def _on_connected(self, event: dict) -> None:
        self.status_label.setText(f"Conectado: {event.get('client_id', '')[:8]}")
        self.status_label.setStyleSheet("font-weight: 700; color: #067647;")
        self._sample_rate = int(event.get("sample_rate", 16_000))
        public_key = event.get("public_key")
        if public_key:
            self.verifier = TranscriptVerifier(str(public_key))
            self._refresh_integrity_label()

        summary = event.get("summary", {})
        if summary.get("text"):
            self.summary_box.setPlainText(str(summary["text"]))
            through_s = int(summary.get("through_ms", 0)) / 1000
            self.summary_meta_label.setText(
                f"Resumo recebido na entrada (cobre até {through_s:.1f}s)"
            )
        self.connect_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def _on_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "stream_started":
            self._current_samples = 0
            self._pending_captions.clear()
            self.transcript_box.clear()
            self.live_caption_label.setText("Ao vivo: aguardando fala...")
            self.summary_box.clear()
            self.summary_meta_label.setText("Resumo: aguardando conteúdo suficiente")
            self._active_codec = str(event.get("codec", "-"))
            self.metric_labels["codec"].setText(self._active_codec)
            if self.buffer is not None:
                self.buffer.reset()
            if self.playback_worker is not None:
                self.playback_worker.reset_stream()
            if event.get("public_key"):
                self.verifier = TranscriptVerifier(str(event["public_key"]))
            self._refresh_integrity_label()
            return

        if event_type == "stream_ended":
            # Libera eventuais legendas finais cuja janela ainda estava na fila.
            self._flush_pending_captions(force=True)
            if self.buffer is not None:
                self.buffer.rearm()
            self.live_caption_label.setText("Ao vivo: transmissão encerrada.")
            return

        if event_type == "transcript_partial":
            partial = str(event.get("text", "")).strip()
            start_s = int(event.get("start_ms", 0)) / 1000
            if partial:
                self.live_caption_label.setText(f"Ao vivo [{start_s:04.1f}s…]: {partial}")
            return

        if event_type == "transcript":
            self._handle_transcript_event(event)
            return

        if event_type == "summary":
            self.summary_box.setPlainText(str(event.get("text", "")))
            through_s = int(event.get("through_ms", 0)) / 1000
            backend = event.get("backend", "")
            suffix = f" · {backend}" if backend else ""
            self.summary_meta_label.setText(f"Resumo atualizado (até {through_s:.1f}s{suffix})")

    def _handle_transcript_event(self, event: dict) -> None:
        if self.verifier is None:
            self._rejected_count += 1
            self._refresh_integrity_label(tampered=True)
            return

        is_valid = self.verifier.verify(
            session_id=str(event.get("session_id", "")),
            sequence=int(event.get("sequence", -1)),
            start_ms=int(event.get("start_ms", 0)),
            end_ms=int(event.get("end_ms", 0)),
            text=str(event.get("text", "")),
            signature_b64=str(event.get("signature", "")),
        )
        if not is_valid:
            self._rejected_count += 1
            self._refresh_integrity_label(tampered=True)
            self.transcript_box.append(
                "[BLOQUEADO] Legenda adulterada detectada (assinatura Ed25519 inválida)."
            )
            return

        self._verified_count += 1
        self._refresh_integrity_label()
        self.live_caption_label.setText("Ao vivo: ouvindo próximo trecho...")
        self._pending_captions.append(event)
        self._flush_pending_captions(force=False)

    def _on_playback_position(self, timestamp_samples: int) -> None:
        self._current_samples = timestamp_samples
        self._flush_pending_captions(force=False)

    def _flush_pending_captions(self, *, force: bool) -> None:
        remaining: list[dict] = []
        for item in self._pending_captions:
            start_samples = int(item.get("start_samples", 0))
            if force or self._current_samples >= start_samples:
                start_s = int(item.get("start_ms", 0)) / 1000
                end_s = int(item.get("end_ms", 0)) / 1000
                text = str(item.get("text", "")).strip()
                self.transcript_box.append(f"[{start_s:04.1f}s–{end_s:04.1f}s] {text}")
                self.transcript_box.ensureCursorVisible()
            else:
                remaining.append(item)
        self._pending_captions = remaining

    def _refresh_integrity_label(self, *, tampered: bool = False) -> None:
        if tampered:
            self.integrity_label.setText(
                f"ALERTA Ed25519: legenda adulterada rejeitada! | "
                f"Verificadas: {self._verified_count} | Rejeitadas: {self._rejected_count}"
            )
            self.integrity_label.setStyleSheet("font-weight: 700; color: #b42318;")
            return

        self.integrity_label.setText(
            f"Ed25519 ativo | Verificadas: {self._verified_count} | "
            f"Rejeitadas: {self._rejected_count}"
        )
        self.integrity_label.setStyleSheet("font-weight: 600; color: #067647;")

    def _update_metrics(self, metrics: dict) -> None:
        for key in ("received", "played", "lost", "late", "duplicates", "depth"):
            self.metric_labels[key].setText(str(metrics.get(key, 0)))
        kb = int(metrics.get("bytes_received", 0)) / 1024
        self.metric_labels["bytes_kb"].setText(f"{kb:.1f}")

    def _choose_and_upload_audio(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher arquivo de áudio ou palestra",
            "",
            "Áudio/Mídia (*.wav *.mp3 *.m4a *.ogg *.flac *.mp4);;Todos (*.*)",
        )
        if not selected:
            return

        audio_path = Path(selected)
        codec = self.upload_codec_combo.currentText().lower()
        host = self.server_input.text().strip() or "127.0.0.1"
        url = f"http://{host}:{self.server_port_input.value()}/api/v1/stream/upload"

        def _worker() -> None:
            try:
                data = audio_path.read_bytes()
                response = httpx.post(
                    url,
                    params={"filename": audio_path.name, "codec": codec},
                    content=data,
                    timeout=20.0,
                )
                response.raise_for_status()
                self._control_feedback.emit(f"OK: {audio_path.name}")
            except Exception as exc:
                self._control_feedback.emit(f"Erro ao enviar áudio: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _call_server(self, path: str, body: dict | None) -> None:
        host = self.server_input.text().strip() or "127.0.0.1"
        url = f"http://{host}:{self.server_port_input.value()}{path}"

        def _worker() -> None:
            try:
                response = httpx.post(url, json=body, timeout=5.0)
                response.raise_for_status()
                self._control_feedback.emit(f"OK: {path}")
            except Exception as exc:
                self._control_feedback.emit(f"Erro em {path}: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _on_control_feedback(self, message: str) -> None:
        if message.startswith("Erro"):
            self._show_error(message)

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Erro: {message}")
        self.status_label.setStyleSheet("font-weight: 700; color: #b42318;")

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if not self._paused and self.buffer is not None:
            self.buffer.rearm()
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

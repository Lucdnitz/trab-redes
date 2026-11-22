from redes_audio.client.__main__ import build_parser


def test_client_accepts_independent_server_and_udp_ports() -> None:
    args = build_parser().parse_args(
        ["--server", "192.0.2.10", "--server-port", "9000", "--udp-port", "5002"]
    )

    assert args.server == "192.0.2.10"
    assert args.server_port == 9000
    assert args.udp_port == 5002

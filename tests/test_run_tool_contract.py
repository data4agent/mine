from __future__ import annotations

from run_tool import build_parser


def test_run_tool_exposes_guided_session_commands() -> None:
    parser = build_parser()
    command_action = next(action for action in parser._actions if action.dest == "command")
    command_choices = set(command_action.choices or [])

    assert "first-load" in command_choices
    assert "start-working" in command_choices
    assert "check-status" in command_choices
    assert "list-datasets" in command_choices
    assert "pause" in command_choices
    assert "resume" in command_choices
    assert "stop" in command_choices

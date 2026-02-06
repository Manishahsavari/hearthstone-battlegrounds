from pathlib import Path

from services.state_loader import load_recruit_snapshot


def test_load_recruit_snapshot() -> None:
    root = Path(__file__).resolve().parents[1]
    snapshot = load_recruit_snapshot(root / "data/mock_recruit_state_advanced.json")
    assert snapshot.match_id == "mock-adv-001"
    assert len(snapshot.players) == 2
    player = snapshot.players["p1"]
    assert player.hero_name == "Sylvanas Windrunner"
    assert len(player.board) == 7
    assert player.tavern_tier == 3

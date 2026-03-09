from pathlib import Path

from instagram_organizer.infrastructure.instagram.session_manager import SessionManager


class FakeLoader:
    def __init__(self) -> None:
        self.loaded: tuple[str, str] | None = None
        self.saved: str | None = None

    def load_session_from_file(self, username: str, filename: str) -> None:
        self.loaded = (username, filename)

    def save_session_to_file(self, filename: str) -> None:
        self.saved = filename


def test_session_manager_load_and_save(tmp_path: Path) -> None:
    session_file = tmp_path / '.ig_session'
    manager = SessionManager(session_file=session_file)
    loader = FakeLoader()
    manager.load(loader, 'armin')
    manager.save(loader)
    assert loader.loaded == ('armin', str(session_file))
    assert loader.saved == str(session_file)

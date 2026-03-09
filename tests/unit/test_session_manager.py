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


def test_session_manager_load_save_exists_and_clear(tmp_path: Path) -> None:
    session_file = tmp_path / '.ig_session'
    manager = SessionManager(session_file=session_file)
    loader = FakeLoader()

    manager.load(loader, 'armin')
    manager.save(loader)
    session_file.write_text('session', encoding='utf-8')

    assert loader.loaded == ('armin', str(session_file))
    assert loader.saved == str(session_file)
    assert manager.exists() is True
    assert manager.clear() is True
    assert manager.exists() is False

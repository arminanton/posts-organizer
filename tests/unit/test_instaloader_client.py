from pathlib import Path

from instagram_organizer.infrastructure.instagram.instaloader_client import InstaloaderClient


class FakeLoader:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.context = type('Context', (), {'username': 'sample-user'})()
        self.calls = []
        self.login_calls: list[tuple[str, str]] = []
        self.two_factor_calls: list[str] = []

    def download_post(self, post, target: str) -> None:
        self.calls.append((post, target))

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def two_factor_login(self, code: str) -> None:
        self.two_factor_calls.append(code)

    def test_login(self) -> str:
        return 'sample-user'


class FakeProfile:
    def get_posts(self):
        return ['a', 'b']


def test_instaloader_client_fetches_profile_downloads_and_authenticates(tmp_path: Path) -> None:
    client = InstaloaderClient(
        loader_factory=lambda **kwargs: FakeLoader(**kwargs),
        profile_resolver=lambda context, username: (context, username, FakeProfile()),
    )
    context, username, profile = client.fetch_profile('target')
    assert username == 'target'
    assert list(client.iter_posts(profile)) == ['a', 'b']
    client.download_post('post', tmp_path)
    client.login('armin', 'password123')
    client.two_factor_login('246810')
    assert client.test_login() == 'sample-user'
    assert context.username == 'sample-user'
    assert client.loader.calls == [('post', str(tmp_path))]
    assert client.loader.login_calls == [('armin', 'password123')]
    assert client.loader.two_factor_calls == ['246810']

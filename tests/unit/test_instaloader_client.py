from pathlib import Path

from instagram_organizer.infrastructure.instagram.instaloader_client import InstaloaderClient


class FakeLoader:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.context = 'ctx'
        self.calls = []

    def download_post(self, post, target: str) -> None:
        self.calls.append((post, target))


class FakeProfile:
    def get_posts(self):
        return ['a', 'b']


def test_instaloader_client_fetches_profile_and_downloads(tmp_path: Path) -> None:
    client = InstaloaderClient(
        loader_factory=lambda **kwargs: FakeLoader(**kwargs),
        profile_resolver=lambda context, username: (context, username, FakeProfile()),
    )
    context, username, profile = client.fetch_profile('target')
    assert context == 'ctx'
    assert username == 'target'
    assert list(client.iter_posts(profile)) == ['a', 'b']
    client.download_post('post', tmp_path)
    assert client.loader.calls == [('post', str(tmp_path))]

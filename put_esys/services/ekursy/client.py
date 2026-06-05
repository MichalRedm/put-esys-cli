from typing import Optional

import requests

from put_esys.services.auth import ensure_authenticated_session


class EKursyClient:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session
        if not self.session:
            self.session = ensure_authenticated_session()

    @property
    def is_authenticated(self) -> bool:
        return self.session is not None

    def download_resource(self, url: str) -> requests.Response:
        """Download a resource (file) from a URL."""
        if not self.session:
            raise Exception("Session is not authenticated.")
        response = self.session.get(url, stream=True)
        response.raise_for_status()
        return response

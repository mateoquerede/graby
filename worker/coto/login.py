"""Login helper for Coto Digital using per-job credentials."""


def login_with_credentials(client, email: str, password: str):
    return client.login(email, password)

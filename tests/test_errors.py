def test_root_redirects_to_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/login.html"


def test_unknown_api_path_is_code_msg(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert set(r.json()) == {"code", "msg"}

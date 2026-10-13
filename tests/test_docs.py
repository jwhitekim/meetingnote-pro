METHODS = {"get", "post", "put", "delete", "patch"}


def api_ops(spec):
    return [(path, m) for path, ops in spec["paths"].items() if path.startswith("/api/") for m in ops if m in METHODS]


# Swagger UI 제공
def test_openapi_has_26_api_operations(client):
    spec = client.get("/openapi.json").json()
    assert len(api_ops(spec)) == 26


def test_operations_grouped_by_six_tags(client):
    spec = client.get("/openapi.json").json()
    tags = {spec["paths"][p][m]["tags"][0] for p, m in api_ops(spec)}
    assert tags == {"Auth", "Team", "Meeting", "Todo", "Comment", "Activity"}


def test_docs_page(client):
    r = client.get("/docs")
    assert r.status_code == 200 and "swagger-ui" in r.text


# Swagger UI 에서 인증 API 시험
def test_bearer_scheme_on_me(client):
    spec = client.get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    name, scheme = next(iter(schemes.items()))
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer"
    assert {name: []} in spec["paths"]["/api/auth/me"]["get"]["security"]
    assert "security" not in spec["paths"]["/api/auth/login"]["post"]


def test_token_from_login_works_as_bearer(client):
    client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "password123", "name": "김대리"})
    token = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password123"}).json()["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "kim@example.com"

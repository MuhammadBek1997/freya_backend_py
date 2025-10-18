import os
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
employee_id = "2b5f1c72-51fd-4b59-98fd-9c41fcae7c2c"
start_date = "2024-10-14"
url = f"/api/mobile/schedules/employee/{employee_id}?start_date={start_date}&page=1&limit=7"
resp = client.get(url)
print(resp.status_code)
print(resp.json())

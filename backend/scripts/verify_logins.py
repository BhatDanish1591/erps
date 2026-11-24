import asyncio
import httpx

async def main():
    accounts = [
        ("superadmin@edusaas.com", "Super Admin"),
        ("college.admin@apex.edu", "College Admin"),
        ("school.admin@greenwood.edu", "School Admin"),
        ("teacher@apex.edu", "Teacher"),
        ("student@apex.edu", "Student"),
        ("parent@apex.edu", "Parent"),
    ]
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        for email, role_name in accounts:
            res = await client.post("/api/v1/auth/login", json={"identifier": email, "password": "Password123!"})
            if res.status_code == 200:
                d = res.json()["data"]["user"]
                print(f"[OK] {role_name:<15} | Email: {email:<26} | Name: {d.get('full_name')}")
            else:
                print(f"[FAIL] {role_name} -> {res.status_code}")

if __name__ == "__main__":
    asyncio.run(main())

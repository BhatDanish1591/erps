#!/usr/bin/env python3
"""
EduSaaS CRM - High-Concurrency Production Load & Stress Benchmark
Simulates high concurrency across authentication, health, and multi-tenant endpoints.
Measures latency percentiles (P50, P90, P95, P99), throughput (RPS), and error rates.

Usage:
    python scripts/load_test.py --url http://localhost:8000 --users 50 --requests 500
"""

import argparse
import asyncio
import time
from typing import List
import httpx


async def worker(client: httpx.AsyncClient, url: str, endpoint: str, latencies: List[float], errors: List[int]):
    start = time.perf_counter()
    try:
        resp = await client.get(f"{url}{endpoint}", timeout=10.0)
        elapsed = (time.perf_counter() - start) * 1000.0  # ms
        latencies.append(elapsed)
        if resp.status_code >= 400 and resp.status_code != 429:
            errors.append(resp.status_code)
    except Exception:
        errors.append(500)


async def run_benchmark(base_url: str, total_users: int, total_requests: int):
    print("=" * 65)
    print(f"🚀 EduSaaS CRM Concurrency Load Test")
    print(f"Target URL:        {base_url}")
    print(f"Concurrent Users:  {total_users}")
    print(f"Total Requests:    {total_requests}")
    print("=" * 65)

    endpoints = [
        "/api/v1/health",
        "/api/v1/auth/me",
        "/api/v1/institutions/public/catalog",
    ]

    latencies: List[float] = []
    errors: List[int] = []

    limits = httpx.Limits(max_connections=total_users + 10, max_keepalive_connections=total_users)
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        start_time = time.perf_counter()

        # Batch tasks according to concurrency
        tasks = []
        for i in range(total_requests):
            ep = endpoints[i % len(endpoints)]
            tasks.append(worker(client, base_url, ep, latencies, errors))

        # Run with Semaphore
        sem = asyncio.Semaphore(total_users)

        async def sem_worker(t):
            async with sem:
                await t

        await asyncio.gather(*(sem_worker(t) for t in tasks))
        total_duration = time.perf_counter() - start_time

    if not latencies:
        print("❌ All requests failed to execute.")
        return

    latencies.sort()
    count = len(latencies)
    rps = count / total_duration if total_duration > 0 else 0
    p50 = latencies[int(count * 0.50)]
    p90 = latencies[int(count * 0.90)]
    p95 = latencies[int(count * 0.95)]
    p99 = latencies[int(count * 0.99)]
    err_count = len(errors)
    err_rate = (err_count / count) * 100.0 if count > 0 else 0.0

    print("\n" + "=" * 65)
    print("📊 BENCHMARK RESULTS")
    print("=" * 65)
    print(f"Completed Requests:  {count} in {total_duration:.2f}s")
    print(f"Throughput:          {rps:.2f} req/sec")
    print(f"Error Rate:          {err_rate:.2f}% ({err_count} errors)")
    print(f"P50 Latency:         {p50:.2f} ms")
    print(f"P90 Latency:         {p90:.2f} ms")
    print(f"P95 Latency:         {p95:.2f} ms")
    print(f"P99 Latency:         {p99:.2f} ms")
    print(f"Min / Max Latency:   {latencies[0]:.2f} ms / {latencies[-1]:.2f} ms")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduSaaS Production Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of application")
    parser.add_argument("--users", type=int, default=30, help="Concurrent client workers")
    parser.add_argument("--requests", type=int, default=150, help="Total HTTP requests to send")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.url, args.users, args.requests))

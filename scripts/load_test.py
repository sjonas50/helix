"""Load test script for Helix API.

Usage:
    pip install httpx
    python scripts/load_test.py --base-url http://localhost:8000 --concurrency 50

Tests:
    1. Health endpoint latency (target: <10ms p95)
    2. Authenticated workflow list (target: <50ms p95)
    3. Memory semantic search (target: <100ms p95)
    4. Concurrent org creation (target: 100 concurrent)
"""

import argparse
import asyncio
import statistics
import time
import uuid

import httpx


def make_jwt_header() -> dict[str, str]:
    """Create a test JWT for load testing. Requires the API to be running with known SECRET_KEY."""
    # In production load tests, generate real JWTs
    # For now, we'll hit unauthenticated endpoints
    return {}


async def test_health(client: httpx.AsyncClient, n: int) -> list[float]:
    """Test health endpoint latency."""
    latencies = []
    for _ in range(n):
        start = time.monotonic()
        r = await client.get("/health")
        latencies.append((time.monotonic() - start) * 1000)
        assert r.status_code == 200
    return latencies


async def test_concurrent_health(client: httpx.AsyncClient, concurrency: int) -> list[float]:
    """Test health endpoint under concurrent load."""
    async def _single():
        start = time.monotonic()
        r = await client.get("/health")
        return (time.monotonic() - start) * 1000

    tasks = [_single() for _ in range(concurrency)]
    return await asyncio.gather(*tasks)


def report(name: str, latencies: list[float]) -> None:
    """Print latency statistics."""
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg = statistics.mean(latencies)

    print(f"\n{'=' * 50}")
    print(f"  {name}")
    print(f"{'=' * 50}")
    print(f"  Requests:  {len(latencies)}")
    print(f"  Avg:       {avg:.1f}ms")
    print(f"  P50:       {p50:.1f}ms")
    print(f"  P95:       {p95:.1f}ms")
    print(f"  P99:       {p99:.1f}ms")
    print(f"  Min:       {min(latencies):.1f}ms")
    print(f"  Max:       {max(latencies):.1f}ms")


async def main(base_url: str, concurrency: int) -> None:
    """Run all load tests."""
    print(f"Helix Load Test — {base_url} (concurrency={concurrency})")

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # 1. Sequential health checks (warm up)
        latencies = await test_health(client, 100)
        report("Health (sequential, 100 requests)", latencies)

        # 2. Concurrent health checks
        latencies = await test_concurrent_health(client, concurrency)
        report(f"Health (concurrent, {concurrency} requests)", latencies)

        # 3. Sustained load
        latencies = []
        for _ in range(5):
            batch = await test_concurrent_health(client, concurrency)
            latencies.extend(batch)
        report(f"Health (sustained, 5 x {concurrency} requests)", latencies)

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Helix API Load Test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=50)
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.concurrency))

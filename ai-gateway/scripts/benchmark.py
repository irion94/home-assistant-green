#!/usr/bin/env python3
"""Performance benchmark script for AI Gateway (Phase 7).

Tests conversation endpoint latency under load.
Target: P95 < 2000ms (down from 8-13s baseline).

Usage:
    python scripts/benchmark.py --requests 100 --url http://localhost:8080/conversation
"""

import asyncio
import argparse
import time
from statistics import mean, median
from typing import List

import httpx


async def benchmark_conversation(
    url: str,
    num_requests: int = 100,
    concurrent: int = 1,
    session_prefix: str = "bench"
) -> dict:
    """
    Benchmark conversation endpoint.

    Args:
        url: Conversation endpoint URL
        num_requests: Total number of requests to send
        concurrent: Number of concurrent requests
        session_prefix: Prefix for session IDs

    Returns:
        Dictionary with benchmark results
    """
    latencies: List[float] = []
    errors = 0

    print(f"Benchmarking: {url}")
    print(f"Requests: {num_requests}, Concurrent: {concurrent}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for batch in range(0, num_requests, concurrent):
            batch_size = min(concurrent, num_requests - batch)
            tasks = []

            for i in range(batch_size):
                request_id = batch + i
                tasks.append(
                    make_request(
                        client,
                        url,
                        request_id,
                        f"{session_prefix}-{request_id}"
                    )
                )

            # Execute batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    print(f"✗ Error: {result}")
                else:
                    latencies.append(result)

            # Progress update
            completed = batch + batch_size
            if completed % 10 == 0 or completed == num_requests:
                print(f"Progress: {completed}/{num_requests} ({errors} errors)")

    return calculate_stats(latencies, errors, num_requests)


async def make_request(
    client: httpx.AsyncClient,
    url: str,
    request_id: int,
    session_id: str
) -> float:
    """
    Make a single request and measure latency.

    Args:
        client: HTTP client
        url: Endpoint URL
        request_id: Request number
        session_id: Session ID

    Returns:
        Latency in milliseconds

    Raises:
        Exception: On request failure
    """
    start = time.time()

    response = await client.post(url, json={
        "text": "Turn on living room lights",
        "session_id": session_id,
        "room_id": "test"
    })

    latency = (time.time() - start) * 1000  # Convert to ms

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")

    return latency


def calculate_stats(latencies: List[float], errors: int, total: int) -> dict:
    """
    Calculate benchmark statistics.

    Args:
        latencies: List of latency measurements (ms)
        errors: Number of failed requests
        total: Total requests attempted

    Returns:
        Statistics dictionary
    """
    if not latencies:
        return {
            "total_requests": total,
            "successful": 0,
            "errors": errors,
            "error_rate": 100.0,
        }

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    stats = {
        "total_requests": total,
        "successful": n,
        "errors": errors,
        "error_rate": (errors / total) * 100,
        "latency_ms": {
            "mean": mean(latencies),
            "median": median(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "p50": sorted_latencies[int(n * 0.50)],
            "p90": sorted_latencies[int(n * 0.90)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)] if n > 10 else sorted_latencies[-1],
        }
    }

    return stats


def print_results(stats: dict):
    """
    Print benchmark results.

    Args:
        stats: Statistics dictionary from calculate_stats()
    """
    print(f"\n{'='*60}")
    print("BENCHMARK RESULTS")
    print(f"{'='*60}\n")

    print(f"Total Requests:  {stats['total_requests']}")
    print(f"Successful:      {stats['successful']}")
    print(f"Errors:          {stats['errors']}")
    print(f"Error Rate:      {stats['error_rate']:.2f}%\n")

    if stats['successful'] > 0:
        latency = stats['latency_ms']
        print("Latency (milliseconds):")
        print(f"  Mean:    {latency['mean']:>8.2f} ms")
        print(f"  Median:  {latency['median']:>8.2f} ms")
        print(f"  Min:     {latency['min']:>8.2f} ms")
        print(f"  Max:     {latency['max']:>8.2f} ms")
        print(f"  P50:     {latency['p50']:>8.2f} ms")
        print(f"  P90:     {latency['p90']:>8.2f} ms")
        print(f"  P95:     {latency['p95']:>8.2f} ms")
        print(f"  P99:     {latency['p99']:>8.2f} ms\n")

        # Phase 7 success criteria
        target_p95 = 2000  # 2 seconds
        if latency['p95'] < target_p95:
            print(f"✓ SUCCESS: P95 ({latency['p95']:.2f}ms) < {target_p95}ms target")
        else:
            print(f"✗ FAIL: P95 ({latency['p95']:.2f}ms) >= {target_p95}ms target")

    print(f"\n{'='*60}\n")


async def main():
    """Main benchmark entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark AI Gateway conversation endpoint"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080/conversation",
        help="Conversation endpoint URL"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests to send"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=1,
        help="Number of concurrent requests"
    )
    parser.add_argument(
        "--session-prefix",
        default="bench",
        help="Prefix for session IDs"
    )

    args = parser.parse_args()

    # Run benchmark
    stats = await benchmark_conversation(
        url=args.url,
        num_requests=args.requests,
        concurrent=args.concurrent,
        session_prefix=args.session_prefix
    )

    # Print results
    print_results(stats)


if __name__ == "__main__":
    asyncio.run(main())

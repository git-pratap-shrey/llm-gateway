#!/usr/bin/env python3
"""
Load test script for the async LLM gateway endpoint.
Simulates N concurrent requests and polls for completion.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx
import json
import random
from pathlib import Path
from datetime import datetime


@dataclass
class JobResult:
    """Tracks the result of a single async job."""
    job_id: str
    submit_time: float
    provider: str = ""
    model: str = ""
    complete_time: Optional[float] = None
    status: str = "submitted"
    response: Optional[str] = None
    error: Optional[str] = None
    poll_attempts: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """Total time from submission to completion in seconds."""
        if self.complete_time:
            return self.complete_time - self.submit_time
        return None
    
    @property
    def success(self) -> bool:
        """Whether the job completed successfully."""
        return self.status == "completed" and self.error is None


@dataclass
class LoadTestReport:
    """Aggregates metrics from the load test."""
    total_jobs: int = 0
    successful: int = 0
    failed: int = 0
    timed_out: int = 0
    durations: list[float] = field(default_factory=list)
    completion_times: list[float] = field(default_factory=list)  # Track absolute completion times
    errors: list[str] = field(default_factory=list)
    provider_stats: dict[str, dict[str, int]] = field(default_factory=dict)  # Track per-provider stats
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful jobs."""
        return (self.successful / self.total_jobs * 100) if self.total_jobs > 0 else 0.0
    
    @property
    def avg_duration(self) -> Optional[float]:
        """Average completion time in seconds."""
        return sum(self.durations) / len(self.durations) if self.durations else None
    
    @property
    def min_duration(self) -> Optional[float]:
        """Fastest completion time."""
        return min(self.durations) if self.durations else None
    
    @property
    def max_duration(self) -> Optional[float]:
        """Slowest completion time."""
        return max(self.durations) if self.durations else None
    
    @property
    def avg_time_between_completions(self) -> Optional[float]:
        """Average time between successful request completions."""
        if len(self.completion_times) < 2:
            return None
        
        # Sort completion times
        sorted_times = sorted(self.completion_times)
        
        # Calculate intervals between consecutive completions
        intervals = [sorted_times[i+1] - sorted_times[i] for i in range(len(sorted_times) - 1)]
        
        return sum(intervals) / len(intervals) if intervals else None
    
    def record_provider_stat(self, provider: str, status: str):
        """Record statistics for a specific provider."""
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {'total': 0, 'success': 0, 'failed': 0, 'timeout': 0}
        
        self.provider_stats[provider]['total'] += 1
        if status == 'completed':
            self.provider_stats[provider]['success'] += 1
        elif status == 'timeout':
            self.provider_stats[provider]['timeout'] += 1
        else:
            self.provider_stats[provider]['failed'] += 1
    
    def print_summary(self):
        """Print a formatted summary of the load test."""
        print("\n" + "="*60)
        print("LOAD TEST SUMMARY")
        print("="*60)
        print(f"Total Jobs:        {self.total_jobs}")
        print(f"Successful:        {self.successful} ({self.success_rate:.1f}%)")
        print(f"Failed:            {self.failed}")
        print(f"Timed Out:         {self.timed_out}")
        print()
        if self.durations:
            print(f"Avg Duration:      {self.avg_duration:.2f}s")
            print(f"Min Duration:      {self.min_duration:.2f}s")
            print(f"Max Duration:      {self.max_duration:.2f}s")
        if self.avg_time_between_completions is not None:
            print(f"Avg Time Between:  {self.avg_time_between_completions:.2f}s")
        print()
        if self.provider_stats:
            print("PROVIDER BREAKDOWN:")
            for provider, stats in sorted(self.provider_stats.items()):
                total = stats.get('total', 0)
                success = stats.get('success', 0)
                failed = stats.get('failed', 0)
                timeout = stats.get('timeout', 0)
                success_rate = (success / total * 100) if total > 0 else 0
                print(f"  {provider:20s} - Total: {total:3d}, Success: {success:3d} ({success_rate:5.1f}%), Failed: {failed:3d}, Timeout: {timeout:3d}")
        print()
        if self.errors:
            print("ERRORS:")
            for i, error in enumerate(self.errors[:10], 1):  # Show first 10 errors
                print(f"  {i}. {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        print("="*60 + "\n")


class AsyncLLMLoadTester:
    """Load tester for the async LLM gateway."""
    
    # Randomized messages for load testing
    DEFAULT_MESSAGES = [
        "Hello.",
        "What is artificial intelligence?",
        "Explain quantum computing in simple terms.",
        "Write a short poem about the ocean.",
        "What are the benefits of renewable energy?",
        "How does photosynthesis work?",
        "Tell me a fun fact about space.",
        "What is the capital of France?",
        "Explain the theory of relativity.",
        "How do neural networks learn?",
        "What is the meaning of life?",
        "Describe the water cycle.",
        "What causes seasons on Earth?",
        "How does blockchain technology work?",
        "What are the primary colors?",
    ]
    
    def __init__(
        self,
        base_url: str = "https://lm-gateway.git-pratap-shrey.online",
        poll_interval: float = 2.0,
        timeout: float = 120.0,
        model_config_path: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.jobs: dict[str, JobResult] = {}
        self.report = LoadTestReport()
        self.model_configs = self._load_model_configs(model_config_path)
    
    def _load_model_configs(self, config_path: Optional[str]) -> list[dict]:
        """Load model configurations from JSON file."""
        if not config_path:
            return []
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                models = data.get('models', [])
                print(f"✓ Loaded {len(models)} model configurations from {config_path}")
                return models
        except FileNotFoundError:
            print(f"⚠️  Config file not found: {config_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON in config file: {e}")
            return []
    
    def _get_random_model_config(self) -> tuple[str, str]:
        """Get a random provider and model from loaded configs."""
        if not self.model_configs:
            # Fallback to default
            return "gemini", "gemma-4-31b-it"
        
        config = random.choice(self.model_configs)
        return config['provider'], config['model']
    
    def _get_random_message(self) -> str:
        """Get a random message from the default message list."""
        return random.choice(self.DEFAULT_MESSAGES)
    
    def _calculate_timeout(self, n_requests: int) -> float:
        """
        Calculate appropriate timeout based on number of requests.
        
        Args:
            n_requests: Number of requests in the load test
            
        Returns:
            Timeout in seconds
        """
        # Base timeout for small loads
        base_timeout = 60.0
        
        # Scale timeout based on request count
        # Assume ~5 seconds per request on average for processing
        # Add buffer for queue delays and batch processing
        if n_requests <= 10:
            return base_timeout
        elif n_requests <= 50:
            return base_timeout + (n_requests * 3)  # ~60-210s
        elif n_requests <= 100:
            return base_timeout + (n_requests * 4)  # ~260-460s
        else:
            return base_timeout + (n_requests * 5)  # 500s+
    
    
    async def submit_job(
        self,
        client: httpx.AsyncClient,
        provider: str = "gemini",
        model: str = "gemma-4-31b-it",
        message: str = "Hello.",
    ) -> Optional[JobResult]:
        """Submit a single async job to the gateway."""
        payload = {
            "provider": provider,
            "model": model,
            "messages": [{"role": "user", "content": message}]
        }
        
        try:
            submit_time = time.time()
            response = await client.post(
                f"{self.base_url}/api/async",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            
            data = response.json()
            job_id = data.get("job_id")
            
            if not job_id:
                print(f"❌ No job_id in response: {data}")
                return None
            
            job_result = JobResult(
                job_id=job_id,
                submit_time=submit_time,
                provider=provider,
                model=model
            )
            self.jobs[job_id] = job_result
            print(f"✓ Submitted job {job_id[:8]}... [{provider}/{model}]")
            return job_result
            
        except Exception as e:
            print(f"❌ Failed to submit job [{provider}/{model}]: {e}")
            self.report.errors.append(f"Submit error [{provider}/{model}]: {str(e)}")
            return None
    
    async def poll_job(
        self,
        client: httpx.AsyncClient,
        job_result: JobResult,
    ) -> None:
        """Poll a job until it completes or times out."""
        start_poll = time.time()
        
        while True:
            elapsed = time.time() - start_poll
            if elapsed > self.timeout:
                job_result.status = "timeout"
                job_result.error = f"Timed out after {self.timeout}s"
                print(f"⏱️  Job {job_result.job_id[:8]}... [{job_result.provider}/{job_result.model}] timed out")
                self.report.timed_out += 1
                self.report.record_provider_stat(job_result.provider, "timeout")
                return
            
            try:
                response = await client.get(
                    f"{self.base_url}/{job_result.job_id}",
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                
                job_result.poll_attempts += 1
                status = data.get("status", "unknown")
                job_result.status = status
                
                if status == "completed":
                    job_result.complete_time = time.time()
                    job_result.response = data.get("response")
                    duration = job_result.duration
                    print(f"✓ Job {job_result.job_id[:8]}... [{job_result.provider}/{job_result.model}] completed in {duration:.2f}s (polled {job_result.poll_attempts}x)")
                    
                    self.report.successful += 1
                    self.report.durations.append(duration)
                    self.report.completion_times.append(job_result.complete_time)
                    self.report.record_provider_stat(job_result.provider, "completed")
                    return
                
                elif status == "failed":
                    job_result.complete_time = time.time()
                    job_result.error = data.get("error", "Unknown error")
                    print(f"❌ Job {job_result.job_id[:8]}... [{job_result.provider}/{job_result.model}] failed: {job_result.error}")
                    
                    self.report.failed += 1
                    self.report.errors.append(f"Job {job_result.job_id} [{job_result.provider}/{job_result.model}]: {job_result.error}")
                    self.report.record_provider_stat(job_result.provider, "failed")
                    return
                
                elif status == "processing":
                    # Still processing, keep polling
                    await asyncio.sleep(self.poll_interval)
                
                else:
                    # Unknown status, keep polling
                    await asyncio.sleep(self.poll_interval)
                    
            except Exception as e:
                job_result.error = str(e)
                job_result.status = "error"
                print(f"❌ Error polling job {job_result.job_id[:8]}... [{job_result.provider}/{job_result.model}]: {e}")
                
                self.report.failed += 1
                self.report.errors.append(f"Poll error for {job_result.job_id} [{job_result.provider}/{job_result.model}]: {str(e)}")
                self.report.record_provider_stat(job_result.provider, "failed")
                return
    
    async def run_load_test(
        self,
        n_requests: int,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: int = 10,
        randomize: bool = False,
        use_dynamic_timeout: bool = True,
    ) -> LoadTestReport:
        """
        Run the load test with N requests.
        
        Args:
            n_requests: Number of async requests to send
            provider: LLM provider (gemini, ollama, openrouter) - ignored if randomize=True
            model: Model name - ignored if randomize=True
            batch_size: Number of concurrent submissions at once
            randomize: Use random provider/model from config file
            use_dynamic_timeout: Calculate timeout based on request count
        """
        self.report.total_jobs = n_requests
        
        # Use dynamic timeout if enabled
        if use_dynamic_timeout:
            self.timeout = self._calculate_timeout(n_requests)
        
        print(f"\n🚀 Starting load test with {n_requests} requests...")
        if randomize and self.model_configs:
            print(f"   Randomizing across {len(self.model_configs)} model configurations")
        else:
            print(f"   Provider: {provider or 'gemini'}")
            print(f"   Model: {model or 'gemma-4-31b-it'}")
        print(f"   Messages: Randomized from {len(self.DEFAULT_MESSAGES)} options")
        print(f"   Poll interval: {self.poll_interval}s")
        print(f"   Timeout: {self.timeout:.1f}s {'(dynamic)' if use_dynamic_timeout else ''}")
        print(f"   Batch size: {batch_size}\n")
        
        async with httpx.AsyncClient() as client:
            # Submit all jobs in batches
            submitted_jobs = []
            for i in range(0, n_requests, batch_size):
                batch = []
                for j in range(i, min(i + batch_size, n_requests)):
                    # Always use random message
                    message = self._get_random_message()
                    
                    # Determine provider and model for this request
                    if randomize and self.model_configs:
                        req_provider, req_model = self._get_random_model_config()
                    else:
                        req_provider = provider or "gemini"
                        req_model = model or "gemma-4-31b-it"
                    
                    batch.append(self.submit_job(client, req_provider, req_model, message))
                
                results = await asyncio.gather(*batch)
                submitted_jobs.extend([job for job in results if job is not None])
                
                # Small delay between batches to avoid overwhelming the server
                if i + batch_size < n_requests:
                    await asyncio.sleep(0.5)
            
            print(f"\n✓ Submitted {len(submitted_jobs)} jobs\n")
            print("Polling for completion...\n")
            
            # Poll all jobs concurrently
            poll_tasks = [self.poll_job(client, job) for job in submitted_jobs]
            await asyncio.gather(*poll_tasks)
        
        return self.report

async def main():
    """Main entry point for the load test."""
    random.seed(42)
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test the async LLM gateway")
    parser.add_argument("-n", "--requests", type=int, default=10, help="Number of requests to send")
    parser.add_argument("-u", "--url", default="https://lm-gateway.git-pratap-shrey.online", help="Gateway base URL")
    parser.add_argument("-p", "--provider", help="LLM provider (ignored if --randomize is used)")
    parser.add_argument("-m", "--model", help="Model name (ignored if --randomize is used)")
    parser.add_argument("-c", "--config", default="load_test.json", help="Path to model config JSON file")
    parser.add_argument("-r", "--randomize", action="store_true", help="Randomize provider/model from config file")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("-t", "--timeout", type=float, help="Job timeout in seconds (auto-calculated if not provided)")
    parser.add_argument("-b", "--batch-size", type=int, default=10, help="Concurrent submission batch size")
    
    args = parser.parse_args()
    
    # Determine if we should use dynamic timeout
    use_dynamic_timeout = args.timeout is None
    
    tester = AsyncLLMLoadTester(
        base_url=args.url,
        poll_interval=args.interval,
        timeout=args.timeout if args.timeout else 120.0,  # placeholder, will be overridden if dynamic
        model_config_path=args.config if args.randomize else None,
    )
    
    start_time = time.time()
    report = await tester.run_load_test(
        n_requests=args.requests,
        provider=args.provider,
        model=args.model,
        batch_size=args.batch_size,
        randomize=args.randomize,
        use_dynamic_timeout=use_dynamic_timeout,
    )
    total_time = time.time() - start_time
    
    report.print_summary()
    print(f"Total test duration: {total_time:.2f}s")
    print(f"Throughput: {args.requests / total_time:.2f} jobs/s\n")


if __name__ == "__main__":
    asyncio.run(main())

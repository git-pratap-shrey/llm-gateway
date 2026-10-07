#!/usr/bin/env python3
"""
Script to spawn and manage multiple worker containers using Docker.
Monitors container health and handles graceful shutdown.
"""

import subprocess
import signal
import sys
import time
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import os
from dotenv import dotenv_values

KEYS = [k.strip() for k in dotenv_values(".env")["OLLAMA_API_KEY"].split(",") if k.strip()]
PIN = os.environ.get("PIN", "1") == "1"   # PIN=0 to run unpinned for A/B


@dataclass
class WorkerContainer:
    """Tracks a worker container."""
    worker_id: int
    container_name: str
    container_id: Optional[str]
    start_time: float
    restart_count: int = 0
    
    @property
    def uptime(self) -> float:
        """Uptime in seconds."""
        return time.time() - self.start_time
    
    @property
    def is_running(self) -> bool:
        """Check if the container is still running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "true"
        except Exception:
            return False
    
    @property
    def status(self) -> str:
        """Get container status."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"


class WorkerManager:
    """Manages multiple worker containers using Docker."""
    
    def __init__(
        self,
        num_workers: int,
        image_name: str = "llm_gateway-worker",
        auto_restart: bool = True,
        compose_file: str = "docker-compose.yml"
    ):
        self.num_workers = num_workers
        self.image_name = image_name
        self.auto_restart = auto_restart
        self.compose_file = compose_file
        self.workers: list[WorkerContainer] = []
        self.shutdown_requested = False
        self.project_name = "llmgateway"
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived shutdown signal ({signal.Signals(signum).name})")
        self.shutdown_requested = True
    
    def _ensure_image_built(self):
        """Ensure the Docker image is built."""
        print("🔍 Checking Docker image...")
        
        result = subprocess.run(
            ["docker", "images", "-q", self.image_name],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            print(f"Building Docker image: {self.image_name}...")
            build_result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "build", "worker"],
                capture_output=False
            )
            if build_result.returncode != 0:
                print("Failed to build Docker image")
                sys.exit(1)
            print("Docker image built successfully")
        else:
            print(f"Docker image {self.image_name} exists")
    
    def spawn_worker(self, worker_id: int) -> WorkerContainer:
        """Spawn a single worker container."""
        container_name = f"{self.project_name}_worker_{worker_id}"
        print(f"Spawning worker container {worker_id} ({container_name})...")
        
        pin_args = (
            ["-e", f"OLLAMA_API_KEY={KEYS[(worker_id - 1) % len(KEYS)]}"] if PIN else []
        )

        result = subprocess.run(
            [
                "docker", "run",
                "-d",  # Detached mode
                "--name", container_name,
                "--env-file", ".env",
                *pin_args,  # overrides OLLAMA_API_KEY from .env with this worker's single key
                "-e", "RABBITMQ_HOST=localhost",
                "-e", "RESULT_DB_PATH=/app/data/result_db.db",
                "--network", "host",
                "-v", f"{os.getcwd()}/data:/app/data",
                self.image_name,
                "uv", "run", "worker.py"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Failed to spawn worker {worker_id}: {result.stderr}")
            container_id = None
        else:
            container_id = result.stdout.strip()
            print(f"Worker {worker_id} started (Container ID: {container_id[:12]})")
        
        worker = WorkerContainer(
            worker_id=worker_id,
            container_name=container_name,
            container_id=container_id,
            start_time=time.time()
        )
        
        return worker
    
    def start_workers(self):
        """Start all worker containers."""
        print(f"\n{'='*60}")
        print(f"STARTING {self.num_workers} WORKER CONTAINERS")
        print(f"Image: {self.image_name}")
        print(f"Auto-restart: {self.auto_restart}")
        print(f"{'='*60}\n")
        
        self._ensure_image_built()
        print()
        
        for i in range(1, self.num_workers + 1):
            worker = self.spawn_worker(i)
            self.workers.append(worker)
            time.sleep(0.5)  # Small delay between spawns
        
        print(f"\n✓ All {self.num_workers} workers started\n")
    
    def check_workers(self):
        """Check worker health and restart if needed."""
        for worker in self.workers:
            if not worker.is_running:
                status = worker.status
                print(f"Worker {worker.worker_id} ({worker.container_name}) is {status}")
                
                if self.auto_restart and not self.shutdown_requested:
                    worker.restart_count += 1
                    print(f"Restarting worker {worker.worker_id} (restart #{worker.restart_count})...")
                    
                    # Remove old container
                    subprocess.run(
                        ["docker", "rm", "-f", worker.container_name],
                        capture_output=True
                    )
                    
                    # Spawn new container
                    new_worker = self.spawn_worker(worker.worker_id)
                    worker.container_name = new_worker.container_name
                    worker.container_id = new_worker.container_id
                    worker.start_time = time.time()
    
    def print_status(self):
        """Print current status of all workers."""
        running = sum(1 for w in self.workers if w.is_running)
        stopped = len(self.workers) - running
        
        print(f"\n{'='*60}")
        print(f"WORKER STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Total: {len(self.workers)} | Running: {running} | Stopped: {stopped}\n")
        
        for worker in self.workers:
            is_running = worker.is_running
            status_icon = "RUNNING" if is_running else f" {worker.status.upper()}"
            uptime = f"{worker.uptime:.1f}s" if is_running else "N/A"
            restarts = f" | Restarts: {worker.restart_count}" if worker.restart_count > 0 else ""
            container_id = worker.container_id[:12] if worker.container_id else "N/A"
            print(f"  Worker {worker.worker_id:2d} | Container: {container_id} | {status_icon} | Uptime: {uptime:>8s}{restarts}")
        
        print(f"{'='*60}\n")
    
    def stop_workers(self):
        """Stop all worker containers gracefully."""
        print("\nStopping all workers...")
        
        for worker in self.workers:
            if worker.is_running or worker.container_id:
                print(f"   Stopping worker {worker.worker_id} ({worker.container_name})...")
                subprocess.run(
                    ["docker", "stop", "-t", "10", worker.container_name],
                    capture_output=True
                )
        
        # Remove containers
        print("   Removing containers...")
        for worker in self.workers:
            subprocess.run(
                ["docker", "rm", "-f", worker.container_name],
                capture_output=True
            )
        
        print("\n✓ All workers stopped\n")
    
    def run(self, check_interval: float = 5.0, status_interval: float = 30.0):
        """
        Main loop to monitor workers.
        
        Args:
            check_interval: How often to check worker health (seconds)
            status_interval: How often to print status (seconds)
        """
        self.start_workers()
        
        last_status = time.time()
        
        try:
            while not self.shutdown_requested:
                self.check_workers()
                
                # Print status periodically
                if time.time() - last_status >= status_interval:
                    self.print_status()
                    last_status = time.time()
                
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n Interrupted by user")
        
        finally:
            self.stop_workers()
            self.print_final_report()
    
    def print_final_report(self):
        """Print final statistics."""
        print(f"\n{'='*60}")
        print("FINAL REPORT")
        print(f"{'='*60}")
        
        for worker in self.workers:
            container_id = worker.container_id[:12] if worker.container_id else "N/A"
            print(f"  Worker {worker.worker_id:2d}: Restarts: {worker.restart_count}, Container ID: {container_id}")
        
        print(f"{'='*60}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Spawn and manage multiple worker containers using Docker")
    parser.add_argument("-n", "--workers", type=int, default=4, help="Number of worker containers to spawn")
    parser.add_argument("-i", "--image", default="llm_gateway-worker", help="Docker image name")
    parser.add_argument("--no-restart", action="store_true", help="Disable auto-restart on worker failure")
    parser.add_argument("--check-interval", type=float, default=5.0, help="Health check interval in seconds")
    parser.add_argument("--status-interval", type=float, default=30.0, help="Status report interval in seconds")
    parser.add_argument("-f", "--compose-file", default="docker-compose.yml", help="Path to docker-compose.yml")
    
    args = parser.parse_args()
    
    manager = WorkerManager(
        num_workers=args.workers,
        image_name=args.image,
        auto_restart=not args.no_restart,
        compose_file=args.compose_file
    )
    
    manager.run(
        check_interval=args.check_interval,
        status_interval=args.status_interval
    )


if __name__ == "__main__":
    main()

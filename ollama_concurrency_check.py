import os, sys, time
from concurrent.futures import ThreadPoolExecutor
import httpx
from dotenv import load_dotenv

load_dotenv()
KEYS = [k.strip() for k in os.environ["OLLAMA_API_KEY"].split(",") if k.strip()]
URL = "https://ollama.com/v1/chat/completions"
MODEL = "gemma4:cloud"
MAX_N = 15          # test 1..MAX_N parallel requests
COOLDOWN = 10      # seconds between rounds

# long request: holds a slot for a few seconds
LONG = {"model": MODEL, "max_tokens": 300,
        "messages": [{"role": "user", "content": "Write a 200 word story about a robot."}]}
# tiny probe: used to detect when a slot frees up
PROBE = {"model": MODEL, "max_tokens": 1,
         "messages": [{"role": "user", "content": "hi"}]}

printed_headers = False

def post(key, payload):
    return httpx.post(URL, json=payload, timeout=120,
                      headers={"Authorization": f"Bearer {key}"})

def worker(key, i, t0):
    global printed_headers
    r = post(key, LONG)
    done = time.time() - t0
    info = {"i": i, "status": r.status_code, "done": done,
            "retry_after": r.headers.get("retry-after"), "freed_at": None, "probes": 0}
    if r.status_code == 429:
        if not printed_headers:
            printed_headers = True
            print("   [first 429] headers:", dict(r.headers))
            print("   [first 429] body:", r.text[:300])
        # probe every 0.5s until we stop getting 429
        while time.time() - t0 < 120:
            time.sleep(0.5)
            info["probes"] += 1
            if post(key, PROBE).status_code != 429:
                info["freed_at"] = time.time() - t0
                break
    return info

def run_key(key_idx):
    key = KEYS[key_idx]
    print(f"\n=== key #{key_idx} (…{key[-4:]}) ===")
    for n in range(1, MAX_N + 1):
        t0 = time.time()
        with ThreadPoolExecutor(n) as ex:
            results = list(ex.map(lambda i: worker(key, i, t0), range(n)))
        ok = [r for r in results if r["status"] == 200]
        bad = [r for r in results if r["status"] != 200]
        print(f"\nn={n}: {len(ok)} ok, {len(bad)} failed")
        for r in sorted(results, key=lambda r: r["done"]):
            extra = ""
            if r["status"] == 429:
                extra = (f" retry-after={r['retry_after']} "
                         f"slot_freed_at={r['freed_at'] and round(r['freed_at'], 1)}s "
                         f"({r['probes']} probes)")
            print(f"   req{r['i']}: {r['status']} finished at {r['done']:.1f}s{extra}")
        time.sleep(COOLDOWN)

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "0"
    for idx in (range(len(KEYS)) if arg == "all" else [int(arg)]):
        run_key(idx)

=== key #0 (…E-7w) ===

n=1: 1 ok, 0 failed
   req0: 200 finished at 2.6s

n=2: 2 ok, 0 failed
   req1: 200 finished at 1.7s
   req0: 200 finished at 3.8s

n=3: 3 ok, 0 failed
   req2: 200 finished at 1.6s
   req0: 200 finished at 3.4s
   req1: 200 finished at 5.7s

n=4: 4 ok, 0 failed
   req2: 200 finished at 1.8s
   req1: 200 finished at 3.4s
   req0: 200 finished at 7.5s
   req3: 200 finished at 9.2s

n=5: 5 ok, 0 failed
   req2: 200 finished at 3.3s
   req1: 200 finished at 4.8s
   req3: 200 finished at 6.6s
   req0: 200 finished at 8.4s
   req4: 200 finished at 9.6s

n=6: 6 ok, 0 failed
   req3: 200 finished at 2.4s
   req0: 200 finished at 4.3s
   req4: 200 finished at 5.9s
   req5: 200 finished at 7.7s
   req1: 200 finished at 9.1s
   req2: 200 finished at 13.3s

 Thu  8 Oct - 04:05  ~/PROJECTS/llm_gateway   origin ☊ main 1⚙ 1☀ 
 @anon  uv run script.py

=== key #0 (…E-7w) ===

n=1: 1 ok, 0 failed
   req0: 200 finished at 2.8s

n=2: 2 ok, 0 failed
   req0: 200 finished at 3.0s
   req1: 200 finished at 4.6s

n=3: 3 ok, 0 failed
   req1: 200 finished at 1.6s
   req0: 200 finished at 3.1s
   req2: 200 finished at 6.6s

n=4: 4 ok, 0 failed
   req0: 200 finished at 1.7s
   req3: 200 finished at 3.6s
   req1: 200 finished at 5.1s
   req2: 200 finished at 6.7s

n=5: 5 ok, 0 failed
   req1: 200 finished at 2.4s
   req2: 200 finished at 3.9s
   req4: 200 finished at 6.2s
   req0: 200 finished at 8.1s
   req3: 200 finished at 11.9s

n=6: 6 ok, 0 failed
   req3: 200 finished at 1.6s
   req0: 200 finished at 3.6s
   req4: 200 finished at 5.8s
   req2: 200 finished at 7.0s
   req1: 200 finished at 8.6s
   req5: 200 finished at 10.0s
   [first 429] headers: {'content-type': 'application/json', 'retry-after': '14', 'x-build-commit': 'f2926315eed18fb6baf6be6d4cd8034b717b0af5', 'x-build-time': '2026-10-07T13:21:32-07:00', 'x-frame-options': 'DENY', 'x-ratelimit-active': '1', 'x-ratelimit-max-concurrent': '1', 'x-ratelimit-queue-limit': '5', 'x-ratelimit-queued': '5', 'x-request-id': '330d7b81-59b1-4e19-86fe-a669f498239c', 'content-length': '41', 'date': 'Wed, 07 Oct 2026 22:43:05 GMT', 'server': 'Google Frontend', 'traceparent': '00-3f8a407cf78834ff727c8172961a83c3-8bd46c2b21f6e826-00', 'x-cloud-trace-context': '3f8a407cf78834ff727c8172961a83c3/10075797198843865126', 'via': '1.1 google', 'alt-svc': 'h3=":443"; ma=2592000,h3-29=":443"; ma=2592000'}
   [first 429] body: {"error":"too many concurrent requests"}


n=7: 6 ok, 1 failed
   req4: 429 finished at 1.3s retry-after=14 slot_freed_at=10.3s (1 probes)
   req6: 200 finished at 2.3s
   req0: 200 finished at 3.9s
   req3: 200 finished at 5.4s
   req1: 200 finished at 7.0s
   req5: 200 finished at 8.6s
   req2: 200 finished at 9.9s

n=8: 6 ok, 2 failed
   req1: 429 finished at 1.3s retry-after=12 slot_freed_at=11.0s (1 probes)
   req0: 429 finished at 1.6s retry-after=13 slot_freed_at=11.4s (2 probes)
   req2: 200 finished at 1.7s
   req4: 200 finished at 3.9s
   req7: 200 finished at 5.8s
   req5: 200 finished at 7.6s
   req3: 200 finished at 9.1s
   req6: 200 finished at 10.4s

n=9: 6 ok, 3 failed
   req1: 429 finished at 1.3s retry-after=12 slot_freed_at=11.9s (2 probes)
   req5: 429 finished at 1.3s retry-after=20 slot_freed_at=11.2s (1 probes)
   req2: 429 finished at 1.3s retry-after=19 slot_freed_at=12.4s (3 probes)
   req6: 200 finished at 1.8s
   req3: 200 finished at 3.5s
   req4: 200 finished at 5.0s
   req7: 200 finished at 6.4s
   req8: 200 finished at 8.2s
   req0: 200 finished at 10.7s

n=10: 6 ok, 4 failed
   req5: 429 finished at 0.4s retry-after=15 slot_freed_at=14.7s (1 probes)
   req0: 429 finished at 1.4s retry-after=12 slot_freed_at=16.0s (8 probes)
   req7: 429 finished at 1.4s retry-after=17 slot_freed_at=15.2s (4 probes)
   req2: 429 finished at 1.4s retry-after=15 slot_freed_at=15.6s (5 probes)
   req8: 200 finished at 1.8s
   req3: 200 finished at 7.1s
   req9: 200 finished at 9.0s
   req4: 200 finished at 10.9s
   req6: 200 finished at 12.7s
   req1: 200 finished at 14.4s

n=11: 6 ok, 5 failed
   req7: 429 finished at 1.3s retry-after=11 slot_freed_at=14.6s (5 probes)
   req3: 429 finished at 1.3s retry-after=14 slot_freed_at=13.0s (1 probes)
   req0: 429 finished at 1.3s retry-after=15 slot_freed_at=13.8s (4 probes)
   req1: 429 finished at 1.4s retry-after=17 slot_freed_at=13.4s (2 probes)
   req9: 429 finished at 1.5s retry-after=13 slot_freed_at=14.2s (4 probes)
   req10: 200 finished at 2.5s
   req4: 200 finished at 4.4s
   req6: 200 finished at 6.3s
   req5: 200 finished at 7.7s
   req8: 200 finished at 9.3s
   req2: 200 finished at 12.4s

n=12: 6 ok, 6 failed
   req10: 429 finished at 1.3s retry-after=14 slot_freed_at=23.5s (12 probes)
   req4: 429 finished at 1.3s retry-after=13 slot_freed_at=22.4s (9 probes)
   req2: 429 finished at 1.3s retry-after=18 slot_freed_at=22.8s (12 probes)
   req7: 429 finished at 1.3s retry-after=19 slot_freed_at=23.2s (13 probes)
   req8: 429 finished at 1.3s retry-after=11 slot_freed_at=22.0s (7 probes)
   req9: 429 finished at 1.3s retry-after=20 slot_freed_at=21.5s (1 probes)
   req0: 200 finished at 1.8s
   req6: 200 finished at 11.8s
   req3: 200 finished at 15.5s
   req1: 200 finished at 17.1s
   req11: 200 finished at 18.6s
   req5: 200 finished at 20.8s

n=13: 6 ok, 7 failed
   req6: 429 finished at 1.4s retry-after=13 slot_freed_at=14.0s (3 probes)
   req0: 429 finished at 1.4s retry-after=10 slot_freed_at=16.1s (8 probes)
   req8: 429 finished at 1.4s retry-after=18 slot_freed_at=13.2s (1 probes)
   req12: 429 finished at 1.4s retry-after=15 slot_freed_at=14.7s (5 probes)
   req4: 429 finished at 1.4s retry-after=14 slot_freed_at=13.6s (2 probes)
   req2: 429 finished at 1.4s retry-after=14 slot_freed_at=15.5s (7 probes)
   req7: 429 finished at 1.5s retry-after=14 slot_freed_at=14.3s (4 probes)
   req5: 200 finished at 2.2s
   req1: 200 finished at 3.8s
   req3: 200 finished at 5.3s
   req10: 200 finished at 7.9s
   req11: 200 finished at 10.1s
   req9: 200 finished at 12.7s

n=14: 6 ok, 8 failed
   req2: 429 finished at 1.3s retry-after=20 slot_freed_at=11.4s (2 probes)
   req9: 429 finished at 1.3s retry-after=15 slot_freed_at=10.4s (1 probes)
   req5: 429 finished at 1.3s retry-after=14 slot_freed_at=11.9s (4 probes)
   req1: 429 finished at 1.3s retry-after=20 slot_freed_at=13.1s (6 probes)
   req12: 429 finished at 1.3s retry-after=20 slot_freed_at=13.5s (6 probes)
   req6: 429 finished at 1.3s retry-after=16 slot_freed_at=12.2s (5 probes)
   req4: 429 finished at 1.3s retry-after=14 slot_freed_at=10.9s (1 probes)
   req0: 429 finished at 1.3s retry-after=11 slot_freed_at=12.7s (6 probes)
   req7: 200 finished at 1.7s
   req10: 200 finished at 3.0s
   req13: 200 finished at 4.4s
   req8: 200 finished at 6.0s
   req11: 200 finished at 7.8s
   req3: 200 finished at 10.0s
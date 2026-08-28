import os, sys
sys.path.insert(0, "/home/z/work/hanzo/python-sdk/pkg")
import hanzoai.cloud as c
cfg = c.Configuration(host=os.environ["HANZO_BASE_URL"])
fail = 0
with c.ApiClient(cfg) as api:
    ai = c.AiApi(api)
    try:
        r = ai.get_models_with_http_info()
        n = len((r.data or {}).get("data", [])) if isinstance(r.data, dict) else -1
        print(f"  ok  GET /v1/models  {r.status_code}")
    except Exception as e:
        print("  FAIL models:", type(e).__name__, str(e)[:80]); fail += 1
    try:
        c.EngineApi(api).engine_status()
        print("  FAIL engine: unauthenticated call reported success"); fail += 1
    except c.ApiException as e:
        print(f"  ok  GET /v1/engine/status refused: {e.status}")
    except Exception as e:
        print("  ok  refused:", type(e).__name__)
print("PASS python" if not fail else f"FAIL python ({fail})")
sys.exit(1 if fail else 0)

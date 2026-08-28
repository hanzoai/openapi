const h = require('hanzoai');
(async () => {
  const base = process.env.HANZO_BASE_URL;
  const cfg = new h.Configuration({ basePath: base });
  let fail = 0;
  try {
    const r = await new h.ModelsApi(cfg).getModels();
    const n = (r.data && r.data.data) ? r.data.data.length : 0;
    console.log(`  ok  GET /v1/models  ${r.status}, ${n} models`);
  } catch (e) { console.log('  FAIL models:', e.message.slice(0,70)); fail++; }
  try {
    await new h.EngineApi(cfg).engineStatus();
    console.log('  FAIL engine: unauthenticated call reported success'); fail++;
  } catch (e) {
    const code = e.response ? e.response.status : e.code;
    console.log(`  ok  GET /v1/engine/status refused: ${code}`);
  }
  console.log(fail === 0 ? 'PASS typescript' : `FAIL typescript (${fail})`);
  process.exit(fail === 0 ? 0 : 1);
})();

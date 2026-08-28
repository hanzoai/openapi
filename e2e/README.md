# e2e — the clients against a real cloud

`generate.py --check` proves a client is the projection of the document.
A compile proves it is well-formed Go, Dart, PHP. Neither proves it can reach a
server, decode a body, or turn a refusal into an error.

That last one is the trap. An SDK that swallows a 403 and hands back a zero
value is indistinguishable from one that works, right up until production. So
every probe asserts the same two things, in each language:

  1. `GET /v1/models` answers 200 and the body decodes to a non-empty list.
  2. `GET /v1/engine/status` — which needs a caller who is signed in — comes
     back as an ERROR carrying 403, not as an empty success.

    ./run.sh                                   # against the local cloud
    HANZO_BASE_URL=https://api.hanzo.ai ./run.sh

Both are read-only GETs. The probe never writes.

## What it found the first time it ran

The same operation does not live in the same place in every client. `GET
/v1/models` is `AiAPI.GetModels` in Go and `ai_api::get_models` in Rust, but
`ModelsApi.getModels` in TypeScript — one document, three groupings. Nothing
catches that except calling it.

## Not covered

java and kotlin need a jar on the classpath, swift needs macOS, cpp needs a
build. They are exercised by hand today; adding them here needs a toolchain
step, not another probe.

The probes are unauthenticated, so they cover transport, routing, decoding and
the refusal path — not an authorised round trip. Anything past a 403 needs a
credential this harness deliberately does not hold.

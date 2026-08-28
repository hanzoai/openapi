// e2e: the Go client against the LOCAL cloud.
//
// It asserts the three things a generated client owes that a compile cannot
// show: it reaches the server, it decodes a real body, and it surfaces a
// refusal as an error rather than as an empty success.
package main

import (
	"context"
	"fmt"
	"os"

	hanzoai "github.com/hanzoai/go-sdk/v8"
)

func main() {
	cfg := hanzoai.NewConfiguration()
	cfg.Servers = hanzoai.ServerConfigurations{{URL: os.Getenv("HANZO_BASE_URL")}}
	api := hanzoai.NewAPIClient(cfg)
	ctx := context.Background()
	fail := 0

	// 1. reaches the server, and the answer arrives TYPED.
	//
	// This used to read resp.Body and hand-decode an anonymous struct, because
	// there was nothing else to do: the document declared no response for this
	// address, so the generator gave GetModels a bare *http.Response and the
	// caller had to know the shape by heart. Reading through the generated type
	// is the assertion — it only compiles if the shape crossed from ai, through
	// cloud's relay, into the document this client was projected from.
	models, resp, err := api.AiAPI.GetModels(ctx).Execute()
	switch {
	case err != nil || resp.StatusCode != 200:
		fmt.Println("  FAIL models:", err)
		fail++
	case models == nil || len(models.Data) == 0:
		fmt.Println("  FAIL models: decoded to an empty catalogue")
		fail++
	default:
		first := models.Data[0]
		fmt.Printf("  ok  GET /v1/models  200, object=%s, %d models, first=%s owned_by=%s\n",
			models.GetObject(), len(models.Data), first.GetId(), first.GetOwnedBy())
	}

	// 2. a refusal is an ERROR, not an empty success — the trap a compile misses
	_, _, err = api.EngineAPI.EngineStatus(ctx).Execute()
	if err == nil {
		fmt.Println("  FAIL engine: unauthenticated call reported success")
		fail++
	} else {
		var oa *hanzoai.GenericOpenAPIError
		if ok := asGeneric(err, &oa); ok {
			fmt.Printf("  ok  GET /v1/engine/status refused, decoded: %s\n", firstLine(string(oa.Body())))
		} else {
			fmt.Printf("  ok  GET /v1/engine/status refused: %v\n", err)
		}
	}

	if fail > 0 {
		fmt.Printf("FAIL go (%d)\n", fail)
		os.Exit(1)
	}
	fmt.Println("PASS go")
}

func asGeneric(err error, out **hanzoai.GenericOpenAPIError) bool {
	if e, ok := err.(hanzoai.GenericOpenAPIError); ok {
		*out = &e
		return true
	}
	return false
}

func firstLine(s string) string {
	if len(s) > 90 {
		return s[:90]
	}
	return s
}

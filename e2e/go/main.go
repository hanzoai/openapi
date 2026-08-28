// e2e: the Go client against the LOCAL cloud.
//
// It asserts the three things a generated client owes that a compile cannot
// show: it reaches the server, it decodes a real body, and it surfaces a
// refusal as an error rather than as an empty success.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"

	hanzoai "github.com/hanzoai/go-sdk/v8"
)

func main() {
	cfg := hanzoai.NewConfiguration()
	cfg.Servers = hanzoai.ServerConfigurations{{URL: os.Getenv("HANZO_BASE_URL")}}
	api := hanzoai.NewAPIClient(cfg)
	ctx := context.Background()
	fail := 0

	// 1. reaches the server and the body decodes
	resp, err := api.AiAPI.GetModels(ctx).Execute()
	if err != nil || resp.StatusCode != 200 {
		fmt.Println("  FAIL models:", err)
		fail++
	} else {
		body, _ := io.ReadAll(resp.Body)
		var doc struct {
			Data []struct {
				ID string `json:"id"`
			} `json:"data"`
		}
		if json.Unmarshal(body, &doc) != nil || len(doc.Data) == 0 {
			fmt.Println("  FAIL models: body did not decode")
			fail++
		} else {
			fmt.Printf("  ok  GET /v1/models  200, %d models, first=%s\n", len(doc.Data), doc.Data[0].ID)
		}
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

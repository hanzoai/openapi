import ai.hanzo.cloud.*;
import ai.hanzo.cloud.api.*;

public class E2E {
    public static void main(String[] a) throws Exception {
        int fail = 0;
        ApiClient c = new ApiClient();
        c.setBasePath(System.getenv("HANZO_BASE_URL"));
        try {
            ApiResponse<?> r = new ModelsApi(c).getModelsWithHttpInfo();
            System.out.println("  ok  GET /v1/models  " + r.getStatusCode());
        } catch (ApiException e) {
            System.out.println("  FAIL models: " + e.getCode()); fail++;
        }
        try {
            new EngineApi(c).engineStatus();
            System.out.println("  FAIL engine: unauthenticated call reported success"); fail++;
        } catch (ApiException e) {
            System.out.println("  ok  GET /v1/engine/status refused: " + e.getCode());
        }
        System.out.println(fail == 0 ? "PASS java" : "FAIL java (" + fail + ")");
        System.exit(fail == 0 ? 0 : 1);
    }
}

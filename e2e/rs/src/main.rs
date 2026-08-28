use hanzo_client::apis::configuration::Configuration;

#[tokio::main]
async fn main() {
    let mut cfg = Configuration::new();
    cfg.base_path = std::env::var("HANZO_BASE_URL").unwrap();
    let mut fail = 0;

    match hanzo_client::apis::ai_api::get_models(&cfg).await {
        Ok(_) => println!("  ok  GET /v1/models  decoded"),
        Err(e) => { println!("  FAIL models: {e}"); fail += 1; }
    }
    match hanzo_client::apis::engine_api::engine_status(&cfg).await {
        Ok(_) => { println!("  FAIL engine: unauthenticated call reported success"); fail += 1; }
        Err(e) => println!("  ok  GET /v1/engine/status refused: {}", &format!("{e}")[..40.min(format!("{e}").len())]),
    }
    println!("{}", if fail == 0 { "PASS rust" } else { "FAIL rust" });
    std::process::exit(if fail == 0 { 0 } else { 1 });
}

$LOAD_PATH.unshift '/home/z/work/hanzo/ruby-sdk/lib'
require 'hanzoai'
base = ENV.fetch('HANZO_BASE_URL')
Hanzoai.configure { |c| c.host = base.sub(%r{^https?://}, ''); c.scheme = base.start_with?('https') ? 'https' : 'http' }
fail = 0
begin
  _, code, = Hanzoai::AiApi.new.get_models_with_http_info
  puts "  ok  GET /v1/models  #{code}"
rescue => e
  puts "  FAIL models: #{e.class}: #{e.message[0,70]}"; fail += 1
end
begin
  Hanzoai::EngineApi.new.engine_status
  puts "  FAIL engine: unauthenticated call reported success"; fail += 1
rescue Hanzoai::ApiError => e
  puts "  ok  GET /v1/engine/status refused: #{e.code}"
rescue => e
  puts "  ok  refused: #{e.class}"
end
puts(fail.zero? ? 'PASS ruby' : "FAIL ruby (#{fail})")
exit(fail.zero? ? 0 : 1)

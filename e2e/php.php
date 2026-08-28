<?php
require '/home/z/work/hanzo/php-sdk/vendor/autoload.php';
$base = getenv('HANZO_BASE_URL');
$cfg = Hanzo\Cloud\Configuration::getDefaultConfiguration()->setHost($base);
$http = new GuzzleHttp\Client(['http_errors' => false]);
$fail = 0;
try {
    $r = (new Hanzo\Cloud\Api\AiApi($http, $cfg))->getModelsWithHttpInfo();
    echo "  ok  GET /v1/models  {$r[1]}\n";
} catch (Throwable $e) { echo "  FAIL models: ".get_class($e)."\n"; $fail++; }
try {
    (new Hanzo\Cloud\Api\EngineApi($http, $cfg))->engineStatus();
    echo "  FAIL engine: unauthenticated call reported success\n"; $fail++;
} catch (Hanzo\Cloud\ApiException $e) {
    echo "  ok  GET /v1/engine/status refused: {$e->getCode()}\n";
} catch (Throwable $e) { echo "  ok  refused: ".get_class($e)."\n"; }
echo $fail === 0 ? "PASS php\n" : "FAIL php ($fail)\n";
exit($fail === 0 ? 0 : 1);

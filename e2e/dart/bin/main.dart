import 'dart:io';
import 'package:hanzoai/hanzoai.dart';

Future<void> main() async {
  final base = Platform.environment['HANZO_BASE_URL']!;
  final client = ApiClient(basePath: base);
  var fail = 0;
  try {
    final r = await AiApi(client).getModelsWithHttpInfo();
    print('  ok  GET /v1/models  ${r.statusCode}');
  } catch (e) {
    print('  FAIL models: $e'); fail++;
  }
  try {
    await EngineApi(client).engineStatus();
    print('  FAIL engine: unauthenticated call reported success'); fail++;
  } on ApiException catch (e) {
    print('  ok  GET /v1/engine/status refused: ${e.code}');
  } catch (e) {
    print('  ok  refused: ${e.runtimeType}');
  }
  print(fail == 0 ? 'PASS dart' : 'FAIL dart ($fail)');
  exit(fail == 0 ? 0 : 1);
}

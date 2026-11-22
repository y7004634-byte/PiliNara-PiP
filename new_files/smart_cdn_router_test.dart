import 'package:PiliPlus/models/common/video/cdn_type.dart';
import 'package:PiliPlus/utils/smart_cdn_router.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('no recent samples retains deterministic backup order', () {
    expect(SmartCdnRouter.rankForMetrics({}), [
      CDNService.backupUrl,
      CDNService.hw_08c,
      CDNService.ali,
      CDNService.cos,
      CDNService.akamai,
    ]);
  });

  test('verified faster CDN wins over untested fallback', () {
    final order = SmartCdnRouter.rankForMetrics({
      CDNService.hw_08c: 480,
      CDNService.ali: 40,
      CDNService.cos: 160,
    });
    expect(order.take(3), [
      CDNService.ali,
      CDNService.cos,
      CDNService.hw_08c,
    ]);
    expect(order[3], CDNService.backupUrl);
  });

  test('recently failed CDN is demoted despite fast historic sample', () {
    final order = SmartCdnRouter.rankForMetrics(
      {
        CDNService.ali: 20,
        CDNService.cos: 120,
      },
      cooldown: {CDNService.ali},
    );
    expect(order.first, CDNService.cos);
    expect(order.last, CDNService.ali);
  });

  test('two failures do not reshuffle other validated winners', () {
    final order = SmartCdnRouter.rankForMetrics(
      {
        CDNService.akamai: 60,
        CDNService.hw_08c: 55,
        CDNService.cos: 90,
      },
      cooldown: {CDNService.hw_08c, CDNService.backupUrl},
    );
    expect(order.first, CDNService.akamai);
    expect(order[1], CDNService.cos);
    expect(order.last, CDNService.hw_08c);
  });
}

#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

def edit(rel, old, new):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"patch anchor not found: {rel}")
    p.write_text(s.replace(old, new, 1))

p = root / "Door581Probe/ProbeBridge.js"
s = p.read_text()
s = s.replace(
"  const safeRead = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };\n",
"  const safeRead = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };\n"
"  const safeSessionRead = key => { try { return sessionStorage.getItem(key); } catch (_) { return null; } };\n"
"  const safeSessionWrite = (key,value) => { try { sessionStorage.setItem(key,value); return true; } catch (_) { return false; } };\n"
"  const safeSessionRemove = key => { try { sessionStorage.removeItem(key); } catch (_) {} };\n",
1)

old = """  async function receiveIntent(intent) {
    if (!intent || typeof intent.id!=='string' || !Number.isFinite(intent.lat) || !Number.isFinite(intent.lng)
      || intent.lat<20 || intent.lat>27 || intent.lng<117 || intent.lng>123) return {ok:false,error:'invalid_intent'};
    if(!api()?.setDestination)return {ok:false,error:'web_not_ready'};
    const serial=++deliverySerial;
    latestIntent=intent;directMailboxBlocked=true;
    // No reload; use the real exported application entry point, not a separate fake Pin.
    if(!appliedIDs.has(intent.id)){
      api().setDestination({lat:intent.lat,lng:intent.lng},{fit:true,persist:true,stableUrl:true});
      appliedIDs.add(intent.id);
    }
    // Give the app's queued rendering task a turn; this ACK is data acceptance,
    // not a claim that network route computation or every tile has completed.
    await new Promise(resolve=>setTimeout(resolve,100));
    if(serial!==deliverySerial || latestIntent.id!==intent.id)return {ok:false,error:'superseded',id:intent.id};
    const raw=point(safeRead('581-door-dest-raw'));
    if(!equals(raw,intent))return {ok:false,error:'destination_readback_mismatch',id:intent.id,raw};
    const ack={ok:true,id:intent.id,rawDestination:raw,effectiveDestination:point(safeRead('581-door-dest')),
      routeStatus:text('routeStatus'),sceneStatus:text('mainSceneStatus'),documentID,
      elapsedMS:Date.now()-Number(intent.receivedAt),ackMeaning:'destination-applied; route-not-yet-asserted'};
    lastACK=ack;send('destination_ack',ack);return ack;
  }
"""
new = """  function siteBooted() {
    if (api()?.setDestination) return true;
    const body=document.body;
    return !!body && !!body.dataset?.webapp && !!body.dataset?.theme
      && !!document.getElementById('routeStatus') && !!document.getElementById('gpsState');
  }
  function makeACK(intent, mode) {
    const raw=point(safeRead('581-door-dest-raw'));
    const effective=point(safeRead('581-door-dest'));
    if(!equals(raw,intent) || !equals(effective,intent)) return null;
    const ack={ok:true,id:intent.id,rawDestination:raw,effectiveDestination:effective,
      routeStatus:text('routeStatus'),sceneStatus:text('mainSceneStatus'),documentID,
      elapsedMS:Date.now()-Number(intent.receivedAt),deliveryMode:mode,
      ackMeaning:'destination-applied; route-not-yet-asserted'};
    lastACK=ack;safeSessionRemove('door581-probe-fallback-id');send('destination_ack',ack);return ack;
  }
  async function receiveIntent(intent) {
    if (!intent || typeof intent.id!=='string' || !Number.isFinite(intent.lat) || !Number.isFinite(intent.lng)
      || intent.lat<20 || intent.lat>27 || intent.lng<117 || intent.lng>123) return {ok:false,error:'invalid_intent'};
    if(!siteBooted())return {ok:false,error:'web_not_ready'};
    const serial=++deliverySerial;
    latestIntent=intent;directMailboxBlocked=true;
    if(api()?.setDestination){
      if(!appliedIDs.has(intent.id)){
        api().setDestination({lat:intent.lat,lng:intent.lng},{fit:true,persist:true,stableUrl:true});
        appliedIDs.add(intent.id);
      }
      await new Promise(resolve=>setTimeout(resolve,100));
      if(serial!==deliverySerial || latestIntent.id!==intent.id)return {ok:false,error:'superseded',id:intent.id};
      const ack=makeACK(intent,'api');
      return ack || {ok:false,error:'destination_readback_mismatch',id:intent.id,raw:point(safeRead('581-door-dest-raw'))};
    }
    const afterReload=makeACK(intent,'url-reload');
    if(afterReload)return afterReload;
    const marker=safeSessionRead('door581-probe-fallback-id');
    if(marker===intent.id)return {ok:false,error:'reload_fallback_not_applied',id:intent.id};
    safeSessionWrite('door581-probe-fallback-id',intent.id);
    const u=new URL(location.href);
    u.searchParams.set('dest',`${intent.lat.toFixed(6)},${intent.lng.toFixed(6)}`);
    u.searchParams.delete('rawDest');u.searchParams.delete('gmap');u.hash='';
    setTimeout(()=>{ location.href=u.toString(); },25);
    return {ok:false,error:'reload_fallback_started',id:intent.id};
  }
"""
if old not in s:
    raise SystemExit("ProbeBridge receiveIntent anchor missing")
s = s.replace(old, new, 1)
s = s.replace(
"    if(api()?.setDestination){\n      clearInterval(timer);ready=true;\n      send('web_ready',{siteVersion:api().VERSION,elapsedMS:Math.round(performance.now()-startedAt)});",
"    if(siteBooted()){\n      clearInterval(timer);ready=true;\n      send('web_ready',{siteVersion:api()?.VERSION||null,readyMode:api()?.setDestination?'api':'dom-fallback',elapsedMS:Math.round(performance.now()-startedAt)});",
1)
s = s.replace(
"    }else if(++attempt>=120){clearInterval(timer);send('web_ready_timeout',{elapsedMS:Math.round(performance.now()-startedAt)});}",
"    }else if(++attempt>=180){clearInterval(timer);send('web_ready_timeout',{elapsedMS:Math.round(performance.now()-startedAt)});}",
1)
p.write_text(s)

p = root / "Door581Probe/ProbeViewController.swift"
s = p.read_text()
s = s.replace('nativeProbe", value: "001"', 'nativeProbe", value: "002"')
s = s.replace('Door581Probe/0.0.1', 'Door581Probe/0.0.2')
s = s.replace('withTimeInterval: 25, repeats: false', 'withTimeInterval: 45, repeats: false', 1)
s = s.replace('581 Probe 0.0.1', '581 Probe 0.0.2')
old = """                if let ack = data as? [String: Any], ack["ok"] as? Bool == true, ack["id"] as? String == p.id {
                    self.acceptACK(ack)
                } else {
                    self.log("destination_not_acknowledged", ["id": p.id, "response": data])
                    if self.queue.pending?.id == p.id { self.setStatus("座標已保存，但網頁尚未確認接收；按「測試 → 重試傳送」。", error: true) }
                }
"""
new = """                if let ack = data as? [String: Any], ack["ok"] as? Bool == true, ack["id"] as? String == p.id {
                    self.acceptACK(ack)
                } else if let reply = data as? [String: Any], reply["error"] as? String == "reload_fallback_started" {
                    self.log("destination_reload_fallback", ["id": p.id])
                    self.setStatus("目的地已保存；正在用同站網址重新套用座標…")
                } else {
                    self.log("destination_not_acknowledged", ["id": p.id, "response": data])
                    if self.queue.pending?.id == p.id { self.setStatus("座標已保存，但網頁尚未確認接收；按「測試 → 重試傳送」。", error: true) }
                }
"""
if old not in s:
    raise SystemExit("ProbeViewController ACK anchor missing")
p.write_text(s.replace(old, new, 1))

for rel in ["Door581Probe/Info.plist", "tools/build_ipa.sh", "tools/generate_project.py"]:
    p = root / rel
    p.write_text(p.read_text().replace("0.0.1", "0.0.2"))

p = root / "Tests/bridge.test.mjs"
s = p.read_text()
s = s.replace(
"function world({origin='https://rider-door-map-canary.pages.dev',ready=true,fetchImpl,storage}={}){",
"function world({origin='https://rider-door-map-canary.pages.dev',ready=true,domBooted=false,fetchImpl,storage}={}){",1)
s = s.replace(
"  const records=[],kv=new Map(),timers=[],geoCallbacks=new Map(),listeners=new Map();",
"  const records=[],kv=new Map(),skv=new Map(),timers=[],geoCallbacks=new Map(),listeners=new Map();",1)
s = s.replace(
"    document:{getElementById:id=>els.get(id)||null},",
"    document:{getElementById:id=>els.get(id)||null,body:domBooted?{dataset:{webapp:'standalone',theme:'dark'}}:{dataset:{}}},",1)
s = s.replace(
"    localStorage:{getItem:k=>kv.get(k)??null,setItem:(k,v)=>kv.set(k,String(v)),removeItem:k=>kv.delete(k)},",
"    localStorage:{getItem:k=>kv.get(k)??null,setItem:(k,v)=>kv.set(k,String(v)),removeItem:k=>kv.delete(k)},\n    sessionStorage:{getItem:k=>skv.get(k)??null,setItem:(k,v)=>skv.set(k,String(v)),removeItem:k=>skv.delete(k)},",1)
s = s.replace(
"  return {g,records,kv,els,site,geoCallbacks,listeners,timers,get persistCalls(){return persistCalls},get routeCalls(){return routeCalls}};",
"  return {g,records,kv,skv,els,site,geoCallbacks,listeners,timers,get persistCalls(){return persistCalls},get routeCalls(){return routeCalls}};",1)
anchor = """test('cold delivery before ready returns explicit unready and does not acknowledge',async()=>{
  const w=world({ready:false});const r=await w.g.__door581Probe.receiveIntent(intent('cold'));
  assert.equal(r.ok,false);assert.equal(r.error,'web_not_ready');
});
"""
extra = """test('visibly booted real Door Map can use DOM readiness fallback when export is unavailable',()=>{
  const w=world({ready:false,domBooted:true});w.timers[0]();
  const r=w.records.find(x=>x.type==='web_ready');assert.ok(r);assert.equal(r.readyMode,'dom-fallback');
});
test('DOM fallback performs at most one same-origin reload then ACKs readback',async()=>{
  const w=world({ready:false,domBooted:true});const p=intent('reload',24.16496,120.643653);
  const first=await w.g.__door581Probe.receiveIntent(p);assert.equal(first.error,'reload_fallback_started');
  await new Promise(r=>setTimeout(r,35));assert.match(w.g.location.href,/dest=24\\.164960%2C120\\.643653/);
  w.kv.set('581-door-dest-raw',`${p.lat},${p.lng}`);w.kv.set('581-door-dest',`${p.lat},${p.lng}`);
  const second=await w.g.__door581Probe.receiveIntent(p);assert.equal(second.ok,true);assert.equal(second.deliveryMode,'url-reload');
  assert.equal(w.skv.get('door581-probe-fallback-id'),undefined);
});
"""
if anchor not in s:
    raise SystemExit("bridge test anchor missing")
p.write_text(s.replace(anchor, anchor + extra, 1))

print("v0.0.2 patch applied")

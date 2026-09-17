#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${WINGMAN_TEST_STATE:-$(mktemp -d "${TMPDIR:-/tmp}/wingman-harness.XXXXXX")}"
TRACE="$STATE/stub-trace.jsonl"
WORK="$STATE/work"
JOURNAL="$STATE/journal.md"
HARNESS="$STATE/harness.mjs"

mkdir -p "$STATE" "$WORK"
touch "$TRACE"

cat > "$HARNESS" <<'JS'
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'fs'
import { join } from 'path'
const pluginDir=process.env.PLUGIN_DIR,state=process.env.WINGMAN_STATE_DIR,tracePath=process.env.OPERATORS_STUB_TRACE,work=process.env.WINGMAN_WORK,journal=process.env.WINGMAN_JOURNAL
let assertions=0
function assert(c,m){ assertions++; if(!c) throw new Error(m) } function text(r){ return r.content?.[0]?.text ?? '' }
function events(){ const raw=readFileSync(tracePath,'utf8').trim(); return raw?raw.split('\n').map(JSON.parse):[] } function last(t){ return events().filter(e=>e.tool===t).at(-1) }
async function rpc(method,params={},timeoutMs=60000){ const input=[JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'wingman-harness',version:'0.0.1'}}}),JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized',params:{}}),JSON.stringify({jsonrpc:'2.0',id:2,method,params})].join('\n')+'\n'; const p=Bun.spawn(['bun','server.bundle.js'],{cwd:pluginDir,stdin:new Blob([input]),stdout:'pipe',stderr:'pipe',env:{...process.env,WINGMAN_TEST_TRANSPORT:'bun-line',WINGMAN_STATE_DIR:state,WINGMAN_CODEX_BIN:join(pluginDir,'test-stubs/codex'),OPERATORS_STUB_TRACE:tracePath}}); let timer; const status=await Promise.race([p.exited.then(()=> 'exited'),new Promise(r=>timer=setTimeout(()=>r('timeout'),timeoutMs))]); clearTimeout(timer); if(status==='timeout'){p.kill();throw new Error(`timeout ${method}`)} const out=await new Response(p.stdout).text(),err=await new Response(p.stderr).text(); if(err.trim())process.stderr.write(err); const resp=out.trim().split('\n').filter(Boolean).map(JSON.parse).find(x=>x.id===2); if(!resp)throw new Error(`missing response ${method}: ${out}`); if(resp.error)throw new Error(resp.error.message); return resp.result }
const callTool=(name,args)=>rpc('tools/call',{name,arguments:args})
const listed=await rpc('tools/list'); assert(listed.tools.some(t=>t.name==='wingman_ask'),'missing ask'); assert(listed.tools.some(t=>t.name==='wingman_sessions'),'missing sessions')
const source=readFileSync(join(pluginDir,'server.ts'),'utf8'); assert(!source.includes("sh', '-c")&&!source.includes("bash', '-c")&&!source.includes('shell: true'),'shell construction found')
mkdirSync(join(state,'sessions'),{recursive:true})
writeFileSync(join(state,'sessions/live-wing.reserved'),JSON.stringify({name:'live-wing',reserved_ts:new Date().toISOString(),pid:process.pid}))
let before=events().filter(e=>e.tool==='codex').length
let res=await callTool('wingman_ask',{session:'live-wing',message:'Blocked create.',new:{cwd:work}}); assert(res.isError&&text(res).includes('session already exists'),'live foreground reservation accepted'); assert(events().filter(e=>e.tool==='codex').length===before,'live reservation spawned')
unlinkSync(join(state,'sessions/live-wing.reserved'))
res=await callTool('wingman_ask',{session:'wing1',message:'Check my conclusion.',mode:'stress-test-my-conclusion',new:{cwd:work,journal},replace:true}); assert(!res.isError,`new failed ${text(res)}`); let ev=last('codex'); assert(ev.cwd===work,'cwd'); assert(ev.stdin.includes('Stress-test my conclusion'),'mode frame'); assert(existsSync(journal)&&readFileSync(journal,'utf8').includes('Check my conclusion.'),'journal')
assert(ev.argv[ev.argv.indexOf('-m')+1]==='gpt-6-astra','fresh wingman must pass -m gpt-6-astra')
assert(ev.argv.includes('model_reasoning_effort=low'),'default effort must remain low')
assert(ev.argv[ev.argv.indexOf('--sandbox')+1]==='workspace-write','sandbox default changed')
assert(!ev.argv.includes('sandbox_workspace_write.network_access=true'),'network default changed')
const recordPath=join(state,'sessions','wing1.json')
assert(JSON.parse(readFileSync(recordPath,'utf8')).model==='gpt-6-astra','fresh registry model must be gpt-6-astra')
res=await callTool('wingman_ask',{session:'wing1',message:'Resume turn.'}); assert(!res.isError,`resume failed ${text(res)}`); ev=last('codex'); assert(ev.argv.includes('resume')&&ev.cwd===work,'resume mechanics')
assert(!ev.argv.includes('-m'),'resume must not introduce a model override')
const legacy=JSON.parse(readFileSync(recordPath,'utf8')); legacy.model='gpt-5.6-sol'; writeFileSync(recordPath,JSON.stringify(legacy))
res=await callTool('wingman_ask',{session:'wing1',message:'Resume legacy turn.'}); assert(!res.isError,`legacy resume failed ${text(res)}`)
assert(JSON.parse(readFileSync(recordPath,'utf8')).model==='gpt-5.6-sol','legacy session record must not be rewritten')
res=await callTool('wingman_ask',{session:'wing-high',message:'Check effort override.',new:{cwd:work,effort:'high'}}); assert(!res.isError,`override failed ${text(res)}`); ev=last('codex')
assert(ev.argv[ev.argv.indexOf('-m')+1]==='gpt-6-astra','effort override must keep Astra model')
assert(ev.argv.includes('model_reasoning_effort=high'),'caller effort override must remain supported')
res=await callTool('wingman_sessions',{}); assert(!res.isError&&text(res).includes('wing1'),'sessions missing')
console.log(`wingman harness: ${assertions} assertions passed / 0 failed / 0 skipped`)
JS

PLUGIN_DIR="$PLUGIN_DIR" WINGMAN_STATE_DIR="$STATE/state" OPERATORS_STUB_TRACE="$TRACE" WINGMAN_WORK="$WORK" WINGMAN_JOURNAL="$JOURNAL" bun "$HARNESS"
echo "Scratch state: $STATE"

#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${OPERATORS_TEST_STATE:-$(mktemp -d "${TMPDIR:-/tmp}/operators-harness.XXXXXX")}"
TRACE="$STATE/stub-trace.jsonl"
WORK="$STATE/work"
BRIEF="$STATE/brief.md"
HARNESS="$STATE/harness.mjs"

mkdir -p "$STATE" "$WORK"
touch "$TRACE"
printf 'Implement the operators plugin test brief.\n' > "$BRIEF"
(cd "$PLUGIN_DIR" && bun test core.guard.test.ts)

cat > "$HARNESS" <<'JS'
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'fs'
import { join } from 'path'
const pluginDir = process.env.PLUGIN_DIR, state = process.env.OPERATORS_STATE_DIR, tracePath = process.env.OPERATORS_STUB_TRACE, work = process.env.OPERATORS_WORK, brief = process.env.OPERATORS_BRIEF
function assert(c,m){ if(!c) throw new Error(m) }
function text(r){ return r.content?.[0]?.text ?? '' }
function events(){ const raw=readFileSync(tracePath,'utf8').trim(); return raw?raw.split('\n').map(JSON.parse):[] }
function last(t){ return events().filter(e=>e.tool===t).at(-1) }
async function rpc(method, params={}, timeoutMs=60000){
  const input=[JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'operators-harness',version:'0.0.1'}}}),JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized',params:{}}),JSON.stringify({jsonrpc:'2.0',id:2,method,params})].join('\n')+'\n'
  const p=Bun.spawn(['bun','server.bundle.js'],{cwd:pluginDir,stdin:new Blob([input]),stdout:'pipe',stderr:'pipe',env:{...process.env,OPERATORS_TEST_TRANSPORT:'bun-line',OPERATORS_STATE_DIR:state,OPERATORS_CODEX_BIN:join(pluginDir,'test-stubs/codex'),OPERATORS_AGY_BIN:join(pluginDir,'test-stubs/agy'),OPERATORS_CURSOR_BIN:join(pluginDir,'test-stubs/cursor-agent'),OPERATORS_STUB_TRACE:tracePath}})
  let timer; const status=await Promise.race([p.exited.then(()=> 'exited'), new Promise(r=>timer=setTimeout(()=>r('timeout'),timeoutMs))]); clearTimeout(timer)
  if(status==='timeout'){ p.kill(); throw new Error(`timeout ${method}`) }
  const out=await new Response(p.stdout).text(), err=await new Response(p.stderr).text(); if(err.trim()) process.stderr.write(err)
  const resp=out.trim().split('\n').filter(Boolean).map(JSON.parse).find(x=>x.id===2); if(!resp) throw new Error(`missing response ${method}: ${out}`); if(resp.error) throw new Error(resp.error.message); return resp.result
}
const callTool=(name,args,timeout)=>rpc('tools/call',{name,arguments:args},timeout)

const listed=await rpc('tools/list')
for(const n of ['codex_plan','codex_exec','codex_implement','codex_critique','codex_result','agy_ask','cursor_ask','operator_sessions']) assert(listed.tools.some(t=>t.name===n),`missing ${n}`)
const agyEffortSchema=listed.tools.find(t=>t.name==='agy_ask')?.inputSchema?.properties?.effort
assert(JSON.stringify(agyEffortSchema?.enum)===JSON.stringify(['low','high']),'agy effort schema must advertise only values accepted by every model')
assert(agyEffortSchema?.description?.includes('gemini-3.5-flash accepts low/medium/high'),'agy effort schema missing per-model detail')
const source=readFileSync(join(pluginDir,'server.ts'),'utf8'); assert(!source.includes("sh', '-c")&&!source.includes("bash', '-c")&&!source.includes('shell: true'),'shell construction found')
mkdirSync(join(state,'sessions'),{recursive:true})
writeFileSync(join(state,'sessions/live-reserved.reserved'),JSON.stringify({name:'live-reserved',reserved_ts:new Date().toISOString(),pid:process.pid}))
let before=events().filter(e=>e.tool==='codex').length
let res=await callTool('codex_plan',{session:'live-reserved',brief_path:brief,cwd:work}); assert(res.isError&&text(res).includes('session already exists'),'live foreground reservation accepted'); assert(events().filter(e=>e.tool==='codex').length===before,'live reservation spawned')
unlinkSync(join(state,'sessions/live-reserved.reserved'))
writeFileSync(join(state,'sessions/dead-reserved.reserved'),JSON.stringify({name:'dead-reserved',reserved_ts:new Date().toISOString(),pid:99999999}))
res=await callTool('codex_plan',{session:'dead-reserved',brief_path:brief,cwd:work}); assert(!res.isError,`dead reservation did not clear ${text(res)}`); assert(existsSync(join(state,'sessions/dead-reserved.json')),'dead reservation session missing')
res=await callTool('codex_plan',{session:'impl1',brief_path:brief,cwd:work,effort:'xhigh'}); assert(!res.isError,`plan failed ${text(res)}`); assert(existsSync(join(state,'sessions/impl1.json')),'session missing')
let ev=last('codex'); assert(ev.cwd===work,'plan cwd'); assert(ev.stdin.includes('Stage-1 task'),'stage directive'); assert(!ev.argv.join('\n').includes('Stage-1 task'),'brief leaked')
assert(ev.argv.includes('approval_policy=never'),'fresh approval policy'); assert(ev.argv.indexOf('approval_policy=never')<ev.argv.indexOf('-C'),'approval before cwd')
res=await callTool('codex_implement',{session:'impl1',directive:'Implement now.'}); assert(!res.isError,`implement failed ${text(res)}`); ev=last('codex'); const r=ev.argv.indexOf('resume'); assert(ev.argv.indexOf('--sandbox')<r&&ev.argv.indexOf('-c')<r,'flag order'); assert(ev.cwd===work,'resume cwd')
res=await callTool('codex_critique',{session:'impl1'}); assert(!res.isError,`critique failed ${text(res)}`); assert(last('codex').stdin.includes('Is there any work left'),'critique default')
res=await callTool('codex_exec',{brief:'NO_UUID one-shot.',cwd:work}); assert(!res.isError,`exec without uuid failed ${text(res)}`); assert(!text(res).includes('codex_session_id:'),'unexpected exec uuid meta'); assert(!existsSync(join(state,'sessions/codex-exec.json')),'exec registered')
res=await callTool('codex_exec',{brief:'NO_UUID one-shot.'}); assert(res.isError&&text(res).includes('cwd'),'exec cwd required')
writeFileSync(brief,'DECOY_UUID\n'); res=await callTool('codex_plan',{session:'marker1',brief_path:brief,cwd:work,replace:true}); assert(!res.isError,`marker failed ${text(res)}`); const marker=JSON.parse(readFileSync(join(state,'sessions/marker1.json'),'utf8')); assert(marker.codex_session_id==='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee','marker uuid preferred')
writeFileSync(join(state,'sessions/bad.json'),JSON.stringify({name:'bad',cli:'codex',codex_session_id:'not-a-uuid',cwd:work,effort:'medium',sandbox:'workspace-write'})); res=await callTool('operator_sessions',{name:'bad'}); assert(res.isError&&text(res).includes('corrupt session registry')&&text(res).includes('bad.json'),'corrupt registry rejected'); unlinkSync(join(state,'sessions/bad.json'))
writeFileSync(brief,'SLEEP_LONG\n'); res=await callTool('codex_plan',{session:'bg1',brief_path:brief,cwd:work,background:true,replace:true}); assert(!res.isError,`bg start ${text(res)}`); const job=text(res).match(/job: ([A-Za-z0-9._-]+)/)?.[1] ?? text(res).match(/background job started: ([A-Za-z0-9._-]+)/)?.[1]; assert(job,'job missing'); res=await callTool('codex_result',{job,wait_seconds:5},10000); assert(!res.isError,`bg result ${text(res)}`)
assert(events().some(e=>e.tool==='codex'&&e.stdin.includes('SLEEP_LONG')&&e.jobFilesAtStartup?.includes(`${job}.json`)),'job json missing at child startup')
writeFileSync(brief,'SLEEP_LONG\n'); res=await callTool('codex_plan',{session:'race1',brief_path:brief,cwd:work,background:true,replace:true}); assert(!res.isError,`race first ${text(res)}`); const raceJob=text(res).match(/job: ([A-Za-z0-9._-]+)/)?.[1] ?? text(res).match(/background job started: ([A-Za-z0-9._-]+)/)?.[1]; res=await callTool('codex_plan',{session:'race1',brief_path:brief,cwd:work,background:true}); assert(res.isError&&text(res).includes('session already exists'),'race second accepted'); if(raceJob) await callTool('codex_result',{job:raceJob,wait_seconds:5},10000)
res=await callTool('operator_sessions',{}); assert(!res.isError&&text(res).includes('impl1'),'sessions missing')
res=await callTool('operator_sessions',{name:'impl1'}); assert(!res.isError&&text(res).includes('recent_logs'),'named session logs missing')
res=await callTool('agy_ask',{prompt:'Analyze this.',model:'gemini-3.5-flash',cwd:work,add_dirs:[work]}); assert(!res.isError,`agy failed ${text(res)}`); ev=last('agy'); assert(ev.cwd===work,'agy cwd'); assert(ev.argv.includes('gemini-3.5-flash'),'agy model'); assert(ev.argv.includes('--effort'),'agy effort flag absent'); assert(ev.argv[ev.argv.indexOf('--effort')+1]==='high','agy default effort'); assert(ev.argv.indexOf('--effort')<ev.argv.indexOf('-p'),'agy effort order'); assert(ev.argv.at(-1).includes('Do NOT publish'),'guardrail'); assert(text(res).includes('effort: high'),'agy effort metadata')
res=await callTool('agy_ask',{prompt:'Analyze flash.',model:'gemini-3.5-flash',effort:'medium',cwd:work}); assert(!res.isError,`agy flash medium effort failed ${text(res)}`); ev=last('agy'); assert(ev.argv[ev.argv.indexOf('--effort')+1]==='medium','agy flash medium effort')
res=await callTool('agy_ask',{prompt:'Analyze pro.',model:'gemini-3.1-pro',effort:'low',cwd:work}); assert(!res.isError,`agy explicit effort failed ${text(res)}`); ev=last('agy'); assert(ev.argv.includes('--effort'),'agy explicit effort flag absent'); assert(ev.argv[ev.argv.indexOf('--effort')+1]==='low','agy explicit effort')
before=events().filter(e=>e.tool==='agy').length; res=await callTool('agy_ask',{prompt:'Invalid effort.',model:'gemini-3.1-pro',effort:'medium',cwd:work}); assert(res.isError&&text(res).includes('allowed: low, high'),'agy invalid effort accepted'); assert(events().filter(e=>e.tool==='agy').length===before,'agy invalid effort spawned')
res=await callTool('agy_ask',{prompt:'Analyze this.',model:'gemini-3.5-flash'}); assert(res.isError&&text(res).includes('cwd'),'agy cwd required')
res=await callTool('agy_ask',{prompt:'Bad.',model:'gpt-5.3-codex'}); assert(res.isError,'agy reject')
res=await callTool('cursor_ask',{prompt:'Cursor prompt.',model:'gpt-5.3-codex',cwd:work}); assert(!res.isError,`cursor failed ${text(res)}`); ev=last('cursor'); assert(ev.cwd===work,'cursor cwd'); assert(ev.argv.join(' ')==='-p --force --model gpt-5.3-codex --output-format text','cursor argv'); assert(ev.stdin==='Cursor prompt.','cursor stdin')
res=await callTool('cursor_ask',{prompt:'Cursor prompt.',model:'gpt-5.3-codex'}); assert(res.isError&&text(res).includes('cwd'),'cursor cwd required')
res=await callTool('cursor_ask',{prompt:'Bad.',model:'gemini-3.5-flash'}); assert(res.isError,'cursor reject')
console.log('operators harness: all assertions passed')
JS

PLUGIN_DIR="$PLUGIN_DIR" OPERATORS_STATE_DIR="$STATE/state" OPERATORS_STUB_TRACE="$TRACE" OPERATORS_WORK="$WORK" OPERATORS_BRIEF="$BRIEF" bun "$HARNESS"
echo "Scratch state: $STATE"

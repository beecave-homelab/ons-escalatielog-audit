"""Identical analysis outcomes and priority reuse under optimization (#64)."""

import pytest
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

# Frozen reference from main 14e797a: the original full search loops.
REFERENCES = r"""
function referencePeers(employees,
rows,
s){
const contexts=new Map();
for(const r of rows){
const k=employeeKey(r);
if(!contexts.has(k))contexts.set(k,
{
teams:new Set(),
roles:new Set()}
);
const c=contexts.get(k);
c.teams.add(hasValue(r.employeeTeam)?r.employeeTeam:'');
c.roles.add(hasValue(r.expertise)?r.expertise:'');
}
const stable=e=>{
const c=contexts.get(e.__key);
return c&&c.teams.size===1&&c.roles.size===1&&hasValue(e.Team)&&hasValue(e.Deskundigheid)}
;
return employees.map(e=>{
const eligible=stable(e),
others=employees.filter(p=>p!==e&&stable(p));
const t=eligible?others.filter(p=>p.Team===e.Team):[],
d=eligible?others.filter(p=>p.Deskundigheid===e.Deskundigheid):[],
b=t.filter(p=>p.Deskundigheid===e.Deskundigheid);
const med=(a,
key)=>a.length>=s.peerGroupMinSize?median(a.map(p=>p[key])):null;
const tm=med(t,
'Escalaties'),
dm=med(d,
'Escalaties'),
bm=med(b,
'Escalaties'),
cm=med(t,
'Unieke cliënten');
const out={
Medewerker:e.Medewerker,
Medewerkernummer:e.Medewerkernummer,
Gebruikersnaam:e.Gebruikersnaam,
Team:e.Team,
Deskundigheid:e.Deskundigheid,
Escalaties:e.Escalaties,
'Unieke cliënten':e['Unieke cliënten'],
Vergelijkbaarheid:eligible?
'Stabiele context; alleen waargenomen medewerkers':'Niet vergeleken: context ontbreekt of wisselt',
'Team peers':t.length,
'Teammediaan escalaties':tm??'',
'Ratio volume / team':ratio(e.Escalaties,
tm),
'Teammediaan cliënten':cm??'',
'Ratio cliënten / team':ratio(e['Unieke cliënten'],
cm),
'Deskundigheid peers':d.length,
'Deskundigheidsmediaan escalaties':dm??'',
'Ratio volume / deskundigheid':ratio(e.Escalaties,
dm),
'Team+deskundigheid peers':b.length,
'Combinatiemediaan escalaties':bm??'',
'Ratio volume / team+deskundigheid':ratio(e.Escalaties,
bm)}
;
const missing=(count,
base)=>!eligible?
'Context ontbreekt of wisselt':count<s.peerGroupMinSize?
`Te weinig peers: ${count} / minimum ${s.peerGroupMinSize}`:base===0?'Mediaan is nul':'';
Object.defineProperty(out,
'__ratioMissing',
{
value:{
'Ratio volume / team':missing(t.length,
tm),
'Ratio cliënten / team':missing(t.length,
cm),
'Ratio volume / deskundigheid':missing(d.length,
dm),
'Ratio volume / team+deskundigheid':missing(b.length,
bm)}
,
enumerable:false}
);
Object.defineProperty(out,
'__peerKeys',
{
value:unique([e,
...t,
...d].map(x=>x.__key)),
enumerable:false}
);
return bindEmployeeKey(out,
e.__key);
}
).sort((a,
b)=>(Number(b['Ratio volume / team+deskundigheid'])||
0)-(Number(a['Ratio volume / team+deskundigheid'])||
0));
}
function referenceBursts(rows,
s){
const groups=new Map();
rows.forEach(r=>{
if(!r.started)return;
const k=employeeKey(r);
if(!k)return;
if(!groups.has(k))groups.set(k,
[]);
groups.get(k).push(r)}
);
const out=[];
for(const [k,
events0] of groups){
const events=[...events0].sort((a,
b)=>a.started.epoch-b.started.epoch);
let left=0,
best=null;
for(let right=0;
right<events.length;
right++){
while(events[right].started.epoch-events[left].started.epoch>s.burstWindowMinutes*60000)left++;
const slice=events.slice(left,
right+1),
targets=new Set(slice.map(targetKey).filter(Boolean)),
clients=new Set(slice.filter(isClient).map(r=>r.targetId).filter(hasValue));
const candidate={
count:slice.length,
targets:targets.size,
clients:clients.size,
start:slice[0].started,
end:slice.at(-1).started,
rows:slice}
;
if(!best||
candidate.count>best.count||
(candidate.count===best.count&&candidate.targets>best.targets))best=candidate}
if(best&&best.count>=s.burstThreshold){
const first=events[0];
out.push(bindEmployeeKey({
Medewerker:first.userName||
k,
Medewerkernummer:first.employeeNumber,
Team:first.employeeTeam,
Deskundigheid:first.expertise,
'Max escalaties in venster':best.count,
'Unieke doelen in venster':best.targets,
'Unieke cliënten in venster':best.clients,
'Minimum escalaties':s.burstThreshold,
'Verstreken (sec.)':(best.end.epoch-best.start.epoch)/1000,
'Venster (min.)':s.burstWindowMinutes,
'Start venster':best.start.display,
'Einde venster':best.end.display,
__rows:best.rows}
,
k))}
}
return out.sort((a,
b)=>b['Max escalaties in venster']-a['Max escalaties in venster']||
b['Unieke doelen in venster']-a['Unieke doelen in venster'])}
function referenceClusters(rows,
s){
const groups=new Map();
rows.forEach(r=>{
if(!r.started||
!isClient(r)||
!hasValue(r.targetId))return;
if(!groups.has(r.targetId))groups.set(r.targetId,
[]);
groups.get(r.targetId).push(r)}
);
const out=[];
for(const [cid,
events0] of groups){
const events=[...events0].sort((a,
b)=>a.started.epoch-b.started.epoch);
let left=0,
best=null;
for(let right=0;
right<events.length;
right++){
while(events[right].started.epoch-events[left].started.epoch>s.clientClusterWindowMinutes*60000)left++;
const slice=events.slice(left,
right+1),
emps=new Set(slice.map(employeeKey).filter(Boolean)),
teams=new Set(slice.map(r=>r.employeeTeam).filter(hasValue)),
exp=new Set(slice.map(r=>r.expertise).filter(hasValue));
const candidate={
count:slice.length,
emps:emps.size,
teams:teams.size,
exp:exp.size,
start:slice[0].started,
end:slice.at(-1).started,
rows:slice}
;
if((candidate.emps>=s.clientClusterEmployeeThreshold||
candidate.teams>=s.clientClusterTeamThreshold)&&(!best||
candidate.emps>best.emps||
(candidate.emps===best.emps&&candidate.teams>best.teams)||
(candidate.emps===best.emps&&candidate.teams===best.teams&&candidate.count>best.count)))best=candidate}
if(best&&(best.emps>=s.clientClusterEmployeeThreshold||
best.teams>=s.clientClusterTeamThreshold)){
const r0=events[0];
out.push({
Cliënt:r0.targetName||
cid,
Cliëntnummer:cid,
'Escalaties in venster':best.count,
'Unieke medewerkers':best.emps,
'Unieke teams':best.teams,
'Unieke deskundigheden':best.exp,
'Minimum medewerkers':s.clientClusterEmployeeThreshold,
'Minimum teams':s.clientClusterTeamThreshold,
'Selectiereden':[best.emps>=s.clientClusterEmployeeThreshold?'Medewerkerdrempel':'',
best.teams>=s.clientClusterTeamThreshold?'Teamdrempel':''].filter(Boolean).join(' en '),
'Verstreken (sec.)':(best.end.epoch-best.start.epoch)/1000,
'Venster (min.)':s.clientClusterWindowMinutes,
'Start venster':best.start.display,
'Einde venster':best.end.display,
__rows:best.rows}
)}
}
return out.sort((a,
b)=>b['Unieke medewerkers']-a['Unieke medewerkers']||
b['Unieke teams']-a['Unieke teams']||
b['Escalaties in venster']-a['Escalaties in venster'])}
"""


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            "() => {"
            + REFERENCES
            + "Object.assign(window,{referencePeers,referenceBursts,referenceClusters});}"
        )
        yield page
        browser.close()


def test_windows__match_original_search_and_exact_source_order(page) -> None:
    """Window members, boundaries, tied candidates and missing keys stay identical."""
    result = page.evaluate(
        """() => {
          let seed=64;
          const rand=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
          const serialize=rows=>rows.map(r=>({...r,key:r.__key,
            __rows:r.__rows.map(x=>x.sourceRow)}));
          for(let run=0;run<80;run++){
            const rows=Array.from({length:run===0?0:180},(_,i)=>({
              sourceRow:i+2,userName:i%7===0?'':`Fictief ${i%5}`,
              employeeNumber:i%7===0?'':`E${rand(5)}`,loginName:'',
              employeeTeam:['','-','A','B','C'][rand(5)],
              expertise:['','-','Zorg','Overig'][rand(4)],
              targetType:rand(4)?'Cliënt':'Locatie',targetId:['','-','C1','C2'][rand(4)],
              targetName:'Fictief doel',
              started:i%19===0?null:parseDate(`2026-05-04T08:${String(rand(60)).padStart(2,'0')}:00`)
            }));
            const s={...DEFAULT_SETTINGS,burstWindowMinutes:1+rand(30),
              burstThreshold:1+rand(12),clientClusterWindowMinutes:1+rand(30),
              clientClusterEmployeeThreshold:1+rand(6),clientClusterTeamThreshold:1+rand(4)};
            for(const [actual,reference] of [[burstAnalysis,referenceBursts],
                [clientClusterAnalysis,referenceClusters]]){
              const a=serialize(actual(rows,s)),b=serialize(reference(rows,s));
              if(JSON.stringify(a)!==JSON.stringify(b))return {run,actual:a,expected:b};
            }
          }
          return null;
        }"""
    )
    assert result is None


@pytest.mark.parametrize("size", [0, 1, 2, 3, 4, 7, 12, 25])
@pytest.mark.parametrize("minimum", [1, 2, 4])
def test_peers__match_original_medians_context_and_evidence(page, size, minimum) -> None:
    """Self-exclusion, even/odd medians, duplicates and varying context stay identical."""
    result = page.evaluate(
        """({size,minimum}) => {
          const employees=Array.from({length:size},(_,i)=>bindEmployeeKey({
            Medewerker:`Fictief ${i}`,Medewerkernummer:`E${i}`,Gebruikersnaam:`u${i}`,
            Team:['A','B','A||B'][i%3],Deskundigheid:['Zorg','Overig','B||Zorg'][Math.floor(i/3)%3],
            Escalaties:[1,2,2,4,6][i%5],'Unieke cliënten':i%4},`E${i}`));
          const rows=employees.flatMap((e,i)=>[{
            employeeNumber:e.__key,employeeTeam:e.Team,expertise:e.Deskundigheid},
            {employeeNumber:e.__key,employeeTeam:i%7===6?'Ander team':e.Team,
              expertise:i%5===4?'':e.Deskundigheid}]);
          const serialize=peers=>peers.map(e=>({...e,key:e.__key,
            peerKeys:e.__peerKeys,missing:e.__ratioMissing}));
          const s={...DEFAULT_SETTINGS,peerGroupMinSize:minimum};
          return {actual:serialize(peerAnalysis(employees,rows,s)),
            expected:serialize(referencePeers(employees,rows,s))};
        }""",
        {"size": size, "minimum": minimum},
    )
    assert result["actual"] == result["expected"]


def test_priority__computed_once_and_reused_for_render_and_report(page) -> None:
    """Sorting, screen and report reuse one priority decision per attention item."""
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    # The fixture from the existing upload flow is read by the regular analysis.
    page.locator("#analyzeBtn").click()
    page.wait_for_selector("#workspace.show")
    result = page.evaluate(
        """() => {
          const original=priorityDecision;let calls=0;
          priorityDecision=row=>{calls++;return original(row);};
          const r=analyze(state.rawRows,{...DEFAULT_SETTINGS});state.result=r;
          const afterAnalyze=calls;
          render();exportReport();
          const afterExports=calls;
          const levels=r.attention.map(row=>attentionPriority(row));
          const explanations=r.attention.every(row=>
            JSON.stringify(row.__explanation.priority)===JSON.stringify(original(row)));
          const again=analyze(state.rawRows,{...DEFAULT_SETTINGS,signalNight:false});
          priorityDecision=original;
          return {afterAnalyze,afterExports,count:r.attention.length,explanations,
            allCached:levels.every((level,i)=>level===r.attention[i].__explanation.priority.level),
            rerun:calls-afterExports,rerunCount:again.attention.length};
        }"""
    )
    assert result["afterAnalyze"] == result["count"] == 1790
    assert result["afterExports"] == result["afterAnalyze"]
    assert result["explanations"] and result["allCached"]
    assert result["rerun"] == result["rerunCount"]

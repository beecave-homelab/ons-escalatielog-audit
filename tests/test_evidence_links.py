"""Drilldown evidence comes from the index recorded in analyze() (issue #51)."""

import re

import pytest
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

CHECK_JS = r"""() => {
  const r=state.result;
  const brief='Unieke bronregels die bijdragen aan deze maat.'
    +' Verschillende kaarten kunnen dezelfde regels bevatten.';
  const out={mismatches:[],counts:{}};
  const calls=[];
  const orig=openDrilldown;
  openDrilldown=(title,rows,sub)=>{calls.push({title,rows:rows.map(x=>x.sourceRow),sub})};
  const check=(group,selector,ref,sub)=>{
    const els=$$(selector);
    out.counts[group]=(out.counts[group]||0)+els.length;
    els.forEach((el,i)=>{
      const want=ref(i,el),n=calls.length;
      el.onclick();
      const call=calls.at(-1);
      if(calls.length!==n+1||!call){out.mismatches.push({group,i,err:'geen drilldown'});return}
      const wantRows=want.rows.map(x=>x.sourceRow);
      if(JSON.stringify(call.rows)!==JSON.stringify(wantRows))
        out.mismatches.push({group,i,title:call.title,got:call.rows,want:wantRows});
      if(call.title!==want.title)
        out.mismatches.push({group,i,title:call.title,wantTitle:want.title});
      const wantAria=`${want.title}: ${want.rows.length} bronregels openen`;
      if(el.getAttribute('aria-label')!==wantAria)
        out.mismatches.push({group,i,aria:el.getAttribute('aria-label'),want:wantAria});
      if(sub&&call.sub!==sub(i,el,want))
        out.mismatches.push({group,i,sub:call.sub,want:sub(i,el,want)});
    });
  };
  const sets=[r.auditRows,r.attention,
    r.auditRows.filter(x=>hasValue(employeeKey(x))),
    r.auditRows.filter(x=>isClient(x)&&hasValue(x.targetId)),
    r.auditRows.filter(x=>x.reEscalationMinutes!==null),
    r.auditRows.filter(x=>x.notActivated)];
  check('kpis','#kpis .kpi',
    (i,el)=>({title:el.querySelector('.label').textContent,rows:sets[i]}),
    (i)=>i===3?`${r.clients.length} unieke cliënt-ID\u2019s uit ${sets[i].length} regels. `
      +`${r.auditRows.filter(x=>isClient(x)&&!hasValue(x.targetId)).length} cliëntpogingen`
      +' zonder ID tellen niet mee in cliëntanalyses.':brief);
  check('priority','#priorityStrip .priority-box',
    (i)=>({title:['Hoog','Midden','Basis'][i],
      rows:r.attention.filter(x=>attentionPriority(x)===['Hoog','Midden','Basis'][i])}),
    ()=>'Gekozen controlevolgorde, geen maat voor ernst of rechtmatigheid.');
  check('themes','#signalCategories .signal-bar-row',
    (i)=>({title:signalCategoryLabel(['access','scope','time','data'][i]),
      rows:r.auditRows.filter(x=>x.signals.some(s=>signalCategory(s)===['access','scope','time','data'][i]))}),
    ()=>brief);
  const sigs=[...r.signalCounts.entries()].sort((a,b)=>b[1]-a[1]);
  check('signals','#signals .signal',
    (i)=>({title:sigs[i][0],
      rows:r.auditRows.filter(x=>x.signals.includes(sigs[i][0]))}),
    (i)=>SIGNAL_META[sigs[i][0]]);
  const charts=[['chartEmployees','#chartEmployees',r.employees.slice(0,10),
      x=>r.auditRows.filter(y=>employeeKey(y)===(x.Medewerkernummer||x.Gebruikersnaam||x.Medewerker))],
    ['chartTeams','#chartTeams',r.teams.slice(0,10),
      x=>r.auditRows.filter(y=>(hasValue(y.employeeTeam)?y.employeeTeam:'(leeg)')===x.Team)],
    ['chartReasons','#chartReasons',r.reasons.slice(0,10),
      x=>r.auditRows.filter(y=>(y.reasonNorm||'(leeg)')===x['Genormaliseerde reden'])],
    ['clientBreadth','#clientBreadth',r.clientsByBreadth.slice(0,10),
      x=>r.auditRows.filter(y=>isClient(y)&&y.targetId===x.Cliëntnummer)]];
  for(const [group,sel,data,pred] of charts)
    check(group,sel+' .bar-row',
      (i,el)=>({title:el.querySelector('.bar-label').textContent,rows:pred(data[i])}),
      ()=>brief);
  check('heatmap','#timeHeatmap .heat-cell',
    (i,el)=>({title:el.title,
      rows:r.auditRows.filter(x=>x.started?.weekday===[1,2,3,4,5,6,0][Math.floor(i/24)]&&x.started.hour===i%24)}),
    ()=>'Ruwe telling per weekdag en uur. Ongeldige datums zijn uitgesloten.');
  check('scatter','#employeeScatter .scatter-dot',
    (i,el)=>({title:el.title,x:r.employees[i],
      rows:r.auditRows.filter(y=>employeeKey(y)===(r.employees[i].Medewerkernummer||r.employees[i].Gebruikersnaam||r.employees[i].Medewerker))}),
    ()=>brief);
  for(let i=0;i<3;i++){const rows=[r.time.dates,r.time.hours,r.time.weekdays][i];
    check(`timeChart${i}`,`#timeChart${i} .bar-row`,
      (j,el)=>({title:el.querySelector('.bar-label').textContent,k:rows[j],
        rows:r.auditRows.filter(x=>x.started&&(i===0?x.started.dateKey===rows[j].Datum:i===1?x.started.hour===j:x.started.weekday===[1,2,3,4,5,6,0][j]))}),
      ()=>'Ruwe telling; niet gecorrigeerd voor bezetting of exportdekking.');}
  openDrilldown=orig;
  out.employees=r.employees.length;
  return out;
}"""


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page
        browser.close()


def load_fixture(page) -> None:
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)


def test_drilldown_evidence_matches_reference_on_fixture(page):
    load_fixture(page)
    result = page.evaluate(CHECK_JS)
    assert result["mismatches"] == []
    assert result["counts"]["heatmap"] == 168
    assert result["counts"]["scatter"] == result["employees"]
    assert all(count > 0 for count in result["counts"].values())


def test_drilldown_evidence_matches_reference_on_edge_rows(page):
    page.evaluate(
        """() => {
          const mk=patch=>{const row={'Gebruiker':'Fictieve medewerker','Medewerkernummer':'E1',
            'Medewerkersteam':'Team A','Deskundigheid medewerker':'Zorg',
            'Gebruikersnaam':'fictief','Escalatie reden':'Controle',
            'Tijdsduur (min.)':'840','Escalatiedoel type':'Cliënt',
            'Escalatiedoel naam':'Fictieve cliënt','Escalatiedoel identificatienummer':'C1',
            'Hoofdlocatie cliënt':'Locatie','Gestart op':'01-01-2026, 08:00:00',
            'Geactiveerd op':'niet geactiveerd','Bron':'Fictief',...patch};
            return REQUIRED_HEADERS.map(k=>row[k])};
          const rows=normalizeRows([REQUIRED_HEADERS,
            mk({'Medewerkernummer':'','Gebruikersnaam':'loginAlleen',
              'Gebruiker':'Fictief login'}),
            mk({'Medewerkernummer':'','Gebruikersnaam':'',
              'Gebruiker':'Fictief naam','Escalatie reden':'',
              'Medewerkersteam':'','Gestart op':'01-01-2026, 09:00:00'}),
            mk({'Escalatiedoel identificatienummer':'',
              'Gestart op':'01-01-2026, 10:00:00'}),
            mk({'Escalatiedoel type':'Locatie','Escalatiedoel naam':'Fictieve locatie',
              'Escalatiedoel identificatienummer':'L1','Gestart op':'01-01-2026, 11:00:00'}),
            mk({'Gestart op':'onleesbaar'}),
            mk({'Gestart op':'01-01-2026, 08:00:00',
              'Geactiveerd op':'01-01-2026, 08:05:00'}),
            mk({'Gestart op':'01-01-2026, 09:00:00'}),
            mk({'Gestart op':'01-01-2026, 12:00:00','Geactiveerd op':'niet geactiveerd'}),
            mk({'Escalatie reden':'','Gestart op':'01-01-2026, 13:00:00'}),
          ],0);
          state.result=analyze(rows,{...DEFAULT_SETTINGS});
          window.__empty=analyze([],{...DEFAULT_SETTINGS});
          state.result=window.__empty;render();
          state.result=analyze(rows,{...DEFAULT_SETTINGS});render();
        }"""
    )
    result = page.evaluate(CHECK_JS)
    assert result["mismatches"] == []
    assert result["counts"]["heatmap"] == 168


def test_render_evidence_links_does_not_filter_rows(page):
    load_fixture(page)
    page.evaluate(
        "(()=>{window.__fc=0;"
        "state.result.auditRows.filter=()=>(window.__fc++,[]);"
        "state.result.attention.filter=()=>(window.__fc++,[])})()"
    )
    page.evaluate("renderEvidenceLinks(state.result)")
    assert page.evaluate("window.__fc") == 0
    for selector in (
        "#timeHeatmap [class*='heat-cell l']",
        "#employeeScatter .scatter-dot",
    ):
        el = page.locator(selector).first
        count = re.search(r": (\d+) bronregels", el.get_attribute("aria-label")).group(1)
        expected = format(int(count), ",d").replace(",", ".")
        el.click()
        page.locator("#drillOverlay.show").wait_for()
        assert re.search(rf"{expected} bronregel", page.locator(".drill-chip").first.text_content())
        page.locator("#drillCloseBtn").click()

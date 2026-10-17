"""Analyse zonder globale toestand en bronselecties met vaste sleutels (#63)."""

import pytest
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            """() => {
              window.makeRows = patches => normalizeRows([REQUIRED_HEADERS,
                ...patches.map((patch,i) => {
                  const row = {'Gebruiker':'Fictieve medewerker','Medewerkernummer':'E1',
                    'Gebruikersnaam':'account','Medewerkersteam':'Team',
                    'Deskundigheid medewerker':'Zorg',
                    'Escalatie reden':'Controle','Tijdsduur (min.)':'15',
                    'Escalatiedoel type':'Cliënt',
                    'Escalatiedoel naam':'Fictieve cliënt','Escalatiedoel identificatienummer':'C1',
                    'Hoofdlocatie cliënt':'Locatie','Gestart op':`04-05-2026, 08:0${i}:00`,
                    'Geactiveerd op':'Niet geactiveerd','Bron':'Synthetisch',...patch};
                  return REQUIRED_HEADERS.map(k=>row[k]);
                })],0);
            }"""
        )
        yield page
        browser.close()


def test_analyze__keeps_entire_state_and_input_with_explicit_night_window(page) -> None:
    """Alle aggregaties volgen s; analyse verandert geen state-eigenschap of bronrij."""
    result = page.evaluate(
        """() => {
          const rows=makeRows([{}, {'Escalatiedoel type':'Locatie'}]);
          const before=JSON.stringify(state), refs=Object.entries(state);
          const input=JSON.stringify(rows);
          Object.freeze(state.settings);Object.freeze(state);
          const r=analyze(rows,{...DEFAULT_SETTINGS,nightStartHour:8,nightEndHour:9});
          const other=analyze(rows,{...DEFAULT_SETTINGS,nightStartHour:9,nightEndHour:10});
          return {
            sameState:before===JSON.stringify(state)&&refs.every(([k,v])=>state[k]===v),
            sameInput:input===JSON.stringify(rows),
            nights:[r.employees[0].Nacht,r.clients[0].Nacht,r.teams[0].Nacht,
              r.expertise[0]['Nacht %'],r.locations[0].Nacht],
            otherNights:[other.employees[0].Nacht,other.clients[0].Nacht,other.teams[0].Nacht,
              other.expertise[0]['Nacht %'],other.locations[0].Nacht],
            signalNights:r.auditRows.filter(x=>x.signals.includes('NACHT')).length,
          };
        }"""
    )
    assert result == {
        "sameState": True,
        "sameInput": True,
        "nights": [2, 1, 2, 100, 1],
        "otherNights": [0, 0, 0, 0, 0],
        "signalNights": 2,
    }


@pytest.mark.parametrize(
    ("number", "login", "name", "key"),
    [
        ("E1", "account", "Fictief", "E1"),
        ("-", "account", "Fictief", "account"),
        ("", "-", "Fictief", "Fictief"),
    ],
)
def test_employee_key__survives_display_changes_in_peers_and_drilldowns(
    page, number: str, login: str, name: str, key: str
) -> None:
    """Nummer, account of naam blijven leidend als weergavevelden later veranderen."""
    result = page.evaluate(
        """({number,login,name,key}) => {
          const rows=makeRows([
            {'Medewerkernummer':number,'Gebruikersnaam':login,'Gebruiker':name},
            {'Medewerkernummer':number,'Gebruikersnaam':login,'Gebruiker':name},
            {'Medewerkernummer':'E2','Gebruikersnaam':'ander','Gebruiker':'Fictieve peer'}]);
          const s={...DEFAULT_SETTINGS,peerGroupMinSize:1,burstThreshold:2};
          const r=analyze(rows,s);
          const groups=[r.employees,r.peers,r.concentration,r.bursts];
          const keys=groups.map(group=>group.find(x=>x.__key===key)?.__key);
          const hidden=groups.every(group=>group.every(x=>
            !Object.keys(x).includes('__key')&&!toCsv([x]).includes('__key')));
          // Wijzig uitsluitend zichtbare identificatievelden: de koppeling mag niet meeveranderen.
          for(const group of groups)for(const x of group){
            x.Medewerkernummer='Ander nummer';x.Gebruikersnaam='Ander account';
            x.Medewerker='Andere naam';
          }
          const peers=peerAnalysis(r.employees,r.auditRows,s);
          const p=peers.find(x=>x.__key===key);
          state.result=r;state.settings=s;state.analysisRunAt=new Date(2026,4,4);
          const selected=[];
          const original=openDrilldown;
          openDrilldown=(title,source)=>selected.push(source.map(x=>x.sourceRow));
          const originalTable=tableWidget, callbacks=new Map();
          tableWidget=(selector,data,opt)=>{callbacks.set(selector,{data,opt});originalTable(selector,data,opt)};
          try{
            render();
            for(const selector of ['#employeesTable','#concentrationTable','#peerTable']){
              const {data,opt}=callbacks.get(selector),x=data.find(x=>x.__key===key);
              selected.push(opt.drilldown(x).rows.map(x=>x.sourceRow));
            }
            const index=r.employees.findIndex(x=>x.__key===key);
            document.querySelectorAll('#chartEmployees .bar-row')[index].click();
            document.querySelectorAll('#employeeScatter .scatter-dot')[index].click();
          }finally{openDrilldown=original;tableWidget=originalTable}
          return {keys,hidden,peerCount:p?.['Team peers'],peerKeys:p?.__peerKeys,
            ratio:p?.['Ratio volume / team'],selected};
        }""",
        {"number": number, "login": login, "name": name, "key": key},
    )
    assert result["keys"] == [key] * 4
    assert result["hidden"]
    assert result["peerCount"] == 1
    assert result["peerKeys"] == [key, "E2"]
    assert result["ratio"] == 2
    assert result["selected"] == [[2, 3], [2, 3], [2, 3, 4], [2, 3], [2, 3]]


def test_employee_key__omits_rows_without_any_identity(page) -> None:
    """Ontbrekende identiteit maakt geen medewerkersgroep of peergroep aan."""
    result = page.evaluate(
        """() => {
          const r=analyze(makeRows([{'Medewerkernummer':'-','Gebruikersnaam':'',
            'Gebruiker':'-'}]),DEFAULT_SETTINGS);
          return [r.auditRows.length,r.employees.length,r.peers.length,r.concentration.length];
        }"""
    )
    assert result == [1, 0, 0, 0]

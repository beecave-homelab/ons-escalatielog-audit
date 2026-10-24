/* The training layer guides existing controls; analysis remains in the app. */
const tourFixture = new File([Uint8Array.from(atob('__FIXTURE_BASE64__'), c => c.charCodeAt(0))], 'synthetic-escalatielog.xlsx', {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
const tourSteps = [
  {title:'Welkom in de oefenomgeving', view:'overview', anchor: "#dropzone", text:'Alles staat al klaar met 2.000 verzonnen bronregels. In de gewone webui begin je met Bestand kiezen en Analyse uitvoeren. De verwerking blijft lokaal. Hier kun je geen eigen bestanden openen.'},
  {title:'Lees de populatie en aandachtspunten', view:'overview', anchor: "#kpis", text:'Van 2.000 bronregels blijven 1.802 auditregels over: 156 systeemregels en 42 duplicaten zijn uitgesloten. Er zijn 1.790 unieke aandachtspunten. Een regel kan meerdere signalen hebben; tel de signaalaantallen daarom niet zomaar op.'},
  {title:'Kies een opvallendheid', view:'overview', anchor: "#findingList", text:'De Top-X toont standaard tien opvallendheden met hun selectiereden. Open bij de eerste opvallendheid de knop Bronregels. Bij Volgende openen we diezelfde knop voor je. Je kunt het aantal zelf aanpassen van 1 tot en met 50.'},
  {title:'Controleer de oorspronkelijke bronregels', view:'overview', anchor: "#drillBody", drill:true, text:'De dialoog toont de Excel-rijen uit het synthetische bronbestand. Lees de auditcontext en vergelijk de gegevens. Een signaal bewijst geen dossierinzage. Sluit gerust de dialoog; met Toon onderdeel open je hem opnieuw. Volgende sluit hem gecontroleerd.'},
  {title:'Zoek, filter en sorteer', view:'attention', anchor: "#attentionTable", text:'Probeer in Zoeken de tekst Medewerker en kies het signaal NACHT. Sorteer via een kolomkop. De teller laat zien welk deel zichtbaar is. Dit verandert alleen de weergave, niet de analyse. Als je terugkomt in deze stap, zijn de filters weer leeg.'},
  {title:'Onderzoek de medewerkercontext', view:'employees', anchor: "#employeesTable", text:'Zoek een medewerker en open een tabelregel voor de bronregels. Vergelijk aantallen met de werkcontext. Een hoog volume is geen risico- of ernstscore. Kies Toon verbanden in de uitleg voor de bestaande analyses onder Verdieping. Keer terug met Toon onderdeel.'},
  {title:'Bekijk de cliëntcontext', view:'clients', anchor: "#clientsTable", text:'Bekijk welke medewerkers en teams bij een cliëntdoel terugkomen. Open een regel voor de brongegevens. De cijfers beschrijven de export; ze verklaren niet waarom toegang nodig was.'},
  {title:'Vergelijk teams met hun context', view:'teams', anchor: "#teamsTable", text:'Bekijk de verdeling over teams en open een regel voor de bijbehorende bronregels. Houd rekening met teamgrootte, bezetting en de taken in de onderzochte periode.'},
  {title:'Herken tijdpatronen', view:'time', anchor: "#timeCards", text:'Bekijk de verdeling per datum, uur en weekdag. Een piek of nachtelijk tijdstip is een aanleiding voor onderzoek. Zonder bezetting en exportdekking kun je hier geen oordeel over de zorgpraktijk aan verbinden.'},
  {title:'Controleer de datakwaliteit', view:'quality', anchor: "#qualityTable", text:'Ontbrekende of ongeldige velden kunnen de interpretatie beïnvloeden. Zoek een bevinding en open de bronregels. Controleer bronproblemen voordat je inhoudelijke conclusies trekt.'},
  {title:'Pas een drempel bewust toe', view:'settings', anchor: "#set-activationDelayThresholdMinutes", text:'De activatievertraging staat standaard op 2 minuten. Wijzig bijvoorbeeld naar 5. Dat verandert nog geen uitkomst: gebruik eerst Analyse opnieuw uitvoeren. Deze drempels zijn selectieregels. Opnieuw beginnen herstelt alle standaardinstellingen en Top-X=10.'},
  {title:'Neem resultaten mee', view:'overview', anchor: "#csvBtn", text:'Aandachtspunten CSV bevat de auditregels met signalen; Rapport HTML bevat de analyse als zelfstandig rapport. Dashboard als PNG geeft het hele dashboard als afbeelding; Acht PNG’s als ZIP levert de vaste bundel. Alleen jouw klik start een download. Hier blijven alle exports synthetisch.'},
  {title:'Kies één afbeelding', view:'overview', anchor: "#visualExports", visuals:true, text:'Onder Eén afbeelding als PNG kies je een gerichte visual of het optionele medewerkerprofiel. Kies een afbeelding en klik zelf op Afbeelding downloaden. De rondleiding start geen downloads en kopieert niets naar het klembord.'},
  {title:'Ga zelfstandig oefenen', view:'overview', anchor: "#tabs", text:'Je hebt de belangrijkste bediening gezien. Kies Zelf oefenen om de uitleg te sluiten. Hervatten brengt je terug naar deze stap; Opnieuw beginnen herstelt het voorbeeld. Menselijke beoordeling blijft nodig: signalen bewijzen geen dossierinzage of onrechtmatige toegang. Echte exports kunnen persoonsgegevens bevatten.'}
];
const tour = {index:0, active:false, busy:false, ready:false, frame:0};
const tourPanel = document.querySelector('#tourPanel');
const tourMarker = document.querySelector('#tourMarker');
const tourSelect = id => document.querySelector(id);
function tourDisableImports(){
  for(const id of ['#chooseBtn','#fileInput','#importSettingsBtn','#settingsFileInput']){const el=tourSelect(id);el.disabled=true;el.title='In deze oefenomgeving zijn alleen ingebouwde synthetische gegevens beschikbaar.';}
}
for(const type of ['drop','dragover'])window.addEventListener(type,e=>{e.preventDefault();e.stopImmediatePropagation();},true);
window.addEventListener('change',e=>{if(e.target.matches('#fileInput,#settingsFileInput')){e.preventDefault();e.stopImmediatePropagation();}},true);
tourDisableImports();
tourSelect('#dropzone strong').textContent='Het synthetische voorbeeld staat klaar';
tourSelect('#dropzone > span').textContent='Bestandsimport is uitgeschakeld. Je kunt veilig oefenen met verzonnen gegevens.';
function tourQueue(){if(!tour.frame)tour.frame=requestAnimationFrame(()=>{tour.frame=0;tourPosition();});}
function tourLayout(){
  const root=document.documentElement,values={'--tour-banner-bottom':Math.ceil(tourSelect('#tourBanner').getBoundingClientRect().bottom),'--tour-viewport-height':window.visualViewport?.height||innerHeight};
  for(const [name,value] of Object.entries(values)){const next=value+'px';if(root.style.getPropertyValue(name)!==next)root.style.setProperty(name,next);}
  const height=tour.active?Math.ceil(tourPanel.getBoundingClientRect().height):0,next=height+'px';if(root.style.getPropertyValue('--tour-guide-height')!==next)root.style.setProperty('--tour-guide-height',next);
}
function tourMount(){
  // Keep the guidance inside the existing modal's keyboard scope while it is open.
  const modal=tourSelect('#drillOverlay.show .drill-panel');
  const parent=tour.active&&modal?modal:document.body;
  if(tourPanel.parentElement!==parent)parent.appendChild(tourPanel);
}
function tourPosition(){
  tourMount();tourLayout();
  if(!tour.active){tourMarker.hidden=true;return;}
  const step=tourSteps[tour.index],target=tourSelect(step.anchor),box=target?.getBoundingClientRect();
  const panel=tourPanel.getBoundingClientRect(),banner=tourSelect('#tourBanner').getBoundingClientRect();
  const narrow=innerWidth<=1100,right=narrow?innerWidth-8:panel.left-12,bottom=narrow?panel.top-8:innerHeight-8;
  const covered=!!tourSelect('#drillOverlay.show')&&!target?.closest('#drillOverlay');
  const visible=!covered&&box&&box.width>0&&box.height>0&&box.bottom>banner.bottom+8&&box.top<bottom&&box.left<right&&!target.closest('[hidden]');
  let message='';
  if(!target)message='Dit onderdeel ontbreekt. Je kunt verdergaan of opnieuw beginnen; meld dit bij de beheerder.';
  else if(covered)message='Bronregels zijn geopend. Sluit ze met Sluiten of kies Toon onderdeel om terug te keren.';
  else if(!visible)message='Het onderdeel is nu buiten beeld of gesloten. Kies Toon onderdeel om terug te keren.';
  tourSelect('#tourRestore').hidden=!target||!!visible;
  tourSelect('.tour-context-actions').hidden=tourSelect('#tourRestore').hidden&&tourSelect('#tourRelated').hidden;
  const hint=tourSelect('#tourHint');if(hint.textContent!==message)hint.textContent=message;
  tourMarker.hidden=!visible;
  if(visible){const left=Math.max(5,box.left),top=Math.max(banner.bottom+5,box.top),width=Math.min(box.right,right)-left,height=Math.min(box.bottom,bottom)-top;Object.assign(tourMarker.style,{left:left+'px',top:top+'px',width:Math.max(0,width)+'px',height:Math.max(0,height)+'px'});}
}
function tourPrepare(){
  const step=tourSteps[tour.index];
  closeDrilldown();
  tourSelect('#visualExports').hidden=true;tourSelect('#visualExportsBtn').setAttribute('aria-expanded','false');
  if(step.view==='settings'){openSettings();renderSettings();}
  else {const tab=document.querySelector(`.tab[data-view="${step.view}"]`);if(tab)tab.click();}
  if(step.view==='attention'){renderTables(state.result);renderEvidenceLinks(state.result);}
  if(step.drill){
    const button=document.querySelector('#findingList [data-finding="0"]');
    if(button)button.click();
  }
  if(step.visuals){tourSelect('#visualExports').hidden=false;tourSelect('#visualExportsBtn').setAttribute('aria-expanded','true');}
  tourMount();tourLayout();
  const target=tourSelect(step.anchor);
  if(target){for(let parent=target.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;target.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'});}
}
function tourShow(index){
  if(tour.busy||!tour.ready)return;
  tour.index=Math.max(0,Math.min(index,tourSteps.length-1));tour.active=true;
  document.body.classList.add('tour-active');tourPanel.hidden=false;
  const step=tourSteps[tour.index];
  tourSelect('#tourTitle').textContent=step.title;tourSelect('#tourText').textContent=step.text;
  tourSelect('#tourProgress').textContent=`Stap ${tour.index+1} van ${tourSteps.length}`;
  tourMarker.firstElementChild.textContent=String(tour.index+1);
  tourSelect('#tourPrev').disabled=tour.index===0;tourSelect('#tourNext').disabled=false;
  tourSelect('#tourRelated').hidden=!['employees','clients','teams'].includes(step.view);
  tourSelect('#tourNext').textContent=tour.index===tourSteps.length-1?'Zelf oefenen':'Volgende';
  tourSelect('#tourResume').textContent='Toon huidige stap';
  tourSelect('.tour-content').scrollTop=0;
  tourPrepare();tourSelect('#tourTitle').focus({preventScroll:true});tourQueue();
}
function tourStop(){
  tour.active=false;tourPanel.hidden=true;tourMarker.hidden=true;document.body.classList.remove('tour-active');
  closeDrilldown();tourMount();tourLayout();tourSelect('#tourResume').textContent='Hervatten';tourSelect('#tourResume').focus();
}
async function tourReset(){
  if(tour.busy||dashboardPngBusy||tourSelect('#loading').classList.contains('show'))return;
  tour.busy=true;tour.ready=false;tourSelect('#tourResume').disabled=true;
  tourSelect('#tourReset').disabled=true;tourSelect('#tourPrev').disabled=true;tourSelect('#tourNext').disabled=true;
  try{
    closeDrilldown();state.settings={...DEFAULT_SETTINGS};state.findingLimit=10;
    state.findingTemplateDraft=FINDING_TEMPLATE;tourSelect('#findingTemplate').value=FINDING_TEMPLATE;
    renderSettings();await loadFile(tourFixture);await runAnalysis();
    if(!state.result)throw new Error('De synthetische analyse kon niet worden geladen.');
    tour.ready=true;tour.busy=false;tourSelect('#tourResume').disabled=false;tourSelect('#tourReset').disabled=false;
    tourShow(0);
  }catch(error){tour.busy=false;tourPanel.hidden=false;tourSelect('#tourTitle').textContent='Rondleiding laden mislukt';tourSelect('#tourText').textContent=error.message+' Ververs het bestand om opnieuw te proberen.';}
  tourDisableImports();
}
tourSelect('#tourRelated').addEventListener('click',()=>{document.querySelector('.tab[data-view="deepdive"]').click();tourSelect('#view-deepdive').scrollIntoView({block:'start'});tourQueue();});
tourSelect('#tourPrev').addEventListener('click',()=>tourShow(tour.index-1));
tourSelect('#tourNext').addEventListener('click',()=>tour.index===tourSteps.length-1?tourStop():tourShow(tour.index+1));
tourSelect('#tourStop').addEventListener('click',tourStop);
tourSelect('#tourReset').addEventListener('click',tourReset);
tourSelect('#tourResume').addEventListener('click',()=>tourShow(tour.index));
tourSelect('#tourRestore').addEventListener('click',()=>tourShow(tour.index));
window.addEventListener('keydown',e=>{if(e.key==='Escape'&&tour.active){e.preventDefault();e.stopImmediatePropagation();tourStop();}},true);
new ResizeObserver(tourQueue).observe(tourSelect('#tourBanner'));
new ResizeObserver(tourQueue).observe(tourPanel);
window.visualViewport?.addEventListener('resize',tourQueue);
window.addEventListener('scroll',tourQueue,true);window.addEventListener('resize',tourQueue);
new MutationObserver(tourQueue).observe(tourSelect('.app'),{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','id']});
new MutationObserver(tourQueue).observe(tourSelect('#drillOverlay'),{attributes:true,attributeFilter:['class']});
tourReset();

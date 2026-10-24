/* The training layer guides existing controls; analysis remains in the app. */
const tourFixture = new File([Uint8Array.from(atob('__FIXTURE_BASE64__'), c => c.charCodeAt(0))], 'synthetic-escalatielog.xlsx', {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
const tourSteps = [
  {title:"Begin met een oefenbestand", view:'overview', anchor: "#dropzone", text:"Een escalatielog is een overzicht uit Nedap Ons van pogingen en gebeurtenissen rond uitzonderlijke toegang tot een cliënt of locatie. Deze oefenversie heeft al 2.000 verzonnen regels ingelezen en geanalyseerd. Je hoeft niets te uploaden. In de gewone webui open je jouw Excel-export met Bestand kiezen en klik je op Analyse uitvoeren. De gegevens blijven op je computer. Kies Volgende om de uitkomsten te bekijken."},
  {title:"Begrijp welke regels meetellen", view:'overview', anchor: "#kpis", text:"Een bronregel is één gegevensrij uit het Excelbestand. Van de 2.000 bronregels sluit de webui 156 regels met bekende systeemredenen en 42 exacte duplicaatkopieën uit. Bij exacte duplicaten zijn alle 14 bronvelden gelijk. De 1.802 overgebleven regels heten de auditpopulatie. Een signaal markeert een regel die voldoet aan een ingestelde controleregel. Van de auditpopulatie krijgen 1.790 regels minstens één signaal. Dat zijn de aandachtspunten die je kunt onderzoeken. Eén regel kan meerdere signalen krijgen, maar telt één keer als aandachtspunt. Tel signaalaantallen dus niet op. Deze aantallen horen bij dit oefenbestand, niet bij jouw organisatie."},
  {title:"Kies waar je begint met controleren", view:'overview', anchor: "#findingList", text:"De Top-X is een selectie van opvallende regels en patronen om te onderzoeken. Standaard zie je tien items. Bij elk item staat waarom de webui het selecteert. Het is geen lijst met bewezen overtredingen. Items kunnen dezelfde bronregels bevatten, dus tel hun aantallen niet op als afzonderlijke incidenten. Klik bij het eerste item op Bronregels om de gegevens erachter te bekijken. Met Volgende opent de rondleiding ze voor je. Je kunt het aantal items aanpassen van 1 tot en met 50."},
  {title:"Lees de gegevens achter een signaal", view:'overview', anchor: "#drillBody", drill:true, text:"Dit venster toont de bronregels die bij de gekozen opvallendheid horen. Het Excel-rijnummer helpt je dezelfde regel in het bronbestand terug te vinden. Vergelijk de medewerker, het doel, de reden en de tijdstippen. Een geregistreerde activatie bewijst niet dat iemand daarna dossiergegevens heeft bekeken. Controleer bij echte gegevens ook het rooster, de dossierlogging en de toelichting op de inzet. Sluiten sluit dit venster. Toon onderdeel opent het opnieuw. Met Volgende ga je verder en sluit het venster."},
  {title:"Zoek een groep aandachtspunten", view:'attention', anchor: "#attentionTable", text:"Een signaal betekent dat een regel voldoet aan een ingestelde controleregel. NACHT betekent bijvoorbeeld dat de starttijd binnen het ingestelde nachtvenster valt. Dat zegt op zichzelf niets over de noodzaak van de toegang. Typ Medewerker in het zoekveld en kies NACHT bij het signaalfilter. Klik op een kolomkop om te sorteren. De teller toont hoeveel regels je nu ziet. Zoeken, filteren en sorteren veranderen alleen deze tabelweergave. De analyse en exports blijven gelijk. Terugkeren naar deze stap wist de tabelfilters."},
  {title:"Bekijk de regels per medewerker", view:'employees', anchor: "#employeesTable", text:"Elke tabelregel vat de escalaties van één medewerker samen. Zoek een medewerker en klik op de regel om de bijbehorende bronregels te openen. Veel escalaties kunnen een reden zijn om verder te kijken. Het aantal is geen maat voor de ernst en bewijst geen onrechtmatige toegang. Vergelijk de cijfers met de taken en inzet van die medewerker. Toon verbanden opent Verdieping, met aanvullende vergelijkingen en patronen. Toon onderdeel brengt je terug naar deze tabel."},
  {title:"Bekijk de regels per cliënt", view:'clients', anchor: "#clientsTable", text:"Hier groepeert de webui escalaties met doeltype Cliënt op cliëntnummer. Een cliëntdoel is de cliënt op wie de escalatie betrekking heeft. De tabel laat zien hoeveel verschillende medewerkers en teams bij dat doel voorkomen. Klik op een regel om de bronregels te lezen. Veel betrokken medewerkers verklaren niet vanzelf waarom toegang nodig was. Regels zonder herkenbaar cliëntnummer kunnen niet aan een cliëntgroep worden gekoppeld. De tabel geeft daardoor niet altijd alle cliëntgerichte regels weer."},
  {title:"Vergelijk de geregistreerde teams", view:'teams', anchor: "#teamsTable", text:"Deze tabel groepeert de auditregels op het team dat in de export staat. Klik op een regel om te zien welke bronregels bijdragen aan de aantallen. Een groter team kan meer escalaties hebben doordat er meer medewerkers werken. Bekijk daarom ook de bezetting, taken en onderzochte periode. De export toont niet de volledige teambezetting. De geregistreerde teamnaam bewijst bovendien geen behandelrelatie tussen een medewerker en een cliënt."},
  {title:"Bekijk wanneer escalaties plaatsvinden", view:'time', anchor: "#timeCards", text:"De grafieken verdelen escalaties over datums, uren en weekdagen. Klik op een balk om de bijbehorende bronregels te bekijken. Een piek vertelt je wanneer er veel geregistreerde escalaties waren. Een nachtelijk tijdstip betekent niet dat de toegang onnodig was. Controleer of de export de hele onderzochte periode bevat en vergelijk het patroon met de bezetting en werkzaamheden. Zonder die informatie kun je geen oordeel over de zorgpraktijk aan de cijfers verbinden."},
  {title:"Controleer of de gegevens bruikbaar zijn", view:'quality', anchor: "#qualityTable", text:"Datakwaliteit toont problemen zoals ontbrekende velden, ongeldige tijdstippen en duplicaten. Klik op een bevinding om de betrokken bronregels te lezen. Een ontbrekend cliëntnummer kan bijvoorbeeld verklaren waarom een regel niet in de cliënttabel voorkomt. Controleer zulke bronproblemen voordat je conclusies trekt over medewerkers of cliënten. Dit overzicht onderzoekt de niet-systeemregels vóór het verwijderen van duplicaatkopieën. Aantallen kunnen daarom afwijken van de auditpopulatie."},
  {title:"Probeer een andere selectiegrens", view:'settings', anchor: "#set-activationDelayThresholdMinutes", text:"Activatievertraging is de tijd tussen Gestart op en Geactiveerd op. De webui geeft standaard een signaal als dat verschil meer dan 2 minuten is. Precies 2 minuten telt dus niet als laat. Verander de grens naar 5 en klik op Analyse opnieuw uitvoeren om de wijziging toe te passen. Pas dan gebruikt de analyse de nieuwe grens. Een drempel helpt regels selecteren voor onderzoek en is geen norm voor toegestaan gedrag. Opnieuw beginnen herstelt alle standaardinstellingen en zet de Top-X terug op tien items."},
  {title:"Bewaar een resultaat om te bespreken", view:'overview', anchor: "#csvBtn", text:"Aandachtspunten CSV downloadt de auditregels met signalen als een tabelbestand dat je in Excel kunt openen. Rapport HTML bewaart de analyse als een rapport dat je in een browser kunt lezen. Dashboard als PNG maakt één afbeelding van het hele dashboard. Acht PNG’s als ZIP bundelt acht afbeeldingen in één bestand. Kies zelf een exportknop om te downloaden. In deze oefenomgeving bevatten de bestanden alleen verzonnen gegevens. Exports uit de gewone webui kunnen persoonsgegevens bevatten. Deel die zorgvuldig, net als het bronbestand."},
  {title:"Download één gerichte afbeelding", view:'overview', anchor: "#visualExports", visuals:true, text:"Met Eén afbeelding als PNG kun je een afzonderlijk overzicht bewaren in plaats van het hele dashboard. Kies in het keuzepaneel welke afbeelding je wilt. Je kunt ook een medewerkerprofiel kiezen om de cijfers voor één medewerker te bekijken. Klik daarna op Afbeelding downloaden. Neem de uitleg en beperkingen van de cijfers mee als je een afbeelding bespreekt. De rondleiding start zelf geen downloads en kopieert niets naar je klembord."},
  {title:"Oefen verder en controleer de context", view:'overview', anchor: "#tabs", text:"Kies Zelf oefenen om de uitleg te sluiten en de tabbladen zelf te bekijken. Hervatten opent deze stap opnieuw. Opnieuw beginnen zet het oefenbestand en de instellingen terug naar het begin. Bij een echte analyse begin je met de bronregels achter een signaal. Controleer daarna het rooster, de dossierlogging en de inzet met de betrokkenen. De webui helpt je kiezen wat je onderzoekt. Signalen bewijzen geen dossierinzage of onrechtmatige toegang. Ook een regel zonder signaal is geen bevestiging dat de toegang terecht was."}
];
const tour = {index:0, active:false, busy:false, ready:false, frame:0};
const tourPanel = document.querySelector('#tourPanel');
const tourMarker = document.querySelector('#tourMarker');
const tourSelect = id => document.querySelector(id);
function tourDisableImports(){
  for(const id of ['#chooseBtn','#fileInput','#importSettingsBtn','#settingsFileInput']){const el=tourSelect(id);el.disabled=true;el.title='In deze oefenomgeving kun je alleen de ingebouwde verzonnen gegevens gebruiken.';}
}
for(const type of ['drop','dragover'])window.addEventListener(type,e=>{e.preventDefault();e.stopImmediatePropagation();},true);
window.addEventListener('change',e=>{if(e.target.matches('#fileInput,#settingsFileInput')){e.preventDefault();e.stopImmediatePropagation();}},true);
tourDisableImports();
tourSelect('#dropzone strong').textContent='Het oefenbestand is al geanalyseerd';
tourSelect('#dropzone > span').textContent='Je oefent met verzonnen gegevens. Eigen bestanden openen kan alleen in de gewone webui.';
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
  if(!target)message='Dit onderdeel ontbreekt. Kies Volgende om verder te gaan of Opnieuw beginnen om de rondleiding te herstellen. Meld het probleem bij de beheerder.';
  else if(covered)message='Bronregels zijn geopend. Kies Sluiten om het venster te sluiten of Toon onderdeel om terug te keren naar deze stap.';
  else if(!visible)message='Het onderdeel bij deze stap staat buiten beeld of is gesloten. Kies Toon onderdeel om het weer te bekijken.';
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
    if(!state.result)throw new Error('Het oefenbestand kon niet worden geanalyseerd.');
    tour.ready=true;tour.busy=false;tourSelect('#tourResume').disabled=false;tourSelect('#tourReset').disabled=false;
    tourShow(0);
  }catch(error){tour.busy=false;tourPanel.hidden=false;tourSelect('#tourTitle').textContent='De rondleiding kon niet starten';tourSelect('#tourText').textContent=error.message+' Ververs de pagina om het opnieuw te proberen.';}
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

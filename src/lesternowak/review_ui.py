"""Page unique du pilote de vérification. Tout texte de document passe par textContent."""

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilote de vérification</title>
<style>
body{font:15px/1.5 system-ui,sans-serif;margin:0;color:#222}
header{padding:.4rem 1rem;background:#eee;display:flex;gap:1rem;align-items:center}
#bar{flex:1;height:10px;background:#ccc;border-radius:5px;overflow:hidden}
#bar div{height:100%;background:#3a7;width:0}
main{display:grid;grid-template-columns:1fr 2fr 1fr;gap:1rem;padding:1rem}
section{border:1px solid #ccc;border-radius:8px;padding:.5rem 1rem}
img{max-width:100%}
.passage{white-space:pre-wrap;background:#fffbe0;border-left:4px solid #d4a800;padding:.5rem 1rem}
mark{background:#fc6;padding:0 2px}
button{margin:2px;padding:4px 8px;border:1px solid #888;border-radius:4px;background:#fff;
cursor:pointer}
button.sel{background:#235;color:#fff}
.k{color:#888;font-size:.8em}
.meta{color:#555;font-size:.9em}
textarea{width:100%;box-sizing:border-box}
.blind{background:#ddf;padding:2px 6px;border-radius:4px}
@media(max-width:900px){main{grid-template-columns:1fr}}
</style></head><body>
<header><b id="pos"></b><div id="bar"><div></div></div><span id="stats"></span>
<span id="msg"></span></header>
<main>
<section id="left"></section>
<section id="center"></section>
<section id="right"></section>
</main>
<script>
const REL=["about","group","context","mentions","not_about","unsure"];
const FN=["visual_description","technical_material","iconography_interpretation","comparison",
"attribution_dating","provenance_context","other"];
const FKEY="qwertyu";
const DEC=[["validated","valider","v"],["rejected","rejeter","x"],["unresolved","non résolu","n"]];
let S=null,idx=0,cur={},t0=0;
const $=(t,props,...kids)=>{const e=document.createElement(t);
 if(props)for(const k in props){if(k==="onclick")e.onclick=props[k];else if(k==="href"){
  if(/^https?:\/\//.test(props[k])){e.href=props[k];e.target="_blank";e.rel="noopener noreferrer"}}
  else if(k==="src"){if(/^https?:\/\//.test(props[k]))e.src=props[k]}
  else e[k]=props[k]}
 for(const c of kids)e.append(c);return e};
function link(url,label){return url?$("a",{href:url},label):$("span",{},"")}
async function load(){S=await (await fetch("/api/state")).json();
 const i=S.items.findIndex(x=>!S.events[x.item_id]);idx=i<0?S.items.length-1:i;show()}
function show(){
 const it=S.items[idx];if(!it)return;const ev=S.events[it.item_id];
 cur={relation:ev?.relation||it.proposal?.relation||null,
  function:ev?.function||it.proposal?.function||null,
  decision:ev?(ev.after):null,note:ev?.note||""};
 t0=Date.now();render(it);progress()}
function progress(){const st=S.stats;
 document.getElementById("pos").textContent=`${idx+1} / ${st.total}`;
 document.querySelector("#bar div").style.width=(100*st.decided/Math.max(1,st.total))+"%";
 document.getElementById("stats").textContent=`${st.decided} décidés`+
  (st.mean_ms!=null?` · ${(st.mean_ms/1000).toFixed(1)} s/item`:"")+` · ${S.annotator}`}
function render(it){
 const L=document.getElementById("left");L.replaceChildren();
 const a=it.artwork;
 L.append($("h3",{},a.title));
 if(a.image_display_allowed&&a.image_url)L.append($("img",{src:a.image_url,alt:a.title}));
 else L.append($("p",{className:"meta"},"Image non affichée (droits non établis)."));
 const meta=[["Catalogue",a.catalogue_number],["Inventaire",a.accession_number],
  ...Object.entries(a.other_ids)];
 for(const [k,v] of meta)if(v)L.append($("div",{className:"meta"},`${k} : ${v}`));
 L.append($("div",{},link(a.collection_url,"Fiche du musée")));
 L.append($("div",{className:"meta"},"Droits : "+it.rights_summary));
 const C=document.getElementById("center");C.replaceChildren();
 C.append($("div",{className:"meta"},`${it.corpus} · ${it.passage.section} · ${it.passage.span_id}`+
  (it.blind?" · ":"")),);
 if(it.blind)C.lastChild.append($("span",{className:"blind"},"à l'aveugle"));
 const p=$("div",{className:"passage"});const t=it.passage.text;let pos=0;
 const hs=[...it.highlights].sort((x,y)=>x.start-y.start);
 for(const h of hs){if(h.start<pos)continue;p.append(t.slice(pos,h.start));
  p.append($("mark",{title:h.label},t.slice(h.start,h.end)));pos=h.end}
 p.append(t.slice(pos));C.append(p);
 C.append($("div",{},link(it.source.url,"Page source"),
  it.source.page_label?` (${it.source.page_label})`:""));
 if(it.source.page_image_url)
  C.append($("div",{},link(it.source.page_image_url,"Image de la page")));
 if(it.proposal){C.append($("h4",{},"Proposition"));
  C.append($("div",{},`${it.proposal.relation} · ${it.proposal.function||"fonction non proposée"}`+
   ` · ${it.proposal.evidence_mechanism}`));
  C.append($("div",{className:"meta"},it.proposal.explanation))}
 else C.append($("p",{className:"meta"},"Élément à l'aveugle : aucune proposition."));
 drawRight(it)}
function drawRight(it){
 const R=document.getElementById("right");R.replaceChildren();
 R.append($("h4",{},"Relation"));
 REL.forEach((r,i)=>R.append($("button",{className:cur.relation===r?"sel":"",
  onclick:()=>{cur.relation=r;drawRight(it)}},`${i+1} ${r}`)));
 R.append($("h4",{},"Fonction"));
 FN.forEach((f,i)=>R.append($("button",{className:cur.function===f?"sel":"",
  onclick:()=>{cur.function=f;drawRight(it)}},`${FKEY[i]} ${f}`)));
 if(!it.blind){R.append($("h4",{},"Décision"));
  for(const [d,l,k] of DEC)R.append($("button",{className:cur.decision===d?"sel":"",
   onclick:()=>{cur.decision=d;drawRight(it)}},`${k} ${l}`))}
 R.append($("h4",{},"Note"));
 const n=$("textarea",{rows:3,id:"note",value:cur.note});n.oninput=()=>cur.note=n.value;R.append(n);
 R.append($("div",{},$("button",{onclick:save},"Entrée : enregistrer et suivant"),
  $("button",{onclick:()=>move(-1)},"← précédent")));
 R.append($("p",{className:"k"},"Note : Tab (Échap pour revenir aux raccourcis)"))}
function msg(t){document.getElementById("msg").textContent=t}
function move(d){const j=idx+d;if(j>=0&&j<S.items.length){idx=j;show()}}
async function save(){
 const it=S.items[idx];
 const body={item_id:it.item_id,relation:cur.relation,function:cur.function,
  decision:cur.decision,note:cur.note,elapsed_ms:Date.now()-t0};
 const r=await fetch("/api/decision",{method:"POST",
  headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const j=await r.json();
 if(!r.ok){msg("Refusé : "+j.error);return}
 msg("Enregistré");const st=await (await fetch("/api/state")).json();S=st;
 if(idx<S.items.length-1)idx++;show()}
document.addEventListener("keydown",e=>{
 const it=S&&S.items[idx];if(!it)return;
 if(e.target.id==="note"){if(e.key==="Escape")e.target.blur();return}
 if(e.ctrlKey||e.metaKey||e.altKey)return;
 const k=e.key;let ch=true;
 if(k==="Enter")save();else if(k==="ArrowLeft")move(-1);
 else if(k>="1"&&k<="6")cur.relation=REL[+k-1];
 else if(k.length===1&&FKEY.includes(k.toLowerCase()))
  cur.function=FN[FKEY.indexOf(k.toLowerCase())];
 else if(!it.blind&&k==="v")cur.decision="validated";
 else if(!it.blind&&k==="x")cur.decision="rejected";
 else if(!it.blind&&k==="n")cur.decision="unresolved";
 else if(k==="Tab"){e.preventDefault();document.getElementById("note").focus();ch=false}
 else ch=false;
 if(ch&&k!=="Enter"&&k!=="ArrowLeft")drawRight(it)});
load();
</script></body></html>
"""

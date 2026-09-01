const form=document.querySelector("#commitments");
const checks=[...form.querySelectorAll('input[type="checkbox"]')];
const button=document.querySelector("#continue-button");
const label=document.querySelector("#button-label");
const badge=document.querySelector("#readiness-badge");
const cards=document.querySelector("#corpus-cards");
const requirements=document.querySelector("#requirements-list");
const message=document.querySelector("#access-message");
let readiness={status:"locked",corpora:[]};

const complete=()=>checks.every((check)=>check.checked);
const payload=()=>Object.fromEntries(checks.map((check)=>[check.name,check.checked]));

function updateButton(){
  button.disabled=!complete();
  label.textContent=!complete()?"Complete the acknowledgments":readiness.status==="ready"?"Confirm and continue securely":"Confirm and check readiness";
}

function renderCard(corpus){
  const percent=Math.round(corpus.completed/corpus.required*100);
  return `<section class="corpus-card ${corpus.ready?"ready-card":""}" aria-label="${corpus.label} readiness"><div class="corpus-header"><h3>${corpus.label}</h3><span aria-hidden="true">${corpus.ready?"✓":"●"}</span></div><p class="role">${corpus.role}</p><p class="gate-count"><strong>${corpus.completed}</strong> / ${corpus.required} requirements complete</p><div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${corpus.required}" aria-valuenow="${corpus.completed}"><span style="width:${percent}%"></span></div><p class="corpus-state">${corpus.ready?"Ready for restricted next step":"Waiting on external requirements"}</p></section>`;
}

function render(summary){
  readiness=summary;cards.setAttribute("aria-busy","false");cards.innerHTML=summary.corpora.map(renderCard).join("");
  const outstanding=[...new Set(summary.corpora.flatMap((corpus)=>corpus.blocking_items||[]))];
  requirements.innerHTML=outstanding.length?`<ul>${outstanding.map((item)=>`<li>${item}</li>`).join("")}</ul>`:"<p>Both real-data lanes passed all server-verified requirements.</p>";
  if(summary.status==="ready"){
    badge.className="status-badge ready";badge.textContent="Requirements complete";message.className="access-message ready";message.textContent="Both lanes are ready. Complete the acknowledgments to request the separately approved restricted workspace.";
  }else{
    badge.className="status-badge locked";badge.textContent="Review locked";message.className="access-message";message.textContent="You may finish these acknowledgments now. Research text and ratings stay locked while any external requirement is incomplete.";
  }
  updateButton();
}

function unavailable(){
  readiness={status:"locked",corpora:[]};cards.setAttribute("aria-busy","false");cards.innerHTML='<div class="corpus-card" style="grid-column:1/-1"><h3>Status unavailable</h3><p class="role">The server could not prove readiness. Review access remains locked automatically.</p><p class="corpus-state">No research material was loaded.</p></div>';requirements.innerHTML="<p>The coordinator must restore a valid, text-free readiness record before review can begin.</p>";badge.className="status-badge unavailable";badge.textContent="Verification unavailable";message.className="access-message error";message.textContent="Readiness could not be verified. You can acknowledge the protocol, but review access will remain locked.";updateButton();
}

async function load(){try{const response=await fetch("/api/readiness",{cache:"no-store"});if(!response.ok)throw new Error();const summary=await response.json();if(!Array.isArray(summary.corpora))throw new Error();render(summary)}catch{unavailable()}}

async function requestAccess(){
  if(!complete())return;button.disabled=true;label.textContent="Checking securely…";
  try{
    const response=await fetch("/api/review-access",{method:"POST",headers:{"Content-Type":"application/json"},cache:"no-store",body:JSON.stringify(payload())});
    const result=await response.json();
    if(response.ok&&result.status==="onboarding_complete"){message.className="access-message ready";message.textContent="Onboarding is complete. The coordinator must now connect the separately approved restricted review workspace.";label.textContent="Onboarding complete";return}
    message.className="access-message";message.textContent=result.reason||"Review access remains locked.";label.textContent="Requirements incomplete — check again later";
  }catch{message.className="access-message error";message.textContent="The secure check was unavailable. Review access remains locked and no research material was loaded.";label.textContent="Verification unavailable"}
  button.disabled=false;
}

checks.forEach((check)=>check.addEventListener("change",updateButton));button.addEventListener("click",requestAccess);load();

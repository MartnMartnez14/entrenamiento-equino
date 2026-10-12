import {segments,timing,formatTime,parseTime} from './domain.js';
export function mountTrainingTimes(form,s){
 arrangeForm(form);
 const $=selector=>form.querySelector(selector);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const enabled=st=>['completed','draft'].includes(st),hasDistance=st=>['completed','draft','untimed'].includes(st);
 const finalEntry=document.createElement('div');finalEntry.className='wide';$('#distance').closest('label').after(finalEntry);
 $('#mode').value=s?.timingMode||'split';
 const config=()=>({distance:Number($('#distance').value),length:Number($('#segment').value),status:$('#status').value,mode:$('#mode').value});
 let applied=config(),lengths=[],reference=null,changing=false;
 const inputs=()=>[...form.querySelectorAll('.split-input')];
 const values=()=>applied.mode==='final'?[$('#final-time')?.value||'']:inputs().map(i=>i.value);
 function readTiming(status='draft'){
  const fields=applied.mode==='final'?[$('#final-time')]:inputs();let previous=0,blank=false;
  for(const input of fields){input.removeAttribute('aria-invalid');const value=input.value.trim();try{if(!value){blank=true;if(status!=='draft')throw Error('Completa este tiempo o elige Borrador.');continue;}const time=parseTime(value);if(applied.mode==='cumulative'&&(blank||time<=previous))throw Error(blank?'Completa los acumulados en orden.':'El acumulado debe ser mayor que el anterior.');previous=time;}catch(err){err.input=input;throw err;}}
  if(applied.mode==='final'){const value=$('#final-time').value.trim();if(!value&&status==='draft')return {splits:[],total:null};return {splits:[],total:parseTime(value)};}
  return timing(inputs().map(i=>i.value),applied.mode,status);
 }
 function total(){try{$('#total').textContent=enabled(applied.status)?formatTime(readTiming().total):'—';}catch{$('#total').textContent='—';}}
 // Keep the native select nodes intact when updating dependent fields.
 function draw(v=[]){
  $('#status-help').textContent=statusHelp[applied.status];
  lengths=hasDistance(applied.status)&&applied.mode!=='final'?segments(applied.distance,applied.length):[];
  for(const [id,disabled] of [['distance',!hasDistance(applied.status)],['segment',!hasDistance(applied.status)||applied.mode==='final'],['mode',!enabled(applied.status)]])$('#'+id).disabled=disabled;
  const title=$('#splits').parentElement.querySelector('h2');title.textContent=applied.mode==='final'?'Tiempo final':'Parciales del entrenamiento';
  $('#time-help').textContent=!enabled(applied.status)?'Este estado se guarda sin tiempos.':applied.mode==='final'?'Tiempo total para la distancia indicada. Usa 1:51 o 111 segundos. No se inventan parciales.':(applied.mode==='split'?'Duración de cada tramo. Ejemplo: 38 + 37 + 36 segundos = 1:51. También admite 38,25 o 1:15.50.':'Tiempo del cronómetro en cada punto. Usa 38, 75 y 111 segundos (total 1:51). Deben crecer y ser consecutivos.')+(reference!=null?' Tiempo final anterior de referencia: '+formatTime(reference)+'. Completa los parciales; no se reparten automáticamente.':'');
  finalEntry.hidden=applied.mode!=='final'||!enabled(applied.status);
  finalEntry.innerHTML=finalEntry.hidden?'':`<label class="field">Tiempo final${applied.status==='completed'?' *':' (opcional en borrador)'}<input aria-describedby="time-help" id="final-time" inputmode="decimal" aria-label="Tiempo final" placeholder="1:51 o 111" value="${esc(v[0]||'')}"></label>`;
  $('#segment').closest('label').hidden=applied.mode==='final';
  let end=0;
  $('#splits').innerHTML=!enabled(applied.status)?'':applied.mode==='final'?'':lengths.map((m,i)=>{const start=end;end+=m;return `<label class="field">${applied.mode==='split'?`${start}–${end} m (${m} m)`:`Hasta ${end} m`}<input class="split-input" aria-describedby="time-help" inputmode="decimal" aria-label="Tiempo ${start} a ${end} metros" value="${esc(v[i]||'')}" placeholder="0:00.00"></label>`;}).join('');
  [...inputs(),...form.querySelectorAll('#final-time')].forEach(i=>i.oninput=()=>{i.removeAttribute('aria-invalid');total();});total();
 }
 let initial=s?.splits?.map(v=>v==null?'':formatTime(v))||[];
 if(applied.mode==='final')initial=[s?.total==null?'':formatTime(s.total)];
 else if(applied.mode==='cumulative'){let sum=0;initial=(s?.splits||[]).map(v=>v==null?'':formatTime(sum+=v));}
 draw(initial);
 function restore(){for(const [id,key] of [['distance','distance'],['segment','length'],['status','status'],['mode','mode']])$('#'+id).value=applied[key];$('#status-help').textContent=statusHelp[applied.status];}
 async function change(){
  if(changing)return false;changing=true;
  try{
   const next=config();if(JSON.stringify(next)===JSON.stringify(applied))return true;
   if(hasDistance(next.status))segments(next.distance,next.mode==='final'?next.distance:next.length);
   const old=values(),newLengths=hasDistance(next.status)&&next.mode!=='final'?segments(next.distance,next.length):[];let v=old;
   if(applied.mode==='final'){
    if(old[0]&&(!enabled(next.status)||next.mode!=='final')){if(!await askDiscard(form,'El tiempo final se conservará como referencia. Los parciales deberán ingresarse manualmente. ¿Continuar?')){restore();return false;}reference=readTiming().total;v=[];}
    else if(old[0]&&next.distance!==applied.distance){if(!await askDiscard(form,'¿Conservar el tiempo final asociado a la nueva distancia?')){restore();return false;}}
    if(next.mode!=='final')v=[];
   }else if(next.mode==='final'){
    if(old.some(Boolean)&&!await askDiscard(form,'Se trasladará el total cuando los parciales estén completos y se eliminarán los parciales. ¿Continuar?')){restore();return false;}
    let sum=null;try{sum=readTiming().total;}catch{}v=[sum==null?'':formatTime(sum)];reference=null;
   }else{
    if(next.mode!==applied.mode){try{const result=timing(old,applied.mode,'draft');let sum=0;v=result.splits.map(t=>t==null?'':formatTime(next.mode==='cumulative'?(sum+=t):t));if(next.mode==='cumulative')timing(v,'cumulative','draft');}catch{if(old.some(Boolean)&&!await askDiscard(form,'Los tiempos no se pueden convertir. ¿Descartarlos?')){restore();return false;}v=[];}}
    const mapped=remapTimes(lengths,newLengths,v,next.mode,enabled(next.status));if(mapped.lost&&!await askDiscard(form,'El cambio descarta tiempos de tramos que ya no coinciden. ¿Continuar?')){restore();return false;}v=mapped.values;
   }
   applied=next;draw(v);$('#session-error').textContent='';return true;
  }catch(err){showFormError(form,err);restore();return false;}finally{changing=false;}
 }
 for(const id of ['distance','segment']){$('#'+id).oninput=()=>{if(!values().some(Boolean)&&Number($('#'+id).value)>0)change();};$('#'+id).onchange=change;}
 $('#status').onchange=change;$('#mode').onchange=change;
 return {inputs,change,readTiming};
}

export function remapTimes(oldLengths,newLengths,values,mode,enabled=true){
 const keys=lengths=>{let end=0;return lengths.map(m=>{const start=end;end+=m;return mode==='cumulative'?String(end):`${start}:${end}`;});};
 const oldKeys=keys(oldLengths),newKeys=keys(newLengths);
 return {lost:values.some((v,i)=>v&&(!enabled||!newKeys.includes(oldKeys[i]))),values:enabled?newKeys.map(k=>values[oldKeys.indexOf(k)]||''):[]};
}

function askDiscard(form,message){
 return new Promise(resolve=>{
 const dialog=document.createElement('dialog');dialog.className='management';dialog.setAttribute('aria-label','Confirmar cambio de tiempos');
 const heading=document.createElement('h2');heading.textContent='Revisar tiempos antes de cambiar';
 const text=document.createElement('p');text.textContent=message;
 const actions=document.createElement('div');actions.className='actions';
 const keep=document.createElement('button');keep.type='button';keep.className='secondary';keep.textContent='Conservar tiempos';
 const discard=document.createElement('button');discard.type='button';discard.textContent='Confirmar cambio';
 const finish=value=>{dialog.close();dialog.remove();resolve(value);};
 keep.onclick=()=>finish(false);discard.onclick=()=>finish(true);dialog.oncancel=e=>{e.preventDefault();finish(false);};
 actions.append(keep,discard);dialog.append(heading,text,actions);form.append(dialog);dialog.showModal();keep.focus();
 });
}

const statusHelp={completed:'Trabajo realizado con tiempos completos y positivos.',draft:'Registro pendiente: admite tiempos incompletos y queda fuera de estadísticas deportivas.',untimed:'Trabajo realizado sin tiempos: cuenta en distancia y frecuencia.',rest:'Descanso registrado: no requiere distancia ni tiempos.',cancelled:'Trabajo cancelado: no cuenta como trabajo realizado y no requiere tiempos.'};
function arrangeForm(form){
 const original=form.querySelector('.fields'),timingPanel=form.querySelector('#splits').parentElement;
 const section=(title)=>{const block=document.createElement('section');block.className='form-block';const h=document.createElement('h2');h.textContent=title;const fields=document.createElement('div');fields.className='fields';block.append(h,fields);return {block,fields};};
 const work=section('1. Datos del trabajo'),times=section('2. Distancia y tiempos');
 for(const label of [...original.children]){if(label.querySelector('#distance,#segment,#mode'))times.fields.append(label);else work.fields.append(label);}
 original.replaceWith(work.block,times.block);
 times.fields.prepend(form.querySelector('#mode').closest('label'));
 for(const name of ['type','status']){const input=form.querySelector('[name="'+name+'"]');input.closest('label').firstChild.textContent= name==='type'?'Tipo de trabajo *':'Estado *';}
 form.querySelector('#mode').closest('label').firstChild.textContent='Modalidad de tiempos *';
 form.querySelector('#segment').closest('label').firstChild.textContent='Longitud estándar del tramo (m) *';
 const distanceHelp=document.createElement('p');distanceHelp.className='muted';distanceHelp.textContent='Distancia obligatoria para completado, borrador y sin cronometraje. Modalidad y longitud de tramo se habilitan según el estado; Solo tiempo final no necesita tramos.';times.block.prepend(distanceHelp);
 const responsible=form.querySelector('[name="responsible"]');responsible.closest('label').firstChild.textContent='Responsable del trabajo *';
 const help=document.createElement('small');help.className='field-help';help.textContent='Persona a cargo del trabajo. En la versión compartida, el autor es quien guarda con su cuenta. La demo independiente no tiene cuentas.';responsible.closest('label').append(help);
 const status=form.querySelector('#status'),statusNote=document.createElement('small');statusNote.id='status-help';statusNote.className='field-help';status.setAttribute('aria-describedby','status-help');status.closest('label').append(statusNote);
 form.addEventListener('change',()=>{statusNote.textContent=statusHelp[status.value];});statusNote.textContent=statusHelp[status.value];
 const allStates=document.createElement('details');allStates.className='status-guide';allStates.innerHTML='<summary>Qué significa cada estado</summary><dl>'+Object.entries(statusHelp).map(([key,text])=>'<dt>'+({completed:'Completado',draft:'Borrador',untimed:'Sin cronometraje',rest:'Descanso',cancelled:'Cancelado'}[key])+'</dt><dd>'+text+'</dd>').join('')+'</dl>';work.block.append(allStates);
 const noteFields=form.querySelector('[name="notes"]').closest('.fields'),notes=section('3. Observaciones');notes.fields.append(...noteFields.children);notes.fields.querySelector('label').firstChild.textContent='Observaciones (opcional)';noteFields.replaceWith(notes.block);
 timingPanel.className='timing-details';times.block.append(timingPanel);
 const info=document.createElement('p');info.className='save-message';info.id='save-status';info.setAttribute('role','status');form.querySelector('#session-error').before(info);
 for(const input of form.querySelectorAll('[required]'))input.addEventListener('invalid',()=>input.setAttribute('aria-invalid','true'));
 form.addEventListener('input',e=>e.target.removeAttribute('aria-invalid'));
}
export function savingStatus(form,saving){form.querySelector('#session-error').textContent='';form.querySelector('#save-status').textContent=saving?'Guardando…':'';form.setAttribute('aria-busy',String(saving));}
export function showFormError(form,error){
 const alert=form.querySelector('#session-error');alert.textContent=error.message+' Tus datos siguen en el formulario. Corrige el campo indicado o pulsa Guardar entrenamiento para reintentar.';
 form.querySelector('#save-status').textContent='';
 const input=error.input||form.querySelector('input:invalid,select:invalid,textarea:invalid')||(!form.querySelector('[name="responsible"]').value.trim()?form.querySelector('[name="responsible"]'):null);
 if(input){input.setAttribute('aria-invalid','true');input.focus();}else{alert.tabIndex=-1;alert.focus();}
}

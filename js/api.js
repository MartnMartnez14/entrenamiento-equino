import {authenticate, request, getUser} from './shared.js';
export {request, getUser};
let current;
export async function openStore(){await authenticate();current=await request('/api/state');return current;}
export async function reloadStore(){current=await request('/api/state');return current;}
export async function saveStore(next){
 const changes=[];
 for(const [collection,path] of [['horses','horses'],['sessions','sessions']])for(const record of next[collection]){const before=current[collection].find(r=>r.id===record.id);if(JSON.stringify(before)!==JSON.stringify(record))changes.push({record,before,path});}
 if(changes.length!==1)throw Error('Guarda un registro por operación.');
 const {record,before,path}=changes[0];
 const saved=await request('/api/'+path+(before?'/'+encodeURIComponent(record.id):''),{method:before?'PUT':'POST',body:record,idempotent:true});
 const collection=path==='horses'?'horses':'sessions';current={...current,[collection]:before?current[collection].map(r=>r.id===saved.id?saved:r):[...current[collection],saved]};return current;
}

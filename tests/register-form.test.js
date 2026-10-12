import test from 'node:test';
import assert from 'node:assert/strict';
import {remapTimes} from '../js/register-form.js';
test('distancia menor conserva solo intervalos equivalentes y avisa',()=>{assert.deepEqual(remapTimes([500,500,500],[500,500,200],['38','37','36'],'split'),{lost:true,values:['38','37','']});});
test('acumulados se conservan por punto final, no duración del intervalo',()=>{assert.deepEqual(remapTimes([500,500],[250,250,250,250],['38','75'],'cumulative'),{lost:false,values:['','38','','75']});});
test('cambio conjunto de modalidad y distancia no reutiliza último punto',()=>{assert.deepEqual(remapTimes([500,500,500],[500,500,200],['38','75','111'],'cumulative'),{lost:true,values:['38','75','']});});
test('descanso requiere aviso y elimina tiempos; tramo nuevo permanece vacío',()=>{assert.equal(remapTimes([500],[],['38'],'split',false).lost,true);assert.deepEqual(remapTimes([500],[500,200],['38'],'split').values,['38','']);});

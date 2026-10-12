import {types} from './domain.js';
export const directionColors={up:'#33805b',down:'#c14d4d',equal:'#848b8b'};
export const categoryColors=['#497965','#b89b62','#7092ab','#a86a76','#8a79aa','#b87945','#668c8c','#737b45'];
export function seriesColor(type){return categoryColors[Math.max(0,types.indexOf(type))%categoryColors.length];}
export function variation(previous,current){
 if(!Number.isFinite(previous)||!Number.isFinite(current))return null;
 const delta=current-previous;
 return {delta,direction:delta>0?'up':delta<0?'down':'equal',label:delta>0?'Aumenta':delta<0?'Disminuye':'Sin cambio'};
}
export function directionalDataset(dataset){return {...dataset,pointBackgroundColor:dataset.borderColor,pointBorderColor:dataset.borderColor,spanGaps:false,tension:0,segment:{borderColor:ctx=>{
 const change=variation(dataset.data[ctx.p0DataIndex],dataset.data[ctx.p1DataIndex]);
 return ctx.p0.skip||ctx.p1.skip||ctx.p1DataIndex!==ctx.p0DataIndex+1||!change?'transparent':directionColors[change.direction];
 }}};}
export function chartOptions(type,legend=false){
 const options={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:legend,position:type==='pie'?'bottom':'top',labels:{usePointStyle:true}},tooltip:{callbacks:{}}}};
 if(type==='pie')options.plugins.tooltip.callbacks.label=ctx=>{const total=ctx.dataset.data.reduce((a,b)=>a+b,0);return `${ctx.label}: ${ctx.raw} (${(ctx.raw/total*100).toLocaleString('es-UY',{maximumFractionDigits:1})} %)`;};
 else {options.scales={y:{beginAtZero:type==='bar'},x:{ticks:{maxRotation:45}}};if(type==='line')options.plugins.tooltip.callbacks.label=ctx=>{
 const change=variation(ctx.dataset.data[ctx.dataIndex-1],ctx.raw);
 return `${ctx.dataset.label}: ${ctx.raw.toLocaleString('es-UY',{maximumFractionDigits:3})} s · ${change?change.label+' '+(change.delta>0?'+':'')+change.delta.toLocaleString('es-UY',{maximumFractionDigits:3})+' s respecto al punto anterior':'Sin punto anterior comparable'}`;
 };}
 return options;
}
export function updateChartTheme(charts){const color=getComputedStyle(document.body).getPropertyValue('--muted');Chart.defaults.color=color;for(const chart of charts){chart.options.color=color;chart.options.plugins.legend.labels.color=color;if(chart.config.type!=='pie'){for(const axis of Object.values(chart.options.scales)){axis.ticks.color=color;axis.grid.color=getComputedStyle(document.body).getPropertyValue('--border');}}chart.update();}}

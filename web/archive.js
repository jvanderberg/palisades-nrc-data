// Progressive enhancement only. All content is rendered during the static build.
const $ = id => document.getElementById(id);
const entries = [...document.querySelectorAll('[data-entry]')];
const reports = [...document.querySelectorAll('[data-report]')];
function filter() {
  const query=$('query').value.toLowerCase(); let count=0;
  for(const entry of entries) {
    const matches=['year','kind','rating'].every(key=>$(key).value==='All'||entry.dataset[key]===$(key).value) && entry.textContent.toLowerCase().includes(query);
    entry.hidden=!matches; if(matches)count++;
  }
  $('count').textContent=`${count} entries`;
  $('empty').classList.toggle('hidden',count!==0);
}
for(const key of ['year','kind','rating','query']) $(key).addEventListener('input',filter);
$('report-query').addEventListener('input',()=>{
  const query=$('report-query').value.toLowerCase();let count=0;
  for(const report of reports){report.hidden=!report.textContent.toLowerCase().includes(query);if(!report.hidden)count++;}
  $('report-count').textContent=`${count} reports`;
  $('report-empty').classList.toggle('hidden',count!==0);
});
function openReport(){
  const target=document.getElementById(location.hash.slice(1));
  if(target?.matches('[data-report]')){target.hidden=false;target.open=true;target.scrollIntoView();}
}
addEventListener('hashchange',openReport);openReport();
const checked=$('checked-at');
const time=new Date(checked.dateTime);
if(Number.isFinite(time.valueOf())){
  checked.textContent=time.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'})+' (local time)';
  $('stale').classList.toggle('hidden',Date.now()-time.valueOf()<=48*60*60*1000);
}

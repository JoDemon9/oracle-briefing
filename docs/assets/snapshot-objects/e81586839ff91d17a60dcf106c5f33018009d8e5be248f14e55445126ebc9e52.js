(()=>{'use strict';
const doc=document.documentElement;
const missingPhoto=img=>{const f=img.closest('[data-editorial-image]');if(f){img.hidden=true;const note=f.querySelector('[data-image-fallback]');if(note)note.hidden=false;f.classList.add('image-unavailable')}};
document.addEventListener('error',event=>{if(event.target.tagName==='IMG')missingPhoto(event.target)},true);
document.querySelectorAll('[data-editorial-image] img').forEach(img=>{if(img.complete&&!img.naturalWidth)missingPhoto(img)});
const get=k=>{try{return localStorage.getItem(k)}catch{return null}};
const set=(k,v)=>{try{localStorage.setItem(k,v);return true}catch{return false}};
doc.dataset.theme=get('oracle-black-label-theme')||'light';
const sticky=document.querySelector('.stickybar,.top');if(sticky){const resize=()=>doc.style.setProperty('--sticky-height',sticky.getBoundingClientRect().height+'px');resize();if('ResizeObserver' in window)new ResizeObserver(resize).observe(sticky)}
document.querySelectorAll('[data-theme-toggle]').forEach(b=>b.addEventListener('click',()=>{doc.dataset.theme=doc.dataset.theme==='dark'?'light':'dark';set('oracle-black-label-theme',doc.dataset.theme)}));
document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>print()));
const calc=document.querySelector('[data-calculator]');if(calc){const update=()=>{const p=Number(document.querySelector('#principal').value),years=Number(document.querySelector('#years').value),rate=Number(document.querySelector('#interest').value),out=document.querySelector('#payment');if(p<=0||years<1||years>40||rate<0||rate>30){out.textContent='Συμπλήρωσε έγκυρα στοιχεία.';return}const months=years*12,r=rate/1200,v=r?p*r/(1-(1+r)**(-months)):p/months;out.textContent=new Intl.NumberFormat('el-CY',{style:'currency',currency:'EUR'}).format(v)+' / μήνα'};calc.addEventListener('input',update);update()}
let fontSize=Number(get('oracle:reader-font-size'))||19;
const applyFont=()=>doc.style.setProperty('--reader-font-size',fontSize+'px');applyFont();
document.querySelectorAll('[data-font-step]').forEach(b=>b.addEventListener('click',()=>{fontSize=Math.max(16,Math.min(24,fontSize+Number(b.dataset.fontStep)));applyFont();set('oracle:reader-font-size',String(fontSize))}));
const links=[...document.querySelectorAll('.navs a[href^="#"]')];
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)links.forEach(a=>a.classList.toggle('is-active',a.hash==='#'+entry.target.id))},{rootMargin:'-15% 0px -65% 0px'});links.forEach(a=>{const target=document.querySelector(a.hash);if(target)observer.observe(target)})}
const menus=[...document.querySelectorAll('.section-menu,.utility-menu,.edition-status,.intelligence-filters')];
document.addEventListener('click',event=>menus.forEach(menu=>{if(menu.open&&(!menu.contains(event.target)||event.target.closest('a')))menu.open=false}));
document.addEventListener('keydown',event=>{if(event.key==='Escape')menus.forEach(menu=>{if(menu.open){menu.open=false;menu.querySelector('summary').focus()}})});
let printClosed=[];
window.addEventListener('beforeprint',()=>{printClosed=[...document.querySelectorAll('details:not([open])')];printClosed.forEach(x=>x.open=true)});
window.addEventListener('afterprint',()=>{printClosed.forEach(x=>x.open=false);printClosed=[]});
// Scenario content starts fully readable; JavaScript adds keyboard-accessible tabs.
document.querySelectorAll('[data-scenarios]').forEach(group=>{
 const buttons=[...group.querySelectorAll('[data-scenario]')],panels=[...group.querySelectorAll('[data-scenario-panel]')],bar=group.querySelector('[data-scenario-buttons]');
 if(buttons.length<2)return;
 bar.hidden=false;
 const choose=(button,focus=false)=>{buttons.forEach(b=>{const active=b===button;b.setAttribute('role','tab');b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1});panels.forEach(p=>{p.setAttribute('role','tabpanel');p.setAttribute('aria-labelledby',buttons.find(b=>b.dataset.scenario===p.dataset.scenarioPanel).id);p.hidden=p.dataset.scenarioPanel!==button.dataset.scenario});if(focus)button.focus()};
 buttons.forEach((button,i)=>{button.addEventListener('click',()=>choose(button));button.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(i+1)%buttons.length;if(event.key==='ArrowLeft')next=(i+buttons.length-1)%buttons.length;if(event.key==='Home')next=0;if(event.key==='End')next=buttons.length-1;if(next!==undefined){event.preventDefault();choose(buttons[next],true)}})});choose(buttons[0]);
});
const controls=document.querySelector('[data-intelligence-controls]');
if(controls){
 controls.hidden=false;const stories=[...document.querySelectorAll('[data-intelligence-story]')],delta=controls.querySelector('[data-delta-only]'),baseline=controls.querySelector('[data-delta-baseline]'),status=controls.querySelector('[data-filter-status]');let selectedTag='';
 const filter=()=>{const cutoff=Date.parse(baseline.value);let shown=0,unclassified=0;stories.forEach(story=>{let times=[];try{times=JSON.parse(story.dataset.changeTimes)}catch{}const changed=times.some(at=>Date.parse(at)>cutoff);if(delta.checked&&!changed&&story.dataset.changeStatus==='UNKNOWN')unclassified++;const visible=(!selectedTag||story.dataset.driverTags.split(' ').includes(selectedTag))&&(!delta.checked||changed);story.hidden=!visible;if(visible)shown++});document.querySelectorAll('[data-driver-tag]').forEach(a=>a.setAttribute('aria-pressed',String(a.dataset.driverTag===selectedTag)));status.textContent=shown+' θέματα'+(unclassified?' · '+unclassified+' χωρίς ταξινόμηση μεταβολής':'');const archive=controls.querySelector('[data-tag-archive]');archive.hidden=!selectedTag;if(selectedTag){archive.href='https://jodemon9.github.io/Claude-Briefing/search.html?tag='+encodeURIComponent(selectedTag);archive.textContent='#'+selectedTag+' στο αρχείο ↗'}};
 const mode=value=>{doc.dataset.readingMode=value;controls.querySelectorAll('button[data-reading-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.readingMode===value)));stories.forEach(story=>{story.querySelectorAll('.story-findings').forEach(d=>d.open=value!=='executive');story.querySelectorAll('.card-analysis,.story-more').forEach(d=>d.open=value==='full')})};
 controls.querySelectorAll('button[data-reading-mode]').forEach(button=>button.addEventListener('click',()=>mode(button.dataset.readingMode)));
 document.querySelectorAll('[data-driver-tag]').forEach(a=>a.addEventListener('click',event=>{event.preventDefault();selectedTag=selectedTag===a.dataset.driverTag?'':a.dataset.driverTag;filter()}));
 delta.addEventListener('change',filter);baseline.addEventListener('change',filter);controls.querySelector('[data-clear-filters]').addEventListener('click',()=>{selectedTag='';delta.checked=false;filter()});filter();
}
const main=document.querySelector('[data-article-key]');if(!main)return;
const key='oracle:article:'+main.dataset.articleKey,bookmark=document.querySelector('[data-bookmark]'),resume=document.querySelector('[data-resume]'),status=document.querySelector('[data-storage-status]');
const saved=get(key+':bookmark')==='true';bookmark.setAttribute('aria-pressed',String(saved));bookmark.textContent=saved?'Αποθηκευμένο άρθρο':'Αποθήκευση άρθρου';
bookmark.addEventListener('click',()=>{const next=bookmark.getAttribute('aria-pressed')!=='true';if(set(key+':bookmark',String(next))){bookmark.setAttribute('aria-pressed',String(next));bookmark.textContent=next?'Αποθηκευμένο άρθρο':'Αποθήκευση άρθρου';status.textContent='Η αποθήκευση ισχύει μόνο σε αυτόν τον browser.'}else{status.textContent='Η αποθήκευση δεν είναι διαθέσιμη στον browser.'}});
const previous=Number(get(key+':progress'));if(previous>0.03&&previous<0.98){resume.hidden=false;resume.addEventListener('click',()=>window.scrollTo({top:previous*Math.max(0,doc.scrollHeight-innerHeight),behavior:'auto'}))}
let timer;function progress(persist=false){const amount=Math.max(0,Math.min(1,scrollY/Math.max(1,doc.scrollHeight-innerHeight)));document.querySelector('#reading-progress').value=amount*100;clearTimeout(timer);if(persist)timer=setTimeout(()=>set(key+':progress',String(amount)),250)}
document.addEventListener('scroll',()=>progress(true),{passive:true});progress();
})();

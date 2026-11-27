'use strict';
// Reference map only. WGS-84 reference points never feed the synthetic session engine.
(()=>{
  let enabled=false,viewReady=false,z=2,center=[0,0],nodes=[],gesture=null,request=0,chosenPlace='',userLocation=null,locationPending=false,autoRecenter=false,undoStack=[],redoStack=[];
  const pointers=new Map(),map=$('referenceMap'),tiles=$('tiles'),overlay=$('referenceOverlay'),msg=$('mapMsg');
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),limit=85.05112878,world=(zoom=z)=>256*2**zoom;
  const wrap=x=>((x+180)%360+360)%360-180;
  function project(p,zoom=z){const s=world(zoom),lat=clamp(p[0],-limit,limit)*Math.PI/180;return [(p[1]+180)/360*s,(1-Math.asinh(Math.tan(lat))/Math.PI)/2*s];}
  function unproject(p,zoom=z){const s=world(zoom);return [clamp(Math.atan(Math.sinh(Math.PI*(1-2*clamp(p[1],0,s)/s)))*180/Math.PI,-limit,limit),wrap(p[0]/s*360-180)];}
  function distance(a,b){const rad=Math.PI/180,dlat=(b[0]-a[0])*rad,dlon=(b[1]-a[1])*rad,k=Math.sin(dlat/2)**2+Math.cos(a[0]*rad)*Math.cos(b[0]*rad)*Math.sin(dlon/2)**2;return 6371008.8*2*Math.asin(Math.sqrt(clamp(k,0,1)));}
  const controls=document.createElement('div');
  controls.innerHTML='<div class="toolbar" style="flex-wrap:nowrap"><input id="mapSearch" type="search" placeholder="搜索学校、道路或地名" aria-label="搜索地名" style="min-width:0;flex:1"><button id="mapSearchGo">搜索</button></div><div id="mapSearchResults" hidden></div>';
  $('mapPanel').prepend(controls);
  const HUD=document.createElement('div');HUD.style.cssText='position:absolute;top:8px;left:8px;background:#fafaf6ed;border:1px solid #dce2da;border-radius:8px;padding:4px 7px;font-size:11px;pointer-events:none;z-index:2';map.append(HUD);
  const zoomControls=document.createElement('div');zoomControls.style.cssText='position:absolute;right:8px;top:8px;display:grid;gap:4px;z-index:3';
  zoomControls.innerHTML='<button id="mapPlus" aria-label="放大地图" style="width:42px;height:42px;font-size:23px;padding:0">+</button><button id="mapMinus" aria-label="缩小地图" style="width:42px;height:42px;font-size:23px;padding:0">−</button>';
  map.append(zoomControls);
  map.style.height='min(56vh, 460px)';map.hidden=true;map.style.minHeight='280px';
  const footer=document.createElement('p');footer.className='hint';footer.textContent='单指平移，双指缩放；把中心准星对准地物后再添加。19级以上为底图放大，不会新增地图细节。';map.after(footer);
  const retry=document.createElement('button');retry.textContent='重试底图';retry.className='wide';retry.hidden=true;footer.after(retry);
  const place=document.createElement('p');place.className='hint';retry.after(place);
  function saveView(){if(!viewReady)return;try{localStorage.setItem('stridelab.reference.view',JSON.stringify({center,z}));}catch(e){}}
  function restoreView(){try{let v=JSON.parse(localStorage.getItem('stridelab.reference.view')||'null');if(v&&Array.isArray(v.center)&&v.center.length===2&&v.center.every(Number.isFinite)&&Number.isFinite(v.z)){center=[clamp(v.center[0],-limit,limit),wrap(v.center[1])];z=clamp(v.z,2,22);return true;}}catch(e){}return false;}
  const draftKey='stridelab.reference.draft.v1';
  function snapshotRef(){return {nodes:nodes.map(p=>p.slice()),closed:$('mapClosed').checked};}
  function persistDraft(){try{localStorage.setItem(draftKey,JSON.stringify(snapshotRef()));}catch(e){$('mapStatus').textContent='草稿保存失败，请手动保存参考点。';}}
  function loadDraft(){try{const v=JSON.parse(localStorage.getItem(draftKey)||'null');if(v&&Array.isArray(v.nodes)&&v.nodes.length<=120&&v.nodes.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=limit&&Math.abs(p[1])<=180)){nodes=v.nodes;$('mapClosed').checked=v.closed!==false;return true;}}catch(e){}return false;}
  function restoreRef(s){nodes=s.nodes.map(p=>p.slice());$('mapClosed').checked=s.closed;persistDraft();draw();stats();}
  function mutateRef(fn){undoStack.push(snapshotRef());if(undoStack.length>100)undoStack.shift();redoStack=[];fn();persistDraft();draw();stats();}
  const redoButton=document.createElement('button');redoButton.id='mapRedo';redoButton.textContent='重做';$('mapUndo').after(redoButton);
  const insertButton=document.createElement('button');insertButton.id='mapInsert';insertButton.textContent='在所选点后插入准星';$('mapMove').after(insertButton);
  const expandButton=document.createElement('button');expandButton.id='mapExpand';expandButton.textContent='扩大地图';$('mapCenter').after(expandButton);expandButton.onclick=()=>{let big=expandButton.textContent==='扩大地图';map.style.height=big?'75vh':'min(56vh, 460px)';expandButton.textContent=big?'恢复地图大小':'扩大地图';draw();};
  function stats(){let d=0;for(let i=1;i<nodes.length;i++)d+=distance(nodes[i-1],nodes[i]);if($('mapClosed').checked&&nodes.length>2)d+=distance(nodes.at(-1),nodes[0]);const selected=$('mapNode').value;$('mapNode').innerHTML='<option value="-1">选择节点</option>'+nodes.map((p,i)=>'<option value="'+i+'">节点 '+(i+1)+'</option>').join('');if(Number(selected)<nodes.length)$('mapNode').value=selected;$('mapUndo').disabled=!undoStack.length;redoButton.disabled=!redoStack.length;$('mapCount').textContent=nodes.length;$('mapLength').textContent=nodes.length>1?d.toFixed(1):'—';}
  function tileState(){if(!enabled)return;const imgs=[...tiles.children],ok=imgs.filter(i=>i.dataset.state==='ok').length,failed=imgs.filter(i=>i.dataset.state==='error').length;msg.hidden=ok>0;msg.textContent=failed===imgs.length&&imgs.length?'在线底图未能加载。请检查网络后重试；可手动录入已知坐标。':'地图加载中…';retry.hidden=!failed;place.textContent=(chosenPlace?'搜索定位：'+chosenPlace+'。 ':'')+(ok? (failed?'部分地图瓦片未加载。':'地名、道路等由在线底图提供。'):'底图未就绪，暂不允许地图选点。');const w=map.clientWidth/2,h=map.clientHeight/2,central=imgs.some(i=>i.dataset.state==='ok'&&parseFloat(i.style.left)<=w&&parseFloat(i.style.left)+parseFloat(i.style.width)>w&&parseFloat(i.style.top)<=h&&parseFloat(i.style.top)+parseFloat(i.style.height)>h);$('mapAdd').disabled=!central;$('mapMove').disabled=!central;insertButton.disabled=!central;}
  let frame=0;
  function schedule(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;draw();});}
  function draw(){if(!enabled||!viewReady)return;let w=map.clientWidth,h=map.clientHeight;if(!w||!h)return;const c=project(center),left=c[0]-w/2,top=c[1]-h/2;
    const xy=p=>{let a=project(p),dx=a[0]-c[0];if(dx>world()/2)dx-=world();if(dx< -world()/2)dx+=world();return [dx+w/2,a[1]-top];};
    overlay.setAttribute('viewBox','0 0 '+w+' '+h);let q=nodes.map(xy),path=q.map((p,i)=>(i?'L':'M')+p[0]+','+p[1]).join(' ')+(q.length>2&&$('mapClosed').checked?' Z':'');
    overlay.innerHTML='<path d="'+path+'" stroke="#38594a" stroke-width="3" fill="none"/>'+q.map((p,i)=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="9" fill="#405f50" stroke="white" stroke-width="2"/><text x="'+p[0]+'" y="'+(p[1]+3)+'" fill="white" text-anchor="middle" font-size="9">'+(i+1)+'</text>').join('')+'<path d="M'+(w/2-13)+' '+h/2+'h26 M'+w/2+' '+(h/2-13)+'v26" stroke="#fff" stroke-width="4"/><path d="M'+(w/2-13)+' '+h/2+'h26 M'+w/2+' '+(h/2-13)+'v26" stroke="#263b34" stroke-width="1.5"/>';
    if(userLocation){const [x,y]=xy(userLocation);overlay.insertAdjacentHTML('afterbegin','<circle cx="'+x+'" cy="'+y+'" r="14" fill="#4285f4" opacity=".2"/><circle id="currentLocationMarker" cx="'+x+'" cy="'+y+'" r="7" fill="#4285f4" stroke="white" stroke-width="2.5"/>');}
    let tz=Math.min(19,Math.floor(z)),n=2**tz,size=256*2**(z-tz),needed=new Set(),existing=new Map([...tiles.children].map(i=>[i.dataset.key,i]));
    for(let y=Math.floor(top/size);y<=Math.floor((top+h)/size);y++)for(let x=Math.floor(left/size);x<=Math.floor((left+w)/size);x++){
      if(y<0||y>=n)continue;let key=tz+':'+x+':'+y,im=existing.get(key);needed.add(key);
      if(!im){im=document.createElement('img');im.dataset.key=key;im.dataset.state='loading';im.alt='';im.draggable=false;
        im.onload=()=>{im.dataset.state='ok';tileState();};im.onerror=()=>{im.dataset.state='error';tileState();};
        im.src='https://tile.openstreetmap.org/'+tz+'/'+((x%n+n)%n)+'/'+y+'.png';tiles.append(im);}
      Object.assign(im.style,{left:(x*size-left)+'px',top:(y*size-top)+'px',width:size+'px',height:size+'px'});
    }
    for(let el of [...tiles.children])if(!needed.has(el.dataset.key))el.remove();
    $('mapLat').value=center[0].toFixed(7);$('mapLon').value=center[1].toFixed(7);
    let metresPerPixel=40075016.686*Math.cos(center[0]*Math.PI/180)/world(),scale=metresPerPixel*80;
    HUD.textContent='缩放 '+z.toFixed(1)+' · 80px ≈ '+(scale>=1000?(scale/1000).toFixed(1)+' km':scale.toFixed(1)+' m');
    stats();tileState();
  }
  function setCenter(lat,lon,zoom=17){if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>limit||Math.abs(lon)>180){$('mapStatus').textContent='请输入有效的地图中心坐标。';return;}center=[lat,wrap(lon)];z=clamp(zoom,2,22);viewReady=true;map.hidden=false;draw();saveView();}
  function zoomBy(delta){if(!viewReady)return;z=clamp(z+delta,2,22);draw();saveView();}
  function locate(lat,lon){locationPending=false;lat=Number(lat);lon=Number(lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>limit||Math.abs(lon)>180){window.StrideMapLocationError();return;}userLocation=[lat,wrap(lon)];if(!enabled)return;if(autoRecenter||!viewReady){chosenPlace='当前位置';setCenter(lat,lon,18);}else draw();autoRecenter=false;$('mapStatus').textContent='蓝点表示当前位置；可拖动地图或双指缩放。';}
  window.StrideMapLocation=locate;window.StrideMapLocationError=()=>{locationPending=false;autoRecenter=false;$('mapStatus').textContent='定位不可用或权限未授予。可搜索地名、输入坐标或重新定位。';};
  $('mapSearchGo').onclick=()=>{let query=$('mapSearch').value.trim();if(!query)return;let id=++request;$('mapSearchResults').hidden=false;$('mapSearchResults').textContent='正在搜索…';if(window.StrideAndroid&&typeof StrideAndroid.searchPlace==='function'){StrideAndroid.searchPlace(query,id);setTimeout(()=>{if(request===id&&$('mapSearchResults').textContent==='正在搜索…')$('mapSearchResults').textContent='搜索超时，可重试或输入坐标。';},15000);}else $('mapSearchResults').textContent='此环境没有地名搜索服务，可手动输入坐标。';};
  $('mapSearch').addEventListener('keydown',e=>{if(e.key==='Enter')$('mapSearchGo').click();});
  window.StrideMapSearchResults=(id,results)=>{if(id!==request)return;let box=$('mapSearchResults');box.replaceChildren();if(!Array.isArray(results)||!results.length){box.textContent='未找到地名或搜索服务不可用；可尝试完整地址或手动输入坐标。';return;}for(let result of results){if(!Number.isFinite(result.lat)||!Number.isFinite(result.lon))continue;let b=document.createElement('button');b.className='wide';b.style.marginBottom='4px';b.textContent=result.label;b.onclick=()=>{autoRecenter=false;chosenPlace=result.label;setCenter(result.lat,result.lon,18);box.hidden=true;};box.append(b);}};
  $('mapEnable').onclick=()=>{enabled=!enabled;$('mapPanel').hidden=!enabled;$('mapEnable').textContent=enabled?'关闭在线地图':'启用在线地图';if(enabled){nodes=geo.map(p=>p.slice());loadDraft();viewReady=restoreView();if(!viewReady&&nodes.length){center=nodes[0].slice();z=18;viewReady=true;}map.hidden=!viewReady;$('mapAdd').disabled=$('mapMove').disabled=insertButton.disabled=!viewReady;stats();if(viewReady){draw();}else{$('mapStatus').textContent='请搜索场地名称、点击当前位置，或输入已知坐标开始。';}requestLocation(true);}else{autoRecenter=false;saveView();tiles.replaceChildren();pointers.clear();gesture=null;}};
  $('mapCenter').onclick=()=>{autoRecenter=false;chosenPlace='';setCenter(Number($('mapLat').value),Number($('mapLon').value),Math.max(17,z));};
  function requestLocation(automatic=false){if(locationPending)return;autoRecenter=true;locationPending=true;$('mapStatus').textContent='正在定位当前位置…';if(window.StrideAndroid&&typeof StrideAndroid.locate==='function'){StrideAndroid.locate();return;}if(navigator.geolocation)navigator.geolocation.getCurrentPosition(p=>locate(p.coords.latitude,p.coords.longitude),window.StrideMapLocationError,{timeout:10000,enableHighAccuracy:true});else window.StrideMapLocationError();}
  $('mapLocate').onclick=()=>{autoRecenter=true;if(userLocation){chosenPlace='当前位置';setCenter(...userLocation,18);}requestLocation();};
  $('mapZoomIn').onclick=$('mapPlus').onclick=()=>zoomBy(1);$('mapZoomOut').onclick=$('mapMinus').onclick=()=>zoomBy(-1);
  retry.onclick=()=>{for(let el of [...tiles.children])if(el.dataset.state==='error')el.remove();draw();};
  $('mapAdd').onclick=()=>{if(nodes.length>=120){$('mapStatus').textContent='最多120个参考节点。';return;}if(nodes.some(p=>distance(p,center)<0.05)){$('mapStatus').textContent='该位置已有参考节点。';return;}mutateRef(()=>nodes.push(center.slice()));};$('mapUndo').onclick=()=>{if(!undoStack.length)return;redoStack.push(snapshotRef());restoreRef(undoStack.pop());};redoButton.onclick=()=>{if(!redoStack.length)return;undoStack.push(snapshotRef());restoreRef(redoStack.pop());};$('mapClear').onclick=()=>{if(nodes.length)mutateRef(()=>{nodes=[];});};$('mapMove').onclick=()=>{let i=Number($('mapNode').value);if(i>=0&&i<nodes.length){mutateRef(()=>{nodes[i]=center.slice();});}};$('mapDelete').onclick=()=>{let i=Number($('mapNode').value);if(i>=0&&i<nodes.length){mutateRef(()=>nodes.splice(i,1));}};$('mapReverse').onclick=()=>mutateRef(()=>nodes.reverse());insertButton.onclick=()=>{const i=Number($('mapNode').value);if(i<0||i>=nodes.length||nodes.length>=120){$('mapStatus').textContent='请先选择节点，最多120个参考节点。';return;}mutateRef(()=>nodes.splice(i+1,0,center.slice()));};$('mapClosed').onchange=()=>{const next=$('mapClosed').checked;$('mapClosed').checked=!next;mutateRef(()=>{$('mapClosed').checked=next;});};$('mapSave').onclick=()=>{geo=nodes.map(p=>p.slice());try{localStorage.setItem('stridelab.reference.closed',JSON.stringify($('mapClosed').checked));}catch(e){}persistDraft();geoDisplay();save();saveView();$('mapStatus').textContent='参考点已保存，可在下方独立导出 GeoJSON。';};
  function local(e){let r=map.getBoundingClientRect();return [e.clientX-r.left-map.clientLeft,e.clientY-r.top-map.clientTop];}
  function mid(a,b){return [(a[0]+b[0])/2,(a[1]+b[1])/2];}
  function begin(){let a=[...pointers.values()];if(!a.length){gesture=null;return;}let m=a.length>1?mid(a[0],a[1]):a[0],c=project(center),off=[m[0]-map.clientWidth/2,m[1]-map.clientHeight/2];gesture={z,anchor:unproject([c[0]+off[0],c[1]+off[1]]),span:a.length>1?Math.max(1,Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1])):0};}
  map.addEventListener('pointerdown',e=>{if(e.target.closest('a,button'))return;e.preventDefault();autoRecenter=false;pointers.set(e.pointerId,local(e));map.setPointerCapture(e.pointerId);begin();});
  map.addEventListener('pointermove',e=>{if(!gesture||!pointers.has(e.pointerId))return;e.preventDefault();pointers.set(e.pointerId,local(e));let a=[...pointers.values()],m=a.length>1?mid(a[0],a[1]):a[0];if(gesture.span&&a.length>1)z=clamp(gesture.z+Math.log2(Math.max(1,Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]))/gesture.span),2,22);let anchor=project(gesture.anchor);center=unproject([anchor[0]-m[0]+map.clientWidth/2,anchor[1]-m[1]+map.clientHeight/2]);schedule();});
  function stop(e){if(!pointers.delete(e.pointerId))return;begin();draw();saveView();}
  map.addEventListener('pointerup',stop);map.addEventListener('pointercancel',stop);map.addEventListener('lostpointercapture',stop);
  map.addEventListener('wheel',e=>{e.preventDefault();zoomBy(e.deltaY<0?.5:-.5);},{passive:false});window.addEventListener('resize',()=>draw());window.addEventListener('pagehide',()=>{if(enabled)persistDraft();});
  if(window.StrideAndroid&&typeof StrideAndroid.locate==='function')$('mapEnable').click();
})();

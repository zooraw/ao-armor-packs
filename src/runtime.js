'use strict';
// Target-specific, hash-guarded D3D9 texture updates. No database or executable writes.
if(Process.pointerSize!==4)throw new Error('Only the verified 32-bit client is supported');
const ids=[18000,17988,204160,15805,15806,15807,15808,206969];
const cheetah=Process.getModuleByName('Cheetah.dll');
const utils=Process.getModuleByName('Utils.dll');
const files=new Map(),staging=new Map(),hooks=[],lastModes=new Map();
let device=null,pending=false,busy=false,selection={omni_af:true,tank:true},installed=false;
const frameHooks=[],frameRefs=[],frameAddresses=new Set();
let changes=0,lastError=null,lastApplied=[];
let baseModes={omni_af:'custom',tank:'custom'},restoreRequested=false,closing=false;
function method(object,index,result,args){return new NativeFunction(object.readPointer().add(index*4).readPointer(),result,['pointer',...args],'stdcall');}
function check(hr,label){if(hr<0)throw new Error(label+': HRESULT '+hr);}
function release(object){if(object&&!object.isNull())method(object,2,'uint',[])(object);}
function targets(){
 const manager=cheetah.base.add(0x121cf68).readPointer();
 if(manager.isNull())return [];
 const head=manager.add(8).readPointer(),root=head.add(4).readPointer(),rows=[],seen=new Set();
 function visit(node){
  if(node.equals(head)||node.isNull()||seen.has(node.toString()))return;
  if(seen.size>=20000)throw new Error('Renderer cache exceeded verified traversal bound');
  seen.add(node.toString());visit(node.readPointer());
  const id=node.add(28).readU32(),type=node.add(32).readU32();
  if(ids.includes(id)&&type===1010004){
   const resource=node.add(36).readPointer();
   if(!resource.readPointer().equals(cheetah.base.add(0x3896dc)))throw new Error('Unexpected armor resource class');
   const cache=resource.add(0xc4).readPointer();
   if(!cache.isNull())for(let layer=0;layer<3;layer++){
    const index=resource.add(0xc8+layer*4).readU32();if(index===0xffffffff)continue;
    if(index>=cache.add(0x1c).readU32())throw new Error('Invalid armor cache slot');
    const entry=cache.add(0x18).readPointer().add(index*4).readPointer(),material=entry.add(4).readPointer();
    if(material.isNull())continue;
    const texture=material.add(4).readPointer();if(!texture.isNull())rows.push({id,texture,material});
   }
  }
  visit(node.add(8).readPointer());
 }
 visit(root);return rows;
}
function description(texture){
 const data=Memory.alloc(32);check(method(texture,17,'int',['uint','pointer'])(texture,0,data),'GetLevelDesc');
 const result={format:data.readU32(),width:data.add(24).readU32(),height:data.add(28).readU32(),levels:method(texture,13,'uint',[])(texture)};
 if(result.format!==0x31545844||result.width>4096||result.height>4096)throw new Error('Armor target is not the verified DXT1 layout');
 return result;
}
function readDds(spec){
 const buffer=File.readAllBytes(spec.file);
 if(Checksum.compute('sha256',buffer)!==spec.sha256)throw new Error('DDS hash mismatch: '+spec.id+' '+spec.mode);
 const data=new Uint8Array(buffer),view=new DataView(buffer);
 if(view.getUint32(0,true)!==0x20534444||view.getUint32(84,true)!==0x31545844)throw new Error('Expected a DXT1 DDS');
 let width=view.getUint32(16,true),height=view.getUint32(12,true),offset=128;const levels=[];
 for(let mip=0;mip<view.getUint32(28,true);mip++){
  const rowBytes=Math.max(1,Math.ceil(width/4))*8,rows=Math.max(1,Math.ceil(height/4)),size=rowBytes*rows;
  if(offset+size>data.length)throw new Error('Truncated DDS');
  levels.push({width,height,rowBytes,rows,data:data.slice(offset,offset+size)});
  offset+=size;width=Math.max(1,width>>1);height=Math.max(1,height>>1);
 }
 if(offset!==data.length)throw new Error('Unexpected DDS tail');
 // The client allocates the complete rectangular GPU chain, while FCTX omits
 // its final 1x1 level. A terminal DXT1 block also represents that clipped level.
 while(levels[levels.length-1].width>1||levels[levels.length-1].height>1){
  const last=levels[levels.length-1];if(last.data.length!==8)throw new Error('Incomplete non-terminal DDS mip chain');
  levels.push({width:Math.max(1,last.width>>1),height:Math.max(1,last.height>>1),rowBytes:8,rows:1,data:last.data});
 }
 return levels;
}
function source(mode,id,desc){
 const key=mode+':'+id+':'+desc.width+':'+desc.height+':'+desc.levels;
 if(staging.has(key))return staging.get(key);
 const levels=files.get(mode+':'+id);if(!levels)throw new Error('Missing texture mode: '+key);
 const base=levels.findIndex(l=>l.width===desc.width&&l.height===desc.height);
 if(base<0||levels.length-base<desc.levels)throw new Error('DDS does not cover GPU layout: '+key);
 const output=Memory.alloc(4);output.writePointer(ptr(0));
 check(method(device,23,'int',['uint','uint','uint','uint','uint','uint','pointer','pointer'])(device,desc.width,desc.height,desc.levels,0,desc.format,2,output,ptr(0)),'Create system-memory texture');
 const texture=output.readPointer();
 try{
  for(let mip=0;mip<desc.levels;mip++){
   const locked=Memory.alloc(8),level=levels[base+mip];
   check(method(texture,19,'int',['uint','pointer','pointer','uint'])(texture,mip,locked,ptr(0),0),'Lock staging mip');
   try{
    const pitch=locked.readU32(),destination=locked.add(4).readPointer();if(pitch<level.rowBytes)throw new Error('Invalid staging pitch');
    for(let row=0;row<level.rows;row++)destination.add(row*pitch).writeByteArray(level.data.subarray(row*level.rowBytes,(row+1)*level.rowBytes));
   }finally{check(method(texture,20,'int',['uint'])(texture,mip),'Unlock staging mip');}
  }
  staging.set(key,texture);return texture;
 }catch(error){release(texture);throw error;}
}
function upload(sourceTexture,targetTexture){
 // UpdateTexture consumes the source dirty regions. Cached sources must be
 // marked again on EVERY copy, including rollback and shutdown restoration.
 check(method(sourceTexture,21,'int',['pointer'])(sourceTexture,ptr(0)),'Mark complete staging texture dirty');
 check(method(device,31,'int',['pointer','pointer'])(device,sourceTexture,targetTexture),'Update live armor texture');
}
function apply(restore=false){
 const plan=targets().map(target=>{
  const group=target.id===206969?'tank':'omni_af';
  const desc=description(target.texture),mode=restore?baseModes[group]:(selection[group]?'custom':'stock');
  const previous=lastModes.get(target.texture.toString())||baseModes[target.id===206969?'tank':'omni_af'];
  return{...target,mode,source:source(mode,target.id,desc),previous:source(previous,target.id,desc)};
 });
 const done=[];
 try{
  for(const row of plan){upload(row.source,row.texture);done.push(row);}
 }catch(error){
  const failures=[];for(const row of done.reverse()){try{upload(row.previous,row.texture);}catch(_){failures.push(row.id);}}
  if(failures.length)throw new Error(String(error)+'; rollback failed for '+failures.join(','));throw error;
 }
 for(const row of plan)lastModes.set(row.texture.toString(),row.mode);
 changes++;lastApplied=plan.map(r=>({id:r.id,mode:r.mode,texture:r.texture.toString()}));lastError=null;
 send({event:'armor-applied',selection,targets:lastApplied,thread:Process.getCurrentThreadId()});
}
function frame(){if(!device||!pending||busy||closing)return;busy=true;pending=false;try{apply(restoreRequested);if(restoreRequested){restoreRequested=false;closing=true;}}catch(error){lastError=String(error);send({event:'armor-error',error:lastError});}finally{busy=false;}}
const str=new NativeFunction(utils.getExportByName('?str@String@@QBEABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@XZ'),'pointer',['pointer'],'thiscall');
const boolean=new NativeFunction(utils.getExportByName('?AsBool@Variant@@QBE_NXZ'),'bool',['pointer'],'thiscall');
function stringValue(value){const s=str(value),length=s.add(16).readU32();if(length>64)return '';return(s.add(20).readU32()<16?s:s.readPointer()).readUtf8String(length);}
hooks.push(Interceptor.attach(utils.getExportByName('?SetDValue@DistributedValue_c@@SAXABVString@@ABVVariant@@@Z'),{
 onEnter(args){const name=stringValue(args[0]);this.menu=name==='aou_armor_menu';if(name==='aou_armor_omni_af')this.choice=['omni_af',!!boolean(args[1])];else if(name==='aou_armor_tank')this.choice=['tank',!!boolean(args[1])];},
 onLeave(){if(this.choice){selection[this.choice[0]]=this.choice[1];pending=true;frame();}else if(this.menu)frame();}
}));
// Native resource creation/reload marks the next real render frame dirty.
for(const name of ['??0MTexture@Graphics_n@@QAE@PAVIDXTexture@1@H@Z','?UpdateTexture@MTexture@Graphics_n@@QAEXPAVIDXTexture@2@PAVICheetahTexture2D@Platform_n@@@Z']){
 hooks.push(Interceptor.attach(cheetah.getExportByName(name),{
  onEnter(args){this.material=args[0];},
  onLeave(){const texture=this.material.add(4).readPointer();lastModes.delete(texture.toString());pending=true;}
 }));
}
rpc.exports={
 initialize(specs,choices,bases){
  if(installed)throw new Error('Already initialized');
  if(typeof specs==='string')specs=JSON.parse(File.readAllText(specs));
  if(files.size===0)for(const spec of specs)files.set(spec.mode+':'+spec.id,readDds(spec));
  selection=choices;if(bases)baseModes=bases;const rows=targets();if(rows.length===0)return{ready:false,reason:'Waiting for armor resources'};
  const output=Memory.alloc(4);check(method(rows[0].texture,3,'int',['pointer'])(rows[0].texture,output),'Get armor graphics device');
  device=output.readPointer();
  function watch(object,index){const address=object.readPointer().add(index*4).readPointer(),key=address.toString();if(frameAddresses.has(key))return;frameAddresses.add(key);frameHooks.push(Interceptor.attach(address,{onEnter(){frame();}}));}
  watch(device,17);
  const swap=Memory.alloc(4);if(method(device,14,'int',['uint','pointer'])(device,0,swap)>=0){frameRefs.push(swap.readPointer());watch(swap.readPointer(),3);}
  const iid=Memory.alloc(16);iid.writeByteArray([0xce,0x10,0x8b,0xb1,0x49,0x26,0x5a,0x40,0x87,0x0f,0x95,0xf7,0x77,0xd4,0x31,0x3a]);
  const ex=Memory.alloc(4);if(method(device,0,'int',['pointer','pointer'])(device,iid,ex)>=0){frameRefs.push(ex.readPointer());watch(ex.readPointer(),121);}
  installed=true;pending=true;return{ready:true,targets:rows.length};
 },
 select(choices){selection=choices;pending=true;return true;},
 status(){return{installed,selection,changes,pending,lastError,lastApplied,restored:closing};},
 dispose(){
  for(const hook of frameHooks)hook.detach();frameHooks.length=0;
  for(const ref of frameRefs)release(ref);frameRefs.length=0;
  for(const hook of hooks)hook.detach();
  // The caller invokes restore before detaching if AO remains alive.
  for(const texture of staging.values())release(texture);staging.clear();
  release(device);device=null;return true;
 },
 restore(){restoreRequested=true;pending=true;return true;}
};
send({event:'gpu-swap-script-ready'});

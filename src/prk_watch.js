'use strict';
// PRK-only UI preference observer. The renderer owns textures and all reloads.
if(Process.pointerSize!==4)throw Error('Verified PRK client is 32-bit');
const utils=Process.getModuleByName('Utils.dll');
const str=new NativeFunction(utils.getExportByName('?str@String@@QBEABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@XZ'),'pointer',['pointer'],'thiscall');
const boolean=new NativeFunction(utils.getExportByName('?AsBool@Variant@@QBE_NXZ'),'bool',['pointer'],'thiscall');
function nameOf(value){const s=str(value),n=s.add(16).readU32();if(n>64)return '';return(s.add(20).readU32()<16?s:s.readPointer()).readUtf8String(n);}
const hook=Interceptor.attach(utils.getExportByName('?SetDValue@DistributedValue_c@@SAXABVString@@ABVVariant@@@Z'),{
 onEnter(args){const name=nameOf(args[0]);if(name==='aou_armor_omni_af')this.choice=['omni_af',!!boolean(args[1])];else if(name==='aou_armor_tank')this.choice=['tank',!!boolean(args[1])];},
 onLeave(){if(this.choice)send({event:'armor-choice',group:this.choice[0],enabled:this.choice[1]});}
});
rpc.exports={
 ready(){
  const get=new NativeFunction(Process.getModuleByName('kernel32.dll').getExportByName('GetEnvironmentVariableW'),'uint',['pointer','pointer','uint'],'stdcall');
  const text=Memory.alloc(16),name=Memory.allocUtf16String('RANDYVK_HOTRELOAD');
  const n=get(name,text,8);
  return{utils:utils.path,renderer:Process.getModuleByName('randy31.dll').path,hotReload:n===1&&text.readUtf16String()==='1'};
 },
 dispose(){hook.detach();return true;}
};

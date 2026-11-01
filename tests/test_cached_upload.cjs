// Contract regression: Direct3D consumes source dirty regions even on S_OK.
// This is a stateful API model, not a claim of a real GPU render test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync(require('node:path').join(__dirname,'../src/runtime.js'),'utf8');
const helper=code.slice(code.indexOf('function upload('),code.indexOf('function apply('));
assert.equal((code.match(/method\(device,31/g)||[]).length,1,'All writes must use the shared upload boundary');
const device={},stock={pixels:'stock',dirty:true},custom={pixels:'custom',dirty:true};
const context={device,ptr:()=>null,check:hr=>assert.equal(hr,0),method:(object,index)=>{
  if(index===21)return(source,rect)=>{assert.equal(rect,null);source.dirty=true;return 0;};
  assert.equal(index,31);
  return(_device,source,target)=>{if(source.dirty)target.pixels=source.pixels;source.dirty=false;return 0;};
}};
vm.createContext(context);vm.runInContext(helper,context);
const first={},second={};
for(let round=0;round<3;round++){
  for(const source of [stock,custom,stock]){
    context.upload(source,first);context.upload(source,second);
    assert.equal(first.pixels,source.pixels);assert.equal(second.pixels,source.pixels);
  }
}
console.log('Cached off/on/off and repeated-target transfer contract passed (API model).');

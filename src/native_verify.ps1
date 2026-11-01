param([Parameter(Mandatory=$true)][string]$GamePath,
      [Parameter(Mandatory=$true)][string]$DatabasePath,
      [string]$ManifestPath)
$ErrorActionPreference = 'Stop'
if (-not $ManifestPath) {
    $ManifestPath = [System.IO.Path]::Combine([System.IO.Path]::GetDirectoryName($MyInvocation.MyCommand.Path), 'helmet-hires-manifest.json')
}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
public static class NativeRdbProbe {
 [DllImport("kernel32", CharSet=CharSet.Unicode)] public static extern bool SetDllDirectory(string path);
 [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr LoadLibrary(string path);
 [DllImport("kernel32", CharSet=CharSet.Ansi)] public static extern IntPtr GetProcAddress(IntPtr module,string name);
 [UnmanagedFunctionPointer(CallingConvention.ThisCall)] public delegate IntPtr Constructor(IntPtr self,[MarshalAs(UnmanagedType.I1)]bool flag);
 [UnmanagedFunctionPointer(CallingConvention.ThisCall)] public delegate int Open(IntPtr self,[MarshalAs(UnmanagedType.LPStr)]string path,[MarshalAs(UnmanagedType.I1)]bool readOnly,[MarshalAs(UnmanagedType.I1)]bool secondFlag);
 [UnmanagedFunctionPointer(CallingConvention.ThisCall)] public delegate int Get(IntPtr self,uint type,uint id,ref uint size,ref IntPtr bytes);
 [UnmanagedFunctionPointer(CallingConvention.ThisCall)] public delegate int Close(IntPtr self);
 public static object Bind(IntPtr module,string name,Type type) {
  IntPtr p=GetProcAddress(module,name); if(p==IntPtr.Zero)throw new Exception("Missing export "+name);
  return Marshal.GetDelegateForFunctionPointer(p,type);
 }
 public static void Run(string game,string path,uint[] types,uint[] ids,string[] hashes) {
  if(types.Length==0 || types.Length!=ids.Length || ids.Length!=hashes.Length)throw new Exception("Incomplete resource manifest");
  if(IntPtr.Size!=4)throw new Exception("Requires x86 PowerShell");
  SetDllDirectory(game);
  IntPtr module=LoadLibrary(System.IO.Path.Combine(game,"DatabaseController.dll"));
  if(module==IntPtr.Zero)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  var ctor=(Constructor)Bind(module,"??0BlockDatabase_t@@QAE@_N@Z",typeof(Constructor));
  var open=(Open)Bind(module,"?Open@BlockDatabase_t@@QAEHPBD_N1@Z",typeof(Open));
  var get=(Get)Bind(module,"?GetQuick@BlockDatabase_t@@QAEHIIAAIPAPAD@Z",typeof(Get));
  var close=(Close)Bind(module,"?Close@BlockDatabase_t@@QAEHXZ",typeof(Close));
  IntPtr self=Marshal.AllocHGlobal(4096);Marshal.Copy(new byte[4096],0,self,4096);
  Console.WriteLine("Construct with database runtime initialization");ctor(self,true);
  Console.WriteLine("Opening database read-only");
  int status=open(self,path,true,false);Console.WriteLine("Open(read-only): "+status);
  if(status!=0) {
   throw new Exception("Native database open failed");
  }
  try {
   for(int index=0;index<ids.Length;index++) {
    uint id=ids[index];
    uint size=0;IntPtr data=IntPtr.Zero;int result=get(self,types[index],id,ref size,ref data);
    Console.WriteLine("Get "+id+": status="+result+" size="+size);
    if(result!=0 || data==IntPtr.Zero || size==0 || size>=67108864)throw new Exception("Native resource lookup failed for "+id);
    {
     byte[] bytes=new byte[size];Marshal.Copy(data,bytes,0,(int)size);
     using(var hash=SHA256.Create()) {
      string actual=BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
      Console.WriteLine("SHA256 "+id+": "+actual);
      if(actual!=hashes[index])throw new Exception("Native resource hash mismatch for "+id);
     }
    }
   }
  } finally {
   int closed=close(self);Console.WriteLine("Close: "+closed);Marshal.FreeHGlobal(self);
   if(closed!=0)throw new Exception("Native database close failed");
  }
 }
}
'@
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
[uint32[]]$types = @()
[uint32[]]$ids = @()
[string[]]$hashes = @()
$keys = @{}
foreach ($row in $manifest) {
    $key = "$($row.type):$($row.id)"
    if ($keys.ContainsKey($key) -or -not $row.type -or -not $row.id -or $row.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Manifest identity/hash missing or duplicated' }
    $keys[$key] = $true
    $types += [uint32]$row.type
    $ids += [uint32]$row.id
    $hashes += [string]$row.sha256
}
[NativeRdbProbe]::Run($GamePath,$DatabasePath, $types, $ids, $hashes)
Write-Output "All $($ids.Count) selected texture payloads verified through the client-native reader."

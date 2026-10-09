param([ValidateSet('Status','Read','Provision')][string]$Mode='Status')
$ErrorActionPreference='Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class GraduationVault {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
 public struct Credential {
  public uint Flags, Type; public string TargetName, Comment;
  public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
  public uint CredentialBlobSize; public IntPtr CredentialBlob; public uint Persist, AttributeCount;
  public IntPtr Attributes; public string TargetAlias, UserName;
 }
 [DllImport("advapi32.dll", EntryPoint="CredReadW", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern bool ReadNative(string target,uint type,uint flags,out IntPtr ptr);
 [DllImport("advapi32.dll", EntryPoint="CredWriteW", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern bool WriteNative(ref Credential value,uint flags);
 [DllImport("advapi32.dll")] static extern void CredFree(IntPtr ptr);
 public static string Read(string target) {
  IntPtr ptr; if(!ReadNative(target,1,0,out ptr)) {
   int e=Marshal.GetLastWin32Error(); if(e==1168) return null;
   throw new System.ComponentModel.Win32Exception(e);
  }
  try {var c=(Credential)Marshal.PtrToStructure(ptr,typeof(Credential)); return Marshal.PtrToStringUni(c.CredentialBlob,(int)c.CredentialBlobSize/2);}
  finally {CredFree(ptr);}
 }
 public static void Write(string target,string user,string secret) {
  IntPtr blob=Marshal.StringToCoTaskMemUni(secret);
  try {
   var c=new Credential {Type=1,TargetName=target,UserName=user,CredentialBlob=blob,CredentialBlobSize=(uint)(secret.Length*2),Persist=2};
   if(!WriteNative(ref c,0)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  } finally {Marshal.ZeroFreeCoTaskMemUnicode(blob);}
 }
}
'@
$dbTarget='BigDataGraduationProject/MySQL'
$jwtTarget='BigDataGraduationProject/JWT'
$db=[GraduationVault]::Read($dbTarget)
$jwt=[GraduationVault]::Read($jwtTarget)
if($Mode -eq 'Status') {
 @{database_password_present=($null -ne $db);jwt_present=($null -ne $jwt)} | ConvertTo-Json -Compress
 exit 0
}
if($Mode -eq 'Read') {
 if(-not $db -or -not $jwt){throw 'Runtime credentials missing; run Provision first'}
 @{password_b64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($db));jwt_b64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($jwt))} | ConvertTo-Json -Compress
 exit 0
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form=New-Object System.Windows.Forms.Form
$form.Text='Recovered project - Save application credentials'
$form.Size=New-Object System.Drawing.Size(560,240)
$form.StartPosition='CenterScreen'; $form.TopMost=$true
$label=New-Object System.Windows.Forms.Label
$label.Text='Enter existing bigdata_dev password. It will be tested and stored in Windows Credential Manager. No database account will be changed.'
$label.Location=New-Object System.Drawing.Point(20,15); $label.Size=New-Object System.Drawing.Size(510,60)
$form.Controls.Add($label)
$box=New-Object System.Windows.Forms.TextBox
$box.Location=New-Object System.Drawing.Point(20,90); $box.Width=510; $box.UseSystemPasswordChar=$true
$form.Controls.Add($box)
$button=New-Object System.Windows.Forms.Button
$button.Text='Test and securely save'
$button.Location=New-Object System.Drawing.Point(270,140); $button.Size=New-Object System.Drawing.Size(260,32)
$form.Controls.Add($button)
$button.Add_Click({
 $button.Enabled=$false
 try {
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName='C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
  $info.Arguments='--no-defaults --host=127.0.0.1 --port=3306 --user=bigdata_dev --database=bigdata_graduation --batch --execute="SELECT 1;"'
  $info.EnvironmentVariables['MYSQL_PWD']=$box.Text
  $info.UseShellExecute=$false; $info.CreateNoWindow=$true
  $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
  $p=New-Object System.Diagnostics.Process; $p.StartInfo=$info
  [void]$p.Start(); $null=$p.StandardOutput.ReadToEnd(); $null=$p.StandardError.ReadToEnd(); $p.WaitForExit()
  $info.EnvironmentVariables.Remove('MYSQL_PWD')
  if($p.ExitCode -ne 0){throw 'Application login failed'}
  [GraduationVault]::Write($dbTarget,'bigdata_dev',$box.Text)
  if(-not $jwt){
   $bytes=New-Object byte[] 48
   $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); $rng.Dispose()
   $jwt=[Convert]::ToBase64String($bytes)
   [GraduationVault]::Write($jwtTarget,'backend',$jwt)
  }
  $box.Clear()
  [System.Windows.Forms.MessageBox]::Show('Login passed. Credentials saved securely; no plaintext password file was created.') | Out-Null
  $form.Close()
 } catch {
  [System.Windows.Forms.MessageBox]::Show('Unable to verify or save. Re-enter the existing application password. No password was logged.') | Out-Null
  $button.Enabled=$true
 }
})
$form.AcceptButton=$button
[void]$form.ShowDialog()

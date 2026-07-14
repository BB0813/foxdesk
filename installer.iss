; FoxDesk Inno Setup Script
; Requires: Inno Setup 6+

#define MyAppName "FoxDesk"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "FoxDesk"
#define MyAppURL "https://github.com/BB0813/foxdesk"
#define MyAppExeName "FoxDesk.exe"

[Setup]
AppId={{B9F7E5A0-4C2D-4E8F-9A1B-3D6C7F8E2A50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
; Per-user default avoids Program Files permission traps for uninstall/upgrade.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=FoxDesk-{#MyAppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=100
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=LICENSE
SetupIconFile=static\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=force
RestartApplications=no
; Prefer new per-user path even if an older Program Files install exists.
UsePreviousAppDir=no
CreateUninstallRegKey=yes
UninstallDisplayName={#MyAppName}
InfoBeforeFile=
; Windows VERSIONINFO fields must be numeric (x.y.z[.w]); beta labels stay in AppVersion/AppVerName.
VersionInfoVersion=1.2.0.0
VersionInfoProductVersion=1.2.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "dist\FoxDesk\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\FoxDesk\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Always remove install dir leftovers (logs, broken half-updates, etc.)
[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}"
Type: files; Name: "{userdesktop}\{#MyAppName}.lnk"
Type: files; Name: "{commondesktop}\{#MyAppName}.lnk"
Type: files; Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}.lnk"
Type: filesandordirs; Name: "{group}"
; Temp single-instance lock
Type: filesandordirs; Name: "{%TEMP}\{#MyAppName}"

[Code]
var
  RemoveUserData: Boolean;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  RemoveUserData := False;
  // Stop running FoxDesk / worker processes before files are locked.
  Exec('taskkill.exe', '/F /IM {#MyAppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Ask whether to wipe app data (profiles/proxies/setup markers).
  if MsgBox(
       '是否同时删除用户数据？' + #13#10 + #13#10 +
       '包括配置档案、代理池、运行时缓存与首次引导标记：' + #13#10 +
       ExpandConstant('{userappdata}\FoxDesk') + #13#10 +
       ExpandConstant('{userappdata}\CamoufoxManager') + ' (旧版)' + #13#10 + #13#10 +
       '选择「是」= 完全卸载（推荐重装前使用）' + #13#10 +
       '选择「否」= 仅删除程序，保留配置',
       mbConfirmation, MB_YESNO) = IDYES then
  begin
    RemoveUserData := True;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  LegacyDir: String;
  LegacyLocal: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Extra sweep for leftover shortcuts / empty dirs.
    DeleteFile(ExpandConstant('{userdesktop}\{#MyAppName}.lnk'));
    DeleteFile(ExpandConstant('{commondesktop}\{#MyAppName}.lnk'));
    DeleteFile(ExpandConstant('{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}.lnk'));
    DelTree(ExpandConstant('{group}'), True, True, True);
    DelTree(ExpandConstant('{%TEMP}\{#MyAppName}'), True, True, True);
    DelTree(ExpandConstant('{app}'), True, True, True);

    if RemoveUserData then
    begin
      DataDir := ExpandConstant('{userappdata}\FoxDesk');
      LegacyDir := ExpandConstant('{userappdata}\CamoufoxManager');
      LegacyLocal := ExpandConstant('{localappdata}\CamoufoxManager');
      if DirExists(DataDir) then
        DelTree(DataDir, True, True, True);
      if DirExists(LegacyDir) then
        DelTree(LegacyDir, True, True, True);
      if DirExists(LegacyLocal) then
        DelTree(LegacyLocal, True, True, True);
      // Camoufox browser cache is shared; only remove FoxDesk-managed data above.
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Ensure previous instance is not locking files during upgrade install.
  Exec('taskkill.exe', '/F /IM {#MyAppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

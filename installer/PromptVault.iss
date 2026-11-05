; Inno Setup script. Called by CI:
;   ISCC /DAppVersion=1.0.0 /DArch=x64|arm64 /DSourceDir=<pyinstaller folder> installer\PromptVault.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef Arch
  #define Arch "x64"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\PromptVault"
#endif

[Setup]
AppId={{7B1D5C2E-3A6F-4E0B-9B58-5F2C8D14A7E3}
AppName=Prompt Vault
AppVersion={#AppVersion}
AppVerName=Prompt Vault {#AppVersion}
AppPublisher=Sadroddin Aghaei
AppCopyright=Copyright (c) 2026 Sadroddin Aghaei. All Rights Reserved.
DefaultDirName={autopf}\Prompt Vault
DefaultGroupName=Prompt Vault
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=PromptVault-{#AppVersion}-windows-{#Arch}-setup
SetupIconFile=..\assets\icons\promptvault.ico
UninstallDisplayIcon={app}\PromptVault.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
#if Arch == "arm64"
ArchitecturesAllowed=arm64
ArchitecturesInstallIn64BitMode=arm64
#else
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Prompt Vault"; Filename: "{app}\PromptVault.exe"
Name: "{autodesktop}\Prompt Vault"; Filename: "{app}\PromptVault.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PromptVault.exe"; Description: "{cm:LaunchProgram,Prompt Vault}"; Flags: nowait postinstall skipifsilent

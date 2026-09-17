; ==============================================================================
; INNO SETUP SCRIPT — YT AUTOMATION STUDIO
; ==============================================================================

#define MyAppName "YT Automation Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "YT Automation Studio"
#define MyAppURL "https://github.com/yt-automation-studio"
#define MyAppExeName "YTAutomationStudio.exe"
#define MyAppIconPath "..\assets\icon.ico"

[Setup]
AppId={{D9A35F4C-5B1E-47F1-A8D2-E40B7E0911A3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=YT-Automation-Studio-Setup
SetupIconFile={#MyAppIconPath}
UninstallDisplayIcon={app}\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; Pre-create the local Windows video automation directory structure
Name: "{userdocs}\YT-Automation"
Name: "{userdocs}\YT-Automation\INBOX"
Name: "{userdocs}\YT-Automation\PROCESSING"
Name: "{userdocs}\YT-Automation\APPROVED"
Name: "{userdocs}\YT-Automation\UPLOADING"
Name: "{userdocs}\YT-Automation\UPLOADED"
Name: "{userdocs}\YT-Automation\FAILED"
Name: "{userdocs}\YT-Automation\ARCHIVE"
Name: "{userdocs}\YT-Automation\THUMBNAILS"
Name: "{userdocs}\YT-Automation\TEMP"

[Files]
; Copy packaged binary and application files
Source: "..\dist\YTAutomationStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copy icon assets
Source: "..\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
; Copy initial configuration and schema
Source: "..\database\migrations\001_initial_schema.sql"; DestDir: "{app}\database\migrations"; Flags: ignoreversion
Source: "..\database\seed\seed_data.sql"; DestDir: "{app}\database\seed"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

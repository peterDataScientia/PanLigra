Unicode true
!include "MUI2.nsh"
Name "PanLigra"
OutFile "PanLigra-Setup.exe"
InstallDir "$LOCALAPPDATA\\Programs\\PanLigra"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "PanLigra" SEC01
  SetOutPath "$INSTDIR"
  File /r "..\\dist\\PanLigra\\*"
  CreateDirectory "$SMPROGRAMS\\PanLigra"
  CreateShortcut "$SMPROGRAMS\\PanLigra\\PanLigra.lnk" "$INSTDIR\\PanLigra.exe"
  CreateShortcut "$DESKTOP\\PanLigra.lnk" "$INSTDIR\\PanLigra.exe"
  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\\PanLigra.lnk"
  Delete "$SMPROGRAMS\\PanLigra\\PanLigra.lnk"
  RMDir "$SMPROGRAMS\\PanLigra"
  RMDir /r "$INSTDIR"
SectionEnd

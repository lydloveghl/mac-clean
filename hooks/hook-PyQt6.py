from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas, binaries, hiddenimports = collect_all('PyQt6')
hiddenimports += collect_submodules('PyQt6')
datas += copy_metadata('PyQt6')
datas += copy_metadata('PyQt6-sip')

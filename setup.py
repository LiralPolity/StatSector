from cx_Freeze import setup, Executable

included_files = ['test_combat_entities_data.json']

setup(name = "StatSector" ,
      version = "0.1" ,
      description = "" ,
      options = {'build_exe': {'include_files': included_files}},
      executables = [Executable("main.py")])


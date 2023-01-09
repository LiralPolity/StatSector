"""
Database of all ship and weapon information, divided into one
section for each mod alongside one for vanilla, sub-divided
into one sub-section for ship_data.csv, one sub-section for
weapon_data.csv, and one sub-section for all ship files.
"""
import sys
import os
import csv
import json
from sys import platform
import decimal
from decimal import Decimal


_IDS_OF_MODS_CAUSING_ERRORS = (
    'armaa',
    'gundam_uc',
    'SCY'
)


_WEAPON_DATA_CSV_COLUMN_DATA_TYPES = {
    "name" : str,
    "id" : str,
    "tier" : int,
    "rarity" : Decimal,
    "base value" : int,
    "range" : Decimal,
    "damage/second" : Decimal,
    "damage/shot" : Decimal,
    "emp" : Decimal,
    "impact" : Decimal,
    "turn rate" : Decimal,
    "OPs" : int,
    "ammo" : int,
    "ammo/sec" : Decimal,
    "reload size" : int,
    "type" : str,
    "energy/shot" : Decimal,
    "energy/second" : Decimal,
    "chargeup" : Decimal,
    "chargedown" : Decimal,
    "burst size" : Decimal, 
    "burst delay" : Decimal,
    "min spread" : Decimal,
    "max spread" : Decimal,
    "spread/shot" : Decimal,
    "spread decay/sec" : Decimal,
    "beam speed" : Decimal,
    "proj speed" : Decimal,
    "launch speed" : Decimal,
    "flight time" : Decimal,
    "proj hitpoints" : int,
    "autofireAccBonus" : Decimal, 
    "extraArcForAI" : Decimal,
    "hints" : str,
    "tags" : str,
    "groupTag" : str,
    "tech/manufacturer" : str,
    "for weapon tooltip>>" : str,
    "primaryRoleStr" : str,
    "speedStr" : str,
    "trackingStr" : str,
    "turnRateStr" : str,
    "accuracyStr" : str,
    "customPrimary" : str,
    "customPrimaryHL" : str,
    "customAncillary" : str,
    "customAncillaryHL" : str,
    "noDPSInTooltip" : bool,
    "number" : Decimal
}

_SHIP_DATA_CSV_COLUMN_DATA_TYPES = {
    "name" : str,
    "id" : str,
    "designation" : str,
    "tech/manufacturer" : str,
    "system id" : str,
    "fleet pts" : int,
    "hitpoints" : int,
    "armor rating" : int,
    "max flux" : int,
    "8/6/5/4%" : Decimal,
    "flux dissipation" : int,
    "ordnance points" : int,
    "fighter bays" : int,
    "max speed" : Decimal,
    "acceleration" : Decimal,
    "deceleration" : Decimal,
    "max turn rate" : Decimal,
    "turn acceleration" : Decimal,
    "mass" : int,
    "shield type" : str,
    "defense id" : str,
    "shield arc" : Decimal,
    "shield upkeep" : Decimal,
    "shield efficiency" : Decimal,
    "phase cost" : Decimal,
    "phase upkeep" : Decimal,
    "min crew" : int, 
    "max crew" : int,
    "cargo" : int,
    "fuel" : int,
    "fuel/ly" : Decimal,
    "range" : Decimal,
    "max burn" : int, 
    "base value" : int,
    "cr %/day" : Decimal,
    "CR to deploy" : int,
    "peak CR sec" : Decimal, 
    "CR loss/sec" : Decimal,
    "supplies/rec" : int,
    "supplies/mo" : Decimal,
    "c/s" : Decimal, 
    "c/f" : Decimal,
    "f/s" : Decimal, 
    "f/f" : Decimal,
    "crew/s" : Decimal,
    "crew/f" : Decimal,
    "hints" : str, 
    "tags" : str,
    "rarity" : Decimal,
    "breakProb" : Decimal, 
    "minPieces" : int,
    "maxPieces" : int,
    "travel drive" : str, 
    "number" : Decimal
}


def is_executable() -> bool:
    """
    Return whether this code is executable or not.
    """
    return getattr(sys, "frozen", False)


def get_path(file_name: str) -> str:
    """
    Return the path of the file of this name.

    file_name - name of this file
    """
    data_directory = (os.path.dirname(sys.executable)
                      if is_executable() #get from system
                      else os.path.dirname(__file__)) #get locally
    return os.path.join(data_directory, file_name)


def _subdirectory_paths(path: str) -> tuple:
    """
    Return a list of the relative paths of the directories within this
    one.

    path - a path
    """
    return tuple(f.path for f in os.scandir(path) if f.is_dir())


def _csv_dictionary(file_name: str) -> dict:
    """
    Return a .csv as a flat dictionary keyed by row, with elements typed
    by column.
    """
    types = (_WEAPON_DATA_CSV_COLUMN_DATA_TYPES
             if file_name == "weapon_data.csv" else
             _SHIP_DATA_CSV_COLUMN_DATA_TYPES)
    with open(file_name) as f:
        rows = tuple(row for row in csv.reader(f))
    column_names = rows[0]
    dictionary = {}
    for row in rows[1:]:
        ID = row[1]
        if ID == "": continue
        dictionary[ID] = {}
        for i, value in enumerate(row):
            if value == "": continue
            column_name = column_names[i]
            data_type = types[column_name]
            if data_type != str: value = data_type(value)
            dictionary[ID][column_name] = value
    return dictionary


def _data_dictionary(path: str):
    """
    Return a dictionary of the data of the ships and weapons of this source,
    organized by item.
    """
    source = {}
    directories = [os.path.basename(sub_path) for sub_path in
                   _subdirectory_paths(path)]
    if 'weapons' in directories:
        os.chdir('weapons')
        if 'weapon_data.csv' in os.listdir(os.getcwd()):
            source['weapons'] = _csv_dictionary('weapon_data.csv')
            for weapon_id in source["weapons"]:
                if weapon_id + '.wpn' in os.listdir(os.getcwd()):
                    with open(weapon_id + '.wpn') as f:
                        lines = [line.split("#")[0] + "\n" if "#" in line
                                 else line for line in f.readlines()]
                        for line in lines:
                            if "specClass" in line:
                                source["weapons"][weapon_id]["specClass"] = (
                                    line.split(":")[1].split('"')[1])
                            if "type" in line:
                                source["weapons"][weapon_id]["type"] = (
                                    line.split(":")[1].split('"')[1])
                                                                             
        os.chdir('..')
    if 'hulls' in directories:
        os.chdir('hulls')
        if 'ship_data.csv' in os.listdir(os.getcwd()):
            source['ships'] = _csv_dictionary('ship_data.csv')
            for ship_id in source["ships"]:
                if ship_id + '.ship' in os.listdir(os.getcwd()):
                    with open(ship_id + '.ship') as f:
                        source["ships"][ship_id].update(json.load(f))        
        os.chdir('..')
    return source


def _is_mod_causing_errors(path: str) -> bool:
    with open('mod_info.json') as f:
        lines = f.readlines()
    for line in lines:
        if '"id"' in line:
            for ID in _IDS_OF_MODS_CAUSING_ERRORS:
                if ID in line: return True
    return False


def dictionary():
    """
    Returns a dictionary of all mod csv and .ship file data.

    Loads every weapon_data.csv, ship_data.csv, and .ship file from the
    vanilla folder and mods folder and returns the necessary data as a
    flat dictionary.

    The structure of this dictionary is 
    {
        "ships":{
            "shipId":{
                "attributeId":value
            }
        },
        "weapons" : {
            "weaponId":{
                "attributeId":value
            }
        }
    }

    where every shipId, weaponId, and attributeId is taken from the game
    or mod files.

    methods:
    - weapon_data
    - ship_data
    """

    decimal.places = 6

    #navigate to mods folder
    if is_executable():
        os.chdir(os.path.dirname(sys.executable))
    while os.path.basename(os.getcwd()) != 'mods': os.chdir('..')
        
    #add mod data
    data = dict()
    for path in _subdirectory_paths(os.getcwd()):
        os.chdir(path)
        if 'mod_info.json' not in os.listdir(os.getcwd()): continue
        if _is_mod_causing_errors(path):
            print(("WARNING: mod at", path, "not loaded because its"
                    ".csv or .ship files cause errors."))
            continue
        try:
            os.chdir(path + "/data")
        except:
            data[path] = {}
            continue;
        data[path] = _data_dictionary(os.getcwd())
        os.chdir("..")
        

    #navigate to vanilla folder
    os.chdir("..")
    os.chdir("..")
    if platform == "win32": os.chdir("starsector-core/data")
    elif platform == "darwin": os.chdir("Contents/Resources/Java/data")
    #elif platform == "linux": self._vanilla_path = linux path 

    #add vanilla data
    data['vanilla'] = _data_dictionary(os.getcwd())

    return data

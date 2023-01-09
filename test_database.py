"""
Test suite for the database module.
"""

# Bring packages onto the path
import sys, os
sys.path.append(os.path.abspath(os.path.join('..', 'src')))

import database


def test_Database():
    """
    Check if the database loads and check the output.

    Check if the vanilla data has loaded as expected.
    """
    #load the database
    base = database.dictionary()

    #check a few common weapons in weapon_data.csv
    ids_of_expected_weapons = "flak", "harpoon", "irpulse"
    ids_of_expected_weapon_attributes = "name", "id", "OPs"
    for weapon_id in ids_of_expected_weapons:
        assert base["vanilla"]["weapons"][weapon_id]
        weapon_data = base["vanilla"]["weapons"][weapon_id]
        assert isinstance(weapon_data, dict)
        for weapon_attribute_id in ids_of_expected_weapon_attributes:
            assert weapon_attribute_id in weapon_data
            

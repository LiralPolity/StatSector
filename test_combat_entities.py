import combat_entities
import numpy as np
import pytest
import json
import time
import os, sys
import decimal
from decimal import Decimal


decimal.places = 6

        
def _data():
    with open('test_combat_entities_data.json') as f:
        return json.load(f)["Shot.damage_armor_grid"]


def _decimal_places(data):
    return data["test_config"]["decimal_places"]


def _hit_probability(bound: float): return 1 / 12#hardcoded dummy for test


def _armor_grid(data):
    return combat_entities.ArmorGrid(data["armor_grid_spec"]["armor_rating"],
                                     data["armor_grid_spec"]["cell_size"],
                                     data["armor_grid_spec"]["width"])


def _big_energy_shot(data):
    return combat_entities.Shot(data["shot_spec"]["damage"],
                                data["shot_spec"]["damage_type"],
                                data["shot_spec"]["beam"],
                                data["shot_spec"]["flux_hard"])

def _dominator(data):
    spec = (14_000,#hull
            1_000,#flux_capacity
            100)#flux_dissipation)
    return combat_entities.Ship([], _armor_grid(data), *spec)


def test_armor_grid_constructor():
    data = _data()
    armor_grid = _armor_grid(data)
    rounded_grid = np.round(armor_grid.cells, _decimal_places(data))
    expected_grid = np.array(data["armor_grid_cell_values"]["initial"])
    condition = (rounded_grid == expected_grid).all()
    assert condition, "Initial armor grid does not equal expected one."


def test_armor_slab_creation():
    data = _data()
    x_bounds = data["bounds"][::2]
    width_pixels = max(x_bounds) - min(x_bounds)
    cell_size = data["armor_grid_spec"]["cell_size"]
    width_cells = int(width_pixels / cell_size)
    armor_grid = combat_entities.ArmorGrid(
        data["armor_grid_spec"]["armor_rating"],
        cell_size,
        width_cells)
    print(armor_grid.cells)

    
def test_damage_armor_grid():
    data = _data()
    armor_grid = _armor_grid(data)
    shot = _big_energy_shot(data)
    ship = _dominator(data)
    decimal_places = _decimal_places(data)
    expected_armor_grids = data["armor_grid_cell_values"]["after_shots"]
    shot.distribute(ship, _hit_probability)
    
    for i, expected_armor_grid in enumerate(expected_armor_grids):
        damage_distribution = (shot._expected_armor_damage
                               * armor_grid.damage_factors(shot._strength))
        for j, damage in enumerate(damage_distribution):
            shot.damage_armor_grid(armor_grid, damage, j)
        ship.armor_grid.cells = np.maximum(0, armor_grid.cells)
        assert (np.round(armor_grid.cells, decimal_places)
                == np.array(expected_armor_grid)).all(), (
                "Armor grid after shot", i, "does not equal expected one.")
        

def _simulate_hit(shot: object, ship: object, index: int):
    pooled_armor = max(ship.armor_grid._minimum_armor,
                       ship.armor_grid._pool(index))
    damage_factor = max(combat_entities.ArmorGrid._MINIMUM_DAMAGE_FACTOR, 
                        1 / (1 + pooled_armor / shot._strength))
    damage = shot._armor_damage * damage_factor
    shot.damage_armor_grid(ship.armor_grid, damage, index)
    hull_damage = np.sum(ship.armor_grid.cells[ship.armor_grid.cells<0])
    ship.hull = max(0, ship.hull + hull_damage)
    ship.armor_grid.cells = np.maximum(0, ship.armor_grid.cells)
    

def _test_calculation_vs_simulation():
    #setup
    data = _data()
    shot = _big_energy_shot(data)
    calculated_ship = _dominator(data)
    simulated_ship = _dominator(data)
    shot.distribute(calculated_ship, _hit_probability)
    trials = 1_000

    start = time.perf_counter()
    #calculate
    calculated_firings = 0
    while calculated_ship.hull > 0:
        shot.damage_ship(calculated_ship)
        calculated_firings += 1
    calculation_duration = time.perf_counter() - start
    
    start = time.perf_counter()
    #simulate
    simulated_firings = 0
    simulated_hull_variance = 0
    for trial in range(trials):
        firing = 0
        while simulated_ship.hull > 0:
            index = np.random.randint(0, len(simulated_ship.armor_grid.bounds))
            _simulate_hit(shot, simulated_ship, index)
            if firing == calculated_firings:
                simulated_hull_variance += simulated_ship.hull ** 2
            firing += 1
        simulated_ship.armor_grid = _armor_grid(data)
        simulated_ship.hull = 14_000#hardcoded Dominator value
        simulated_firings += firing
    simulation_duration = time.perf_counter() - start
    speedup = simulation_duration / calculation_duration

    print()
    print()
    print("test_calculation_vs_simulation")
    print("simulation trials:", trials)
    print("number of firings to destroy ship")
    print("calculated:", calculated_firings)
    print("average Simulated:", round(simulated_firings / trials))
    print("standard deviation of simulated hull from zero upon firing "
          "calculated to destroy ship:",
          round(np.sqrt(simulated_hull_variance / trials)))
    print("Calculation duration:", calculation_duration)
    print("Simulation duration:", simulation_duration)
    print("Calculation is:", speedup, "times faster.")


def test_hit_sequence():
    distance = 1000
    gun_data = {
        "chargeup" : Decimal(0),
        "chargedown" : Decimal(0.1),
        "burst size" : Decimal(1),
        "burst delay" : Decimal(0),
        "ammo" : Decimal(10),
        "ammo regen" : Decimal(1),
        "reload size" : Decimal(1),
        "proj speed" : Decimal(500),
        "specClass" : "projectile",
        "type" : "ENERGY"
    }
    beam_data = {
        "chargeup" : Decimal(1),
        "chargedown" : Decimal(1),
        "burst size" : Decimal(1),
        "burst delay" : Decimal(0),
        "ammo" : Decimal(7),
        "ammo regen" : Decimal(1 / 7),
        "reload size" : Decimal(3),
        "proj speed" : Decimal(1000),
        "type" : "ENERGY",
        "specClass" : "beam"
    }
    
    gun = combat_entities.Weapon(gun_data)
    beam = combat_entities.Weapon(beam_data)
    gun.hit_sequence = gun._hit_sequence(distance)
    beam.hit_sequence = beam._hit_sequence(distance)
    
    print()
    print()
    print("test_hit_sequence")
    print("Expected hit sequence")
    print("Gun")
    print(gun.hit_sequence)
    print("Beam")
    print(beam.hit_sequence)

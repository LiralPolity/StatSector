import numpy as np
import copy
import decimal
from decimal import Decimal
"""
Damage computing module.

methods:
- hit_probability
- main

classes:
- ArmorGrid
- Ship
- Shot
- Weapon
"""
decimal.getcontext().prec = 6


class ArmorGrid:
    """
    A Starsector ship armor grid.
    
    - Represents a horizontal frontal row of armor on a ship.
    - Includes 2 rows of vertical padding above; 2 below; 2 columns of
      left horizontal padding; 2 right.
    
    constants:
    _MINIMUM_ARMOR_FACTOR - multiply by armor rating to determine 
                            minimum effective value of pooled armor for 
                            damage calculations
    _MINIMUM_DAMAGE_FACTOR - least factor whereby this ArmorGrid can
                             cause incoming damage to be multiplied
    ARMOR_RATING_PER_CELL_FACTOR - multiply by armor rating to determine
                                   initial value of each cell of an 
                                   ArmorGrid
    WEIGHTS - multiply by damage to the central cell to determine damage
              to surrounding ones
              
    variables:
    _minimum_armor - minimum effective value of armor for damage 
                     calculations
    bounds - right bound of each cell in the middle row, except the two
             padding cells on both sides
    cells - 2d array of armor grid cell values
    
    methods:
    - _pooled_values
    - damage_factors
    """
    _MINIMUM_ARMOR_FACTOR = 0.05
    _MINIMUM_DAMAGE_FACTOR = 0.15
    ARMOR_RATING_PER_CELL_FACTOR = 1 / 15
    POOLING_WEIGHTS = np.array([[0.0, 0.5, 0.5, 0.5, 0.0],
                                [0.5, 1.0, 1.0, 1.0, 0.5],
                                [0.5, 1.0, 1.0, 1.0, 0.5],
                                [0.5, 1.0, 1.0, 1.0, 0.5],
                                [0.0, 0.5, 0.5, 0.5, 0.0]])
    DAMAGE_DISTRIBUTION = ARMOR_RATING_PER_CELL_FACTOR * POOLING_WEIGHTS
    
    def __init__(self, armor_rating: float, cell_size: float, width: int):
        """
        armor_rating - armor rating of the ship to which this ArmorGrid
                       belongs
        cell_size - size, in pixels, of each armor cell, which is square
        width - width of the armor grid in cells
        """
        self._minimum_armor = ArmorGrid._MINIMUM_ARMOR_FACTOR * armor_rating
        armor_per_cell = armor_rating * ArmorGrid.ARMOR_RATING_PER_CELL_FACTOR
        self.cells = np.full((5,width+4), armor_per_cell)
        self.bounds = np.arange(0, width) * cell_size

    def _pool(self, index):
        """
        Return the armor value pooled around a cell at this index.

        The cell must be after the second and before the second to last
        one of the middle row.
        """
        return np.sum(ArmorGrid.POOLING_WEIGHTS * self.cells[0:5,index:index+5])
        
    def _pooled_values(self) -> object:
        """
        Return the armor value pooled around each cell of the middle
        row, from third through third-last.
        """
        return np.maximum(self._minimum_armor,
                          np.array([self._pool(i) for i, _ in
                                    enumerate(self.cells[2,2:-2])]))
                  
    def damage_factors(self, hit_strength: float) -> object:
        """
        Return the factor whereby to multiply the damage of each
        non-padding cell of the grid.
        """
        return np.maximum(ArmorGrid._MINIMUM_DAMAGE_FACTOR, 
                          1 / (1 + self._pooled_values() / hit_strength))
        
        
class Ship:
    """
    A Starsector ship.
    
    methods:
    - will_overload
    - overloaded
    - shield_up
    
    variables:
    weapons - container of the weapons of the ship, with structure to be
              determined
    armor_grid - ArmorGrid of the ship
    hull - amount of hitpoints the ship has
    flux_capacity - how much flux would overload the ship
    flux_dissipation - how much flux the ship can expel every second when
                       not actively venting
    hard_flux - hard flux amount
    soft_flux - soft flux amount
    """
    def __init__(self, data: dict):
        """
        data - entry from the database dictionary
        """
        self.data = data
        self.hull = data["hitpoints"]
        self.flux_capacity = data["max flux"]
        self.flux_dissipation = data["flux dissipation"]
        height = data["height"]
        cell_size = 15 if height < 150 else height/10 if height < 300 else 30
        width_cells = int(data["width"] / cell_size)
        armor_grid = ArmorGrid(data["armor rating"], cell_size, width_cells)
        self.armor_grid = armor_grid
        self.weapons = []
        self.hard_flux, self.soft_flux = 0, 0
    
    @property
    def will_overload(self) -> bool:
        """
        Return whether the ship will now overload.
        
        A ship will overload if soft or hard flux exceeds
        the flux capacity of the ship.
        """
        return (self.hard_flux > self.flux_capacity 
                or self.soft_flux > self.flux_capacity)
    
    @property
    def overloaded(self) -> bool:
        """
        Return whether the ship is in the overloaded state.
        
        Ignores the duration of overloaded.
        -TODO: Implement overload duration
        """
        return self.will_overload
        
    @property
    def shield_up(self) -> bool: 
        """
        Return whether the shield is up or down.
        
        Presumes the shield to be up if the ship is not overloaded,
        ignoring smart tricks the AI can play to take kinetic damage
        on its armor and save its shield for incoming high explosive 
        damage.
        """
        return not self.overloaded


class Shot:
    """
    A shot fired at a row of armor cells protected by a shield.

    Calculates the expectation value of the damage of a shot with a
    spread to a ship with a shield, armor grid, and random positional
    deviation.
    
    variables:
    damage - amount listed under damage in weapon_data.csv
    shield_damage - damage amount to be inflictedon on a shield
    armor_damage - damage amount to be inflicted on armor 
    strength - strength against armor for armor damage calculation
    flux_hard - whether the flux damage against shields is hard or not
    probabilities - chance to hit each cell of an armor grid at which
                    this Shot is targeted after being instantiated
    
    methods:
    - distribute
    - _damage_distribution
    - damage_armor_grid
    """
    DAMAGE_TYPE_DAMAGE_FACTORS = {
        "KINETIC" : {
            "shield" : 2.0,
            "armor" : 0.5,
        },
        "HIGH_EXPLOSIVE" : {
            "shield" : 0.5,
            "armor" : 2.0
        },
        "FRAGMENTATION" : {
            "shield" : 0.25,
            "armor" : 0.25
        },
        "ENERGY" : {
            "shield" : 1.0,
            "armor" : 1.0
        }
    }
    
    def __init__(
            self, 
            damage: float,
            damage_type: str,
            beam: bool,
            flux_hard: bool):
        """
        damage - amount listed under damage in weapon_data.csv
        damage_type - string listed under damage type in weapon_data.csv
        beam - whether the weapon is a beam or not
        flux_hard - whether flux damage to shields is hard or not
        """
        self._damage = damage
        self._armor_damage_factor = Shot.DAMAGE_TYPE_DAMAGE_FACTORS[
            damage_type]["armor"]
        self._shield_damage = damage * Shot.DAMAGE_TYPE_DAMAGE_FACTORS[
            damage_type]["shield"]
        self._armor_damage = damage * self._armor_damage_factor
        self._strength = self._armor_damage * (0.5 if beam else 1)
        self._flux_hard = flux_hard
        self._probabilities = None
        self._expected_armor_damage = None

    def distribute(self, ship: object, distribution: object):
        """
        Spread hit probability and, accordingly, expected distribution of
        base armor damage over each armor cell of a ship.
        
        Calculate the probability to hit each armor cell of a row and
        save the probabilities and consequent expected armor damage for later
        calculation.
        """
        self._probabilities = np.vectorize(distribution)(ship.armor_grid.bounds)
        self._expected_armor_damage = self._armor_damage * self._probabilities
        
    def damage_armor_grid(self, armor_grid: object, damage: float, i: int):
        """
        Distribute across this ArmorGrid this amount of damage at
        this index.

        Note: may reduce armor cell values below zero.

        armor_grid - ArmorGrid instance
        """
        armor_grid.cells[0:5,i:i+5] -= damage * ArmorGrid.DAMAGE_DISTRIBUTION

    def damage_ship(self, ship: object):
        """
        Apply the expected values of shield, armor, and hull damage to a
        ship.

        ship - Ship instance
        """
        if False: pass #TODO: implement shield check
        damage_distribution = (
            self._expected_armor_damage
            * ship.armor_grid.damage_factors(self._strength))
        for i, damage in enumerate(damage_distribution):
            self.damage_armor_grid(ship.armor_grid, damage, i)
        hull_damage = (np.sum(ship.armor_grid.cells[ship.armor_grid.cells<0])
                       / self._armor_damage_factor)
        ship.hull = max(0, ship.hull + hull_damage)
        ship.armor_grid.cells = np.maximum(0, ship.armor_grid.cells)


class AmmoTracker:
    """
    Holds and regenerates weapon ammunition. 
    """
    def __init__(self, weapon: object):
        self.weapon = weapon
        self.ammo = weapon.ammo
        self.ammo_regen_time = 1 / weapon.ammo_regen
        self.ammo_regenerated = Decimal(0)
        self.ammo_regen_timer = Decimal(0)
        self.regenerating_ammo = False
    
    def should_regenerate_ammo(self, time: float) -> bool:
        return time - self.ammo_regen_timer >= self.ammo_regen_time
    
    def regenerate_ammo(self, time: float):
        amount = int(self.weapon.ammo_regen * (time - self.ammo_regen_timer))
        self.ammo_regenerated += amount
        self.ammo_regen_timer += amount / self.weapon.ammo_regen
        if self.ammo_regenerated >= self.weapon.reload_size:
            self.ammo += self.ammo_regenerated
            self.ammo_regenerated = 0
        if self.ammo >= self.weapon.ammo:
            self.ammo = self.weapon.ammo
            self.regenerating_ammo = False
        
                        
class Weapon:
    """
    A weapon for a Starsector ship in simulated battle.
    
    Is carried by a Ship instance, contains a shot with some
    distribution, and fires that shot at a target.

    constants:
    MINIMUM_REFIRE_DELAY - Starsector keeps weapons from firing more
                           than once every 0.05 seconds

    variables:
    shot - projectile, missile, or beam tick of the weapon
    distribution - function returning the probability of the shot to
                   hit between two bounds
    """
    MINIMUM_REFIRE_DELAY = Decimal(0.05)
    
    def __init__(self, data: dict):
        """
        data - relevant game file information
        """
        #parse data
        self.data = data
        self.charge_up = data["chargeup"]
        self.charge_down = data["chargedown"]
        self.burst_size = data["burst size"]
        self.burst_delay = data["burst delay"]
        self.ammo = int(data["ammo"]) if "ammo" in data else "UNLIMITED"
        self.ammo_regen = (data["ammo regen"] if "ammo regen" in data
                          else Decimal(0))
        self.reload_size = (data["reload size"] if "reload size" in data
                           else Decimal(0))
        self.proj_speed = data["proj speed"]
        #determine mode
        self.mode = None
        if data["specClass"] == "projectile":
            if data["type"] == "BALLISTIC" or "ENERGY": self.mode = "GUN"
            else: self.mode = "MISSILE"
        elif data["specClass"] == "BEAM":
            if data["damage/shot"] in data: self.mode = "BURST_BEAM"
            else: self.mode = "CONTINUOUS_BEAM"
        #parse remaining data based on mode
        if self.burst_delay > 0 or self.mode == "BEAM":
            self.burst_delay = max(self.burst_delay, 
                                   Weapon.MINIMUM_REFIRE_DELAY)
        if self.mode == "GUN":
            self.burst_size = int(self.burst_size)
            self.charge_down = max(self.charge_down, 
                                   Weapon.MINIMUM_REFIRE_DELAY)
        #uninitialized attributes
        self.hit_sequence = None
        self.shot = None
        self.distribution = None
        
    def fire(self, ship: object):
        """
        Fire the shot of this weapon at that ship.
        
        ship - a Ship instance
        """
        self.shot.distribute(ship, self.distribution)
        #TODO: implement general hit ship method on Shot
        self.shot.damage_ship(ship)
        return #future code below
        if ship.shield_up: 
            pass #TODO: implement shield damage, overloading, etc.
        else: self.shot.damage_armor_grid(ship)

    def _gun_hit_sequence(self, distance: float) -> list:
        time = Decimal(0)  
        time_limit = Decimal(100)
        time_interval = Decimal(1)
        time_intervals = int(time_limit / time_interval)
        travel_time = Decimal(distance / self.proj_speed)
        ammo_tracker = AmmoTracker(self)
        times = []

        def _simultaneous_shots():
            for i in range(self.burst_size):
                if ammo_tracker.ammo == 0: continue
                times.append(time + travel_time)
                ammo_tracker.ammo -= 1
                if not ammo_tracker.regenerating_ammo:
                    ammo_tracker.ammo_regen_timer = time
                    ammo_tracker.regenerating_ammo = True

        def _successive_shots():
            for i in range(self.burst_size):
                if ammo_tracker.ammo == 0: continue
                times.append(time + travel_time)
                time += self.burst_delay
                ammo_tracker.ammo -= 1
                if not ammo_tracker.regenerating_ammo:
                    ammo_tracker.ammo_regen_timer = time
                    ammo_tracker.regenerating_ammo = True
                if ammo_tracker.should_regenerate_ammo(time): 
                    ammo_tracker.regenerate_ammo(time)

        shot_pattern = (_simultaneous_shots if self.burst_delay == 0 else
                        _successive_shots)
            
        while time < time_limit:
            time += self.charge_up
            if ammo_tracker.should_regenerate_ammo(time): 
                ammo_tracker.regenerate_ammo(time)
            shot_pattern()
            time += self.charge_down
            if ammo_tracker.should_regenerate_ammo(time): 
                ammo_tracker.regenerate_ammo(time)
        return ([len([t for t in times if 0 <= int(t) <= time_interval])]
                + [len([t for t in times if (i - 1) * time_interval < int(t)
                                            <= i * time_interval])
                       for i in range(1, time_intervals)])
            

    def _hit_sequence(self, distance: float) -> list:
        """
        Return a hit sequence for a weapon against some target at a 
        distance.
            
        times in seconds, self.ammo_regen is in ammo / second
        """
        if self.mode == "GUN": return self._gun_hit_sequence(distance)
            
        if self.mode == "CONTINUOUS_BEAM":
            chargeup_ticks = self.charge_up / beam_tick
            charge_down_ticks = self.charge_down / beam_tick
            burst_ticks = self.burst_size / beam_tick
            intensities = []
            #for i in range(chargeup_ticks):
                #beam intensity scales quadratically while charging up
            while time < time_limit:
                times.append(time + travel_time)
                intensities.append(1)
                time += beam_tick
            return [sum([intensity for i, intensity in enumerate(intensities) 
                            if t - 1 < times[i] < t])
                         for t in range(time_intervals)]
        
        if self.mode == "BURST_BEAM":
            charge_up_ticks = self.charge_up // beam_tick
            charge_down_ticks = self.charge_down // beam_tick
            burst_ticks = self.burst_size // beam_tick
            times = []
            intensities = []
            while time < time_limit:
                if ammo_tracker.ammo == 0:
                    time += global_minimum_time
                    if ammo_tracker.should_regenerate_ammo(time): 
                        ammo_tracker.regenerate_ammo(time)
                    continue
                
                ammo_tracker.ammo -= 1
                for i in range(charge_up_ticks):
                    times.append(time + travel_time)
                    intensities.append((i * beam_tick) ** 2)
                    time += beam_tick
                    if not ammo_tracker.regenerating_ammo:
                        ammo_tracker.ammo_regen_timer = time
                        ammo_tracker.regenerating_ammo = True
                    if ammo_tracker.should_regenerate_ammo(time): 
                        ammo_tracker.regenerate_ammo(time)
                                        
                for _ in range(burst_ticks):
                    times.append(time)
                    intensities.append(1)
                    time += beam_tick
                    if ammo_tracker.should_regenerate_ammo(time): 
                        ammo_tracker.regenerate_ammo(time)
                        
                for i in range(charge_down_ticks):
                    times.append(time)
                    intensities.append(
                        ((charge_down_ticks - i) * beam_tick) ** 2)
                    time += beam_tick
                    if ammo_tracker.should_regenerate_ammo(time): 
                        ammo_tracker.regenerate_ammo(time)
                                    
                time += self.burst_delay
                if ammo_tracker.should_regenerate_ammo(time): 
                    ammo_tracker.regenerate_ammo(time)
                
            return [sum([intensity for i, intensity in enumerate(intensities) 
                            if t - 1 < times[i] < t])
                         for t in range(time_intervals)]

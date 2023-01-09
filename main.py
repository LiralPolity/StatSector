import database
import combat_entities

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.messagebox import showerror


class DatabaseFrame(ttk.Frame):
    def __init__(self, container: object, dictionary: dict):
        super().__init__(container)

        #internal fields
        self._ships_or_weapons = 'weapons'
        self._data_dictionary = dictionary
        self._viewed_weapon = None
        self._viewed_ship = None
        self._selected_ship = None
        
        #field options
        options = {'padx': 5, 'pady': 5}

        #title label
        title_label = ttk.Label(self, text = "Select")
        title_label.grid(column=0, row=0, columnspan=3)

        #source label
        source_label = ttk.Label(self, text='Source')
        source_label.grid(column=0, row=1, columnspan=3, sticky=tk.W,
                          **options)

        #source entry
        source = tk.StringVar()
        self._source_entry = ttk.Entry(self, textvariable=source)
        self._source_entry.grid(column=0, row=2, columnspan=3, sticky=tk.EW,
                                **options)

        #ships or weapons button
        self._ships_or_weapons_button = ttk.Button(
            self,
            text='weapons',
            command = self.flip)
        self._ships_or_weapons_button.grid(column=0, row=5, sticky=tk.W,
                                           **options)
        
        #identifier label
        identifier_label = ttk.Label(self, text='Identifier')
        identifier_label.grid(column=0, row=3, columnspan=3, sticky=tk.W,
                              **options)

        #identifier entry
        identifier = tk.StringVar()
        self._identifier_entry = ttk.Entry(self, textvariable=identifier)
        self._identifier_entry.grid(column=0, row=4, columnspan=3, sticky=tk.EW, 
                                    **options)

        #result box
        self._result_box = tk.Text(self, height=20, width=30)
        scroll = tk.Scrollbar(self)
        scroll.config(command=self._result_box.yview)
        self._result_box.config(yscrollcommand=scroll.set)
        self._result_box.grid(column=0, row=7, columnspan=3, sticky=tk.NSEW,
                              **options)

        #search button
        search_button = ttk.Button(
            self,
            text='search',
            command = lambda: self.print_database_output()
        )
        search_button.grid(column=1, row=5, sticky=tk.W, **options)
        
        #result box
        self._result_box = tk.Text(self, height=20, width=30)
        result_scroll = tk.Scrollbar(self)
        result_scroll.config(command=self._result_box.yview)
        self._result_box.config(yscrollcommand=result_scroll.set)
        self._result_box.grid(column=0, row=0, columnspan=3, sticky=tk.NSEW,
                              **options)

        #add button
        add_button = ttk.Button(
            self,
            text='add',
            command = lambda: self.print_state()
        )
        add_button.grid(column=2, row=5, sticky=tk.W, **options)

        #state box
        self._state_box = tk.Text(self, height=20, width=30)
        state_scroll = tk.Scrollbar(self)
        state_scroll.config(command=self._state_box.yview)
        self._state_box.config(yscrollcommand=state_scroll.set)
        self._state_box.grid(column=3, row=0, columnspan=3, sticky=tk.NSEW,
                              **options)

        #focus
        self._identifier_entry.focus()
        self._ships_or_weapons_button.focus()
        self._source_entry.focus()
        search_button.focus()

        #resizing
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)

    def flip(self):
        """
        Handle button click event
        """
        try:
            self._ships_or_weapons = (
                'ships' if self._ships_or_weapons == 'weapons' else 'weapons')
            self._ships_or_weapons_button.config(text=self._ships_or_weapons)
        except ValueError as error:
            showerror(title='Error', message=error)

    def print_database_output(self):
        source_id = self._source_entry.get()
        item_id = self._identifier_entry.get()
        item_data = (
            self._data_dictionary[source_id][self._ships_or_weapons][item_id])
        text = "\n".join([name + ": " + str(item_data[name]) for name in
                                            item_data])   
        self._result_box.delete("1.0","end")
        self._result_box.insert('insert', text)

        if self._ships_or_weapons == "weapons":
            self._viewed_weapon = combat_entities.Weapon(item_data)
            self._viewed_ship = None
        elif self._ships_or_weapons == "ships":
            self._viewed_ship = combat_entities.Ship(item_data)
            self._viewed_weapon = None
        print(self._viewed_weapon)

    def print_state(self):
        if self._selected_ship:
            if self._viewed_weapon:
                self._selected_ship.weapons.append(self._viewed_weapon)
            if self._viewed_ship and (self._viewed_ship.data["id"]
                                      != self._selected_ship.data["id"]):
                self._selected_ship = self._viewed_ship
        elif self._viewed_ship: self._selected_ship = self._viewed_ship
        text = (self._selected_ship.data["name"]
                + "\n"
                + "\n".join(tuple(weapon.data["name"] for weapon in
                                  self._selected_ship.weapons)))
        self._state_box.delete("1.0","end")
        self._state_box.insert('insert', text)
        

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('StatSector Database')
        self.geometry('525x450')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.minsize(525, 450)


if __name__ == "__main__":
    app = App()
    data_dictionary = database.dictionary()
    database_frame = DatabaseFrame(app, data_dictionary)
    database_frame.grid(row=0, column=0, sticky=tk.W)
    app.mainloop()

"""
A function to simulate alpha
"""

import copy
import importlib
from thousandaire.constants import CONST_MAP, DATA_LIST_ALL
from thousandaire.data_loader import DataLoader
from thousandaire.simulator import Simulator

class DataSetter:
    """
    Set every data.
    This an object to give, renew all data we have everyday.
    """
    def __init__(self, data_list):
        self.workdays = DataLoader(['workdays']).get_all()['workdays']
        data_list.remove('workdays')
        self.data = DataLoader(data_list).get_all()

    def set_data(self, data_list, target, region):
        """
        Set data:
            (1)Synchronize used data with workdays.
            (2)Separate used data into workdays, simulate_data and target_data

        Notice:
        Due to the raw data will be used by every alpha, we cannot just pass
        reference of the data.
        We should deepcopy of the data we need.
        """
        workdays = copy.deepcopy(self.workdays[region])
        if target in self.data.keys():
            target_data = copy.deepcopy(self.data[target])
            target_data.set_workdays(workdays)
        else:
            raise KeyError("Key not found")
        simulate_data = {name : copy.deepcopy(self.data[name])
                         for name in data_list if name in self.data.keys()}
        for dataset in simulate_data.values():
            dataset.set_workdays(workdays)
        data = {
            'workdays' : workdays,
            'target_data' : target_data,
            'simulate_data' : simulate_data}
        return data

    def renew_data(self, data_list):
        """
        Used to renew data everyday.
        """

def simulation(alpha_list):
    """
    Act the process of simulating.
    """
    initial_asset = 10000
    all_data = DataSetter(DATA_LIST_ALL)
    for alpha in alpha_list:
        setting_module = importlib.import_module(
            'thousandaire.template.%s_settings' % alpha).AlphaSettings()
        data = all_data.set_data(
            setting_module.data_list,
            CONST_MAP[(setting_module.target[0], setting_module.target[1])],
            setting_module.target[1])
        simulator = Simulator(initial_asset, setting_module, data)
        evaluate_data = simulator.run()
        return evaluate_data

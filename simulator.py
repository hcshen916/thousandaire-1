"""
Create a simulator to calculate pnl
"""

import collections
import importlib
import random
from thousandaire.constants import CONST_MAP
from thousandaire.dataset import Data

class SimulateMethod():
    """
    The method for simulating.
    """
    def __init__(self, region, instruments, asset):
        self.quantity = collections.namedtuple('value', ['value', 'quantity'])
        self.cur_asset = {
            instrument : self.quantity(0, 0) for instrument in instruments}
        self.cur_asset[region] = self.quantity(asset, asset)
        self.asset = asset
        self.__portfolio = list()
        self.__pnl = Data('pnl', ['pnl', 'trading_cost'])
        self.alpha_formula = None

    def alpha_initialize(self, date, data, alpha_formula, parameters):
        """
        Initialize alpha_formula.
        """
        self.alpha_formula = alpha_formula(date, data, parameters)

    def get_results(self):
        """
        Return results.
        """
        result = Data('result', ['pnl', 'trading_cost', 'position'])
        for index in range(0, len(self.__pnl), 1):
            result.append(
                (self.__pnl[index].date, self.__pnl[index].pnl,
                 self.__pnl[index].trading_cost, self.__portfolio[index]))
        return result

    def produce_portfolio(self, today, data):
        """
        Find daily portfolio.
        """
        portfolio = self.alpha_formula(today, data)
        portfolio.normalize()
        self.__portfolio.append(portfolio)

    def produce_pnl(self, region, function_name, target_data):
        """
        Calculate pnl for alphas.
        This method will be called by simulation day by day while inputting
        a new portfolio.

        While calculating pnl,
        we should take a look at our asset and trading cost.
            (1) Total asset
                We assume that our assets are the same everyday (equal to
                self.initial_asset). To achieve this goal, we open a virtual
                account to borrow/lend money to the investing account (this
                account is self.cur_asset[self.base]).
            (2) Trading cost
                There are different functions about calculating trading cost
                in different investing targets.
                This method should import different modules while targets are
                different.

                In our template function, we calculate trading cost while
                selling out the asset.
                The trading_cost function could be built by alpha writers.
                The API will adjust in the future, while the fuction needs
                more data.
        """
        cost_function = importlib.import_module(
            'thousandaire.%s_trading_cost' % function_name)
        today = self.__portfolio[-1]
        trading_cost = 0
        trading_value = 0
        profit = 0
        for instrument, proportion in today.items():
            if target_data[instrument][-1].sell is not None:
                now = self.quantity(
                    proportion * self.asset,
                    proportion * self.asset
                    / target_data[instrument][-1].sell
                )
                trading_value += now.value
                profit += (
                    (self.cur_asset[instrument].quantity - now.quantity) *
                    target_data[instrument][-1].sell)
                trading_cost += cost_function.calculate_cost(
                    self.cur_asset[instrument],
                    now,
                    target_data[instrument][-1]
                )
                self.cur_asset[instrument] = now
        basic_value = self.asset - trading_value
        profit += self.cur_asset[region].value - basic_value
        self.cur_asset[region] = self.quantity(basic_value, basic_value)
        self.__pnl.append((today.date, profit / self.asset * 100, trading_cost))


class Simulator(SimulateMethod):
    """
    Simulate the alpha.
    """
    def __init__(self, asset, settings, data):
        SimulateMethod.__init__(
            self,
            settings.target[1],
            list(data['target_data'].keys()),
            asset)
        self.data = data['simulate_data']
        self.settings = settings
        self.target_data = data['target_data']
        self.__key = random.randint(0, 2147483647)
        self.workdays = data['workdays']

    def next_date(self):
        """
        Move the simulating date.
        """
        for dataset in self.data.values():
            dataset.next_date(self.__key)
        self.target_data.next_date(self.__key)
        self.workdays.next_date(auth_key=self.__key)

    def run(self):
        """
        Carried out simulating process.
        """
        self.setting()
        self.alpha_initialize(
            None, self.data, self.settings.alpha, self.settings.parameters)
        while (self.workdays.get_today() is None or
               self.workdays.get_today() <= self.settings.end_date):
            self.produce_portfolio(self.workdays.get_today(), self.data)
            self.next_date()
            if self.workdays.get_today() is not None:
                self.produce_pnl(
                    self.settings.target[1],
                    CONST_MAP[(self.settings.target[0],
                               self.settings.target[1])],
                    self.target_data)
            else:
                raise ValueError("Please renew the data to calculate pnl.")
        return self.get_results()

    def setting(self):
        """
        Alpha setting.

        This method is used to initialize the settings before simulating alpha.
        We push keys into all_data, and set them into start_date.
        """
        self.workdays.set_key(self.__key)
        self.target_data.set_key(self.__key)
        self.target_data.set_date(self.settings.start_date, self.__key)
        for dataset in self.data.values():
            dataset.set_key(self.__key)
            dataset.set_date(self.settings.start_date, self.__key)
        self.workdays.set_date(self.settings.start_date, auth_key=self.__key)

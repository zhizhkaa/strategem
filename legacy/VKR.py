
from statistics import mean
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from Work_W_FLs import UniversityGame
from Work_W_Dcsn import DecisionManager
from game import Game
import energy
import population
import industry
import agriculture
import finance
import json
import math
import os
import re
ADMIN_LOGIN = "1"
ADMIN_PASSWORD = "123"

class Strategema:
    def __init__(self):
        self.decision_mgr = DecisionManager()
        self.teamwork = UniversityGame()
        # Инициализация параметров
        self.game = Game()

        self.P1_x = [0.0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5, 15.0]
        self.P1_y = [0.030, 0.028, 0.026, 0.024, 0.022, 0.019, 0.016, 0.013, 0.011, 0.010, 0.010]
        self.P2_x = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
        self.P2_y = [1.000, 1.500, 1.450, 1.400, 1.350, 1.300, 1.200, 1.100, 1.000, 1.000, 1.000]
        self.P3_x = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        self.P3_y = [0.060, 0.045, 0.030, 0.022, 0.018, 0.015, 0.013, 0.012, 0.011, 0.010, 0.010]
        self.P4_x = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        self.P4_y = [1.75, 1.60, 1.50, 1.40, 1.30, 1.20, 1.10, 1.00, 1.00, 1.00, 1.00]
        
        self.E1_x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        self.E1_y = [0.0, 17.5, 20.0, 22.5, 25.0, 27.5, 30.0, 32.0, 33.5, 34.5, 35.0]
        self.E2_x = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        self.E2_y = [1.00, 0.80, 0.70, 0.58, 0.50, 0.42, 0.40, 0.35, 0.33, 0.31, 0.30]

        self.G1_x = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
        self.G1_y = [0.40, 0.52, 0.64, 0.76, 0.88, 0.907, 1.00, 1.00, 1.00, 1.00, 1.00]
        self.G2_x = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
        self.G2_y = [1.0, 2.0, 3.0, 3.5, 4.0, 4.3, 4.5, 4.7, 4.8, 4.9, 5.0]
        self.G3_x = [0.0, 3.032, 6.064, 9.096, 12.128, 15.16, 18.192, 21.224, 24.256, 27.288, 30.32]
        self.G3_y = [0.6064, 3.032, 5.4576, 7.8848, 9.475, 10.9152, 12.128, 13.0384, 14.012, 14.7032, 15.16]
        # self.G3_x = [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0]
        # self.G3_y = [0.8, 4.0, 7.2, 10.4, 12.5, 14.4, 16.0, 17.2, 18.5, 19.4, 20.0]

        self.F1_x = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
        self.F1_y = [0.40, 0.52, 0.64, 0.76, 0.88, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]
        self.F2_x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        self.F2_y = [0.0, 1.0, 2.0, 3.0, 3.7, 4.2, 4.5, 4.7, 4.8, 4.9, 5.0]
        self.F3_x = [0.0, 0.1, 0.2,	0.3, 0.4, 0.5, 0.6,	0.7, 0.8, 0.9, 1.0]
        self.F3_y = [0.0, 0.04, 0.055, 0.07, 0.078, 0.083, 0.09, 0.093, 0.095, 0.097, 0.1]
        self.F4_x = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        self.F4_y = [0.0, 0.002, 0.02, 0.035, 0.045, 0.05, 0.045, 0.035, 0.02, 0.002, 0.0]
        
        self.TF1_x = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        self.TF1_y = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
        self.TF2_x = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        self.TF2_y = [0.10, 0.10, 0.10, 0.12, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20]

    
    def load_data_team(self, faculty, group, team):
        """Загружаем параметры команды из JSON файла"""
        file_path = self.teamwork.data_dir / faculty / group / f"{team}.json"
        
        if not file_path.exists():
            print(f"Файл сохранения не найден: {file_path}")
            return None
        
        print("Файл сохранения найден!")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            self.teamwork.period = data.get("period")
            self.teamwork.periods = data.get("periods")
            
            history_data = data.get("history", {})
            parameters = {}
            
            for param_name, param_values in history_data.items():
                cleaned_values = []
                for value in param_values:
                    try:
                        cleaned_values.append(float(value))
                    except (ValueError, TypeError):
                        cleaned_values.append(value)
                parameters[param_name] = cleaned_values
            
            self.history = parameters
            self.calculate_all()
            self.work_w_par()
            
        except Exception as e:
            print(f"Данная команда не проводила сессий!")
            self.teamwork.period = 1
            self.teamwork.periods = None
            self.game.parameters
            self.game.reload_param()
            self.work_w_par()
            self.history = {param: [] for param in self.game.parameters}
            print("Huston")

    def work_w_par(self):
        self.population_module = population.Population(self.game.parameters, self.decision_mgr)
        self.energy_module = energy.Energy(self.game.parameters, self.decision_mgr)
        self.industry_module = industry.Industry(self.game.parameters, self.decision_mgr)
        self.agriculture_module = agriculture.Agriculture(self.game.parameters, self.decision_mgr)
        self.finance_module = finance.Finance(self.game.parameters, self.decision_mgr)

    def interpolate(self, x_vals, y_vals, x):
        """Линейная интерполяция"""
        if not x_vals or not y_vals or len(x_vals) != len(y_vals):
            return 0
        for i in range(len(x_vals) - 1):
            if x_vals[i] <= x <= x_vals[i+1]:
                x0, y0 = x_vals[i], y_vals[i]
                x1, y1 = x_vals[i+1], y_vals[i+1]
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        if x < x_vals[0]:
            return y_vals[0]
        elif x > x_vals[-1]:
            return y_vals[-1]
        return 0

    def append_history(self):
        for param, value in self.game.parameters.items():
            self.history[param].append(value)

    def calculate_all(self):
        self.game.parameters["E3"] = round(self.history["E3"][-1] - self.history["E1"][-1] + self.history["E26"][-1])
        self.game.parameters["E6"] = round(self.history["E6"][-1] - self.history["E4"][-1] + self.history["E27"][-1])
        self.game.parameters["E4"] = round(self.game.parameters["E6"] / 5)
        self.game.parameters["E18"] = round(self.history["E21"][-1])

        self.game.parameters["F3"] = round(self.history["F3"][-1] - self.history["F1"][-1] + self.history["F14"][-1])
        self.game.parameters["F4"] = round(self.history["F6"][-1] / 6)
        self.game.parameters["F6"] = round(self.history["F6"][-1] - self.history["F4"][-1] + self.history["F15"][-1])
        self.game.parameters["F7"] = round(self.history["F7"][-1] + self.interpolate(self.F4_x, self.F4_y, self.history["F7"][-1]) - self.interpolate(self.F3_x, self.F3_y, ((self.history["F3"][-1] * self.history["F10"][-1] + self.history["G3"][-1] * self.history["G11"][-1] + self.history["E3"][-1] - 3 * self.history["F6"][-1]) / 200000)), 2)
        self.game.parameters["F8"] = round(self.game.parameters["F3"] / 1000, 2)
        self.game.parameters["F12"] = round(self.history["TF12"][-1])

        self.game.parameters["G3"] = round(self.history["G3"][-1] - self.history["G1"][-1] + self.history["G18"][-1])
        self.game.parameters["G6"] = round(self.history["G6"][-1] - self.history["G4"][-1] + self.history["G19"][-1])
        self.game.parameters["G4"] = round(self.game.parameters["G6"] / 9)
        self.game.parameters["G13"] = round(self.history["TF11"][-1])

        self.game.parameters["TF1"] = round(self.history["TF1"][-1] + self.history["TF13"][-1] + self.history["TF4"][-1] - self.history["TF14"][-1])

        self.game.parameters["P4"] = round(min(self.history["P9"][-1] / (self.history["P1"][-1] * 5), 5))
        self.game.parameters["P6"] = min(self.history["P11"][-1] / (self.history["P1"][-1] * 5), 15)
        

        self.game.parameters["P5"] = round(self.interpolate(self.P3_x, self.P3_y, self.game.parameters["P4"]) * self.interpolate(self.P4_x, self.P4_y, self.game.parameters["F7"]) * 1000)
        self.game.parameters["P8"] = round(self.interpolate(self.P1_x, self.P1_y, self.game.parameters["P6"]) * self.interpolate(self.P2_x, self.P2_y, self.history["P7"][-1]) * 1000)
        self.game.parameters["P1"] = round(self.history["P1"][-1] + (self.history["P1"][-1] / 1000 * self.game.parameters["P8"] * 5) - (self.history["P1"][-1] / 1000 * self.game.parameters["P5"] * 5), -1)
        self.game.parameters["P7"] = round(self.game.parameters["G6"] / self.game.parameters["P1"] if self.game.parameters["P1"] > 0 else 0, 2)

        self.game.parameters["E1"] = round(self.game.parameters["E3"] / 5)
        self.game.parameters["E2"] = round(self.game.parameters["E3"] * 4 / 5)
        self.game.parameters["E5"] = round(self.game.parameters["E6"] * 4 / 5)
        self.game.parameters["G1"] = round(self.game.parameters["G3"] / 5)
        self.game.parameters["G2"] = round(self.game.parameters["G3"] * 4 / 5)
        self.game.parameters["G5"] = round(self.game.parameters["G6"] * 8 / 9)
        self.game.parameters["F1"] = round(self.game.parameters["F3"] / 5)
        self.game.parameters["F2"] = round(self.game.parameters["F3"] * 4 / 5)
        self.game.parameters["F5"] = round(self.history["F6"][-1] * (5 / 6))

        self.game.parameters["E10"] = round(self.interpolate(self.E2_x, self.E2_y, (self.game.parameters["E6"] / (self.game.parameters["G3"] + self.game.parameters["F3"]))), 2)
        self.game.parameters["E11"] = round(self.game.parameters["E10"] * 2.5 * 5, 1)
        self.game.parameters["E12"] = round(self.game.parameters["E11"] * self.game.parameters["F3"])
        self.game.parameters["E13"] = round(self.game.parameters["E10"] * 4 * 5)
        self.game.parameters["E14"] = round(self.game.parameters["E13"] * self.game.parameters["G3"])
        self.game.parameters["E15"] = round(self.game.parameters["E12"] + self.game.parameters["E14"])

        self.game.parameters["G7"] = round(self.game.parameters["G3"] / (0.1895 * self.game.parameters["P1"]), 2)
        self.game.parameters["G9"] = round(self.game.parameters["G6"] / self.game.parameters["P1"], 2)
        self.game.parameters["G11"] = round(min(self.history["E25"][-1] / self.history["E14"][-1], 1.1), 2)
        self.game.parameters["G10"] = round(self.interpolate(self.G2_x, self.G2_y, self.game.parameters["G9"]), 2)
        self.game.parameters["G8"] = round(self.interpolate(self.G3_x, self.G3_y, (self.game.parameters["G7"] * self.game.parameters["G11"])), 2)

        self.game.parameters["F10"] = round(min(self.history["E24"][-1] / self.history["E12"][-1], 1.1), 2)
        self.game.parameters["F9"] = round(6250 * self.interpolate(self.F2_x, self.F2_y, ((self.game.parameters["F3"] * self.game.parameters["F10"]) / 1000)), -2)

        self.game.parameters["TF2"] = round((self.interpolate(self.TF2_x, self.TF2_y, (self.game.parameters["TF1"] / (mean(self.history["TF10"][-3:]) + mean(self.history["TF11"][-3:]) + mean(self.history["TF12"][-3:]))))) * 100, 1)
        self.game.parameters["TF3"] = round(min(self.interpolate(self.TF1_x, self.TF1_y, (self.game.parameters["TF1"] / (mean(self.history["TF10"][-3:]) + mean(self.history["TF11"][-3:]) + mean(self.history["TF12"][-3:])))), 2), 2)
        self.game.parameters["TF4"] = round(self.game.parameters["TF1"] * (self.game.parameters["TF2"] / 100) * 5, 2)
        self.game.parameters["TF5"] = round(0 if self.game.parameters["TF1"] >= (mean(self.history["TF10"][-3:]) + mean(self.history["TF11"][-3:]) + mean(self.history["TF12"][-3:])) else (mean(self.history["TF10"][-3:]) + mean(self.history["TF11"][-3:]) + mean(self.history["TF12"][-3:])))
        self.game.parameters["TF6"] = round(min(1 * self.game.parameters["TF3"], 2),2)
        self.game.parameters["TF7"] = round(min(1.1 * self.game.parameters["TF3"], 2.2), 2)
        self.game.parameters["TF8"] = round(min(1.1 * self.game.parameters["TF3"], 2.2), 2)
        
        self.game.parameters["E8"] = 0.2
        self.game.parameters["E9"] = round(self.history["P11"][-1] / 5, -1)
        self.game.parameters["E17"] = self.interpolate(self.E1_x, self.E1_y, (self.game.parameters["E3"] / 1000)) * 1000
        self.game.parameters["E16"] = round(max(self.game.parameters["E17"] / self.game.parameters["E3"], 3.5), 1)
        self.game.parameters["E19"] = round(self.history["TF16"][-1] / self.history["TF6"][-1])
        self.game.parameters["E7"] = self.game.parameters["E17"] + self.game.parameters["E19"] + self.history["E22"][-1]

        self.game.parameters["G12"] = round(0.1895 * self.game.parameters["P1"] * 1.155 * self.game.parameters["G10"] * self.game.parameters["G8"] * 5 * min(self.interpolate(self.G1_x, self.G1_y, (self.game.parameters["P6"] / self.history["P6"][-1])), 1), -1)
        self.game.parameters["G14"] = round(self.history["TF17"][-1] / self.game.parameters["TF7"])
        self.game.parameters["G15"] = round(0.1895 * self.game.parameters["P1"] * 1.155 * self.game.parameters["G10"] * self.game.parameters["G8"] * 5 * 1, -2)
        self.game.parameters["G16"] = round(self.game.parameters["G12"] + self.game.parameters["G14"], -2)
        self.game.parameters["G17"] = round(self.game.parameters["E1"] + self.game.parameters["E4"] + self.game.parameters["F1"] + self.game.parameters["F4"] + self.game.parameters["G1"] + self.game.parameters["G4"])

        self.game.parameters["F11"] = round(6250 * min(self.interpolate(self.F2_x, self.F2_y, (self.game.parameters["F3"] * self.game.parameters["F10"] / 1000)), 5) * self.game.parameters["F7"] * min(self.interpolate(self.F1_x, self.F1_y, (self.game.parameters["P4"] / self.history["P4"][-1] )), 1), -2)
        self.game.parameters["F13"] = round(self.history["TF18"][-1] / self.game.parameters["TF8"])

        self.game.parameters["P2"] = round(self.game.parameters["F13"] + self.game.parameters["F11"], -1)
        self.game.parameters["P3"] = round(self.game.parameters["G14"] + self.game.parameters["G12"], -1)
        if self.game.parameters["TF1"] > (1/2 * (self.game.parameters["P3"] + self.game.parameters["P2"] + self.game.parameters["E7"])):
            self.game.parameters["P3"] = self.game.parameters["P3"] * 0.9

        
        

    def admin_login(self):
        print("Добро пожаловать! Введите учетные данные администратора.")
        for attempt in range(3):
            login = input("Логин: ").strip()
            password = input("Пароль: ").strip()
            if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
                print("Доступ разрешен. Вы вошли как администратор.")
                return True
            else:
                print("Неверный логин или пароль. Попробуйте снова.")
        print("Превышено количество попыток.")
        return False
        
    def menu(self):
        actions = {
            "1": self.teamwork.faculty_menu,
            "2": self.run_simulation,
            "3": lambda: False
        }
        
        while True:
            print("\n" + "="*40)
            print("МЕНЮ ИГРЫ".center(40))
            print("="*40)
            print("1. Выбор факультета, группы и команды")
            print("2. Начать игру")
            print("3. Выйти из игры")
            print("="*40)
            
            action_choice = input("Выберите действие: ").strip()
            
            if action_choice == "2" and not self.teamwork.current_team:
                print("Сначала выберите команду!")
                continue

            if action_choice == "3":
                exit()
                
            if action_choice in actions:
                try:
                    actions[action_choice]()
                except Exception as e:
                    print(f"Ошибка {str(e)}")
            else:
                print("Неверный ввод, попробуйте снова")



    def run_simulation(self):
        
        """Функция для проверки есть ли сохранения и чтения данных с файла"""
        self.load_data_team(self.teamwork.current_faculty, self.teamwork.current_group, self.teamwork.current_team)

        if not self.teamwork.periods:
            while True:
                try:
                    choice_periods = {
                        "1": 10,
                        "2": 12
                    }
                    choice = input("\nВыберите количество периодов в игре:\n" +
                                   "1 - 10 периодов\n" +
                                   "2 - 12 периодов\n" + 
                                   "Введите номер действия: ").strip()
                    if choice in choice_periods:
                        self.teamwork.periods = choice_periods[choice]
                        break
                    else:
                        print("Неверный ввод, попробуйте снова.")
                except ValueError:
                    print("Ошибка: введите целое число.")
                except KeyboardInterrupt:
                    print("\nВвод прерван пользователем.")
                    exit()
                except Exception as e:
                    print(f"Произошла непредвиденная ошибка: {e}")
        else:
            print(f"Количество периодов {self.teamwork.periods}")

        minister_actions = {
            "1": self.population_minister_actions,
            "2": self.energy_minister_actions,
            "3": self.industry_minister_actions,
            "4": self.agriculture_minister_actions,
            "5": self.trade_finance_minister_actions,
            "6": self.next_period,
            "7": self.plot_results,
            "8": self.menu
        }
        while self.teamwork.period <= self.teamwork.periods:
            
            print(f"\nИдёт {self.teamwork.period} период!")
            # Выбор министра
            print(self.game.parameters)
            choice = input("\nВыберите министра для действий:\n" +
                        "1 - Министр по делам населения\n" +
                        "2 - Министр энергетики\n" +
                        "3 - Министр промышленности и сферы услуг\n" +
                        "4 - Министр сельского хозяйства\n" +
                        "5 - Министр внешней торговли и финансов\n" +
                        "6 - Перейти к следующему периоду\n" +
                        "7 - Начертить графики\n" +
                        "8 - Вернуться в меню\n" +
                        "Введите номер действия: ").strip()
            action = minister_actions.get(choice)
            if action:
                action()
            else:
                print("Неверный ввод, попробуйте снова.")

    def reset_decisions(self):
        self.choose_dec = 0


### ВСЕ МИНИСТРЫ ###

    def population_minister_actions(self):
        print("Вы выбрали Министра по делам населения. Здесь будут решения.")
        actions = {
            "1": self.population_module.distribute_food,
            "2": self.population_module.distribute_goods,
            "3": lambda: None 
        }
        choose_dec = 1
        
        self.perform_action(actions, choose_dec)
        


    def energy_minister_actions(self):
        print("Вы выбрали Министра энергетики. Здесь будут решения.")
        actions = {
            "1": self.energy_module.distribute_energy_resources,
            "2": self.energy_module.distribute_energy_production,
            "3": self.energy_module.invest_in_energy,
            "4": lambda: None 
        }
        choose_dec = 2
        
        self.perform_action(actions, choose_dec)


    def industry_minister_actions(self):
        print("Вы выбрали Министра промышленности и сферы услуг. Здесь будут решения.")

        actions = {
            "1": self.industry_module.distribute_investments,
            "2": lambda: None  
        }
        choose_dec = 3

        self.perform_action(actions, choose_dec)

    def agriculture_minister_actions(self):
        print("Вы выбрали Министра сельского хозяйства. Здесь будут решения.")

        actions = {
            "1": self.agriculture_module.distribute_agriculture_investments,
            "2": lambda: None 
        }
        choose_dec = 4

        self.perform_action(actions, choose_dec)


    def trade_finance_minister_actions(self):
        print("Вы выбрали Министра внешней торговли и финансов. Здесь будут решения.")

        actions = {
            "1": self.finance_module.eval_currency_revenue,
            "2": self.finance_module.take_new_loan,
            "3": self.finance_module.pay_debt,
            "4": self.finance_module.distribute_import_currency,
            "5": lambda: None 
        }
        choose_dec = 5

        self.perform_action(actions, choose_dec)

### ВСЕ МИНИСТРЫ ###
    


    def next_period(self):
        self.teamwork.period += 1
        self.reset_decisions()
        self.decision_mgr.reset_decisions()

        print("Переход к следующему периоду.")
        self.append_history()
        print(self.game.parameters)
        print(self.history)
        self.calculate_all()
        self.display_state()
        self.teamwork.save_team_data(self.teamwork.current_faculty, self.teamwork.current_group, self.teamwork.current_team, self.teamwork.period, self.teamwork.periods, self.history)

    def perform_action(self, actions, choose_dec):
        if not self.teamwork.current_team:
            print("Сначала выберите команду!")
            return
        print(f"\nРабота с командой: {self.teamwork.current_team}")
        """Унифицированный метод для выполнения действий министра"""
        # Меню для каждого типа министра
        menus = {
            1: {
                "title": "Министр по делам населения",
                "options": [
                    "1 - Распределить продовольствие",
                    "2 - Распределить товары",
                    "3 - Вернуться назад"
                ]
            },
            2: {
                "title": "Министр энергетики",
                "options": [
                    "1 - Распределить энергоресурсы по направлениям",
                    "2 - Распределить энергию на производство",
                    "3 - Капиталовложения в энергетику",
                    "4 - Вернуться назад"
                ]
            },
            3: {
                "title": "Министр промышленности и сферы услуг",
                "options": [
                    "1 - Распределить товары на капиталовложения",
                    "2 - Вернуться назад"
                ]
            },
            4: {
                "title": "Министр сельского хозяйства",
                "options": [
                    "1 - Распределить капиталовложения",
                    "2 - Вернуться назад"
                ]
            },
            5: {
                "title": "Министр внешней торговли и финансов",
                "options": [
                    "1 - Оценить поступления валюты по статьям",
                    "2 - Принять решение о новом иностранном займе",
                    "3 - Принять решение о выплатах по долгу",
                    "4 - Распределить валюту на закупки по импорту",
                    "5 - Вернуться назад"
                ]
            }
        }
        
        current_menu = menus.get(choose_dec)
        if not current_menu:
            print("Ошибка: неверный тип министра")
            return
        
        if choose_dec == 1:
            self.population_module = population.Population(self.game.parameters, self.decision_mgr)
        elif choose_dec == 2:
            self.energy_module = energy.Energy(self.game.parameters, self.decision_mgr)
        elif choose_dec == 3:
            self.industry_module = industry.Industry(self.game.parameters, self.decision_mgr)
        elif choose_dec == 4:
            self.agriculture_module = agriculture.Agriculture(self.game.parameters, self.decision_mgr)
        elif choose_dec == 5:
            self.finance_module = finance.Finance(self.game.parameters, self.decision_mgr)

        while True:
            
            print(f"\n{'='*40}")
            print(f"{current_menu['title']:^40}")
            print(f"{'='*40}")
            for option in current_menu['options']:
                print(option)
            print(f"{'='*40}")
            try:
                action_choice = input("Введите номер действия: ").strip()
                if action_choice in actions:
                # проверяем, является ли выбор "назад"
                    if action_choice == str(len(current_menu['options'])) or \
                    "вернуться" in current_menu['options'][int(action_choice)-1].lower():
                        break
                    try:
                        result = actions[action_choice]()
                        if result is False:  # Если действие явно возвращает False
                            break
                    except Exception as e:
                        print(f"Ошибка при выполнении действия: {e}")
                else:
                    print("Неверный ввод, пожалуйста, выберите существующий вариант.")
            except ValueError:
                print("\nОшибка: вводите только числовые значения")
                return False
        
    def display_state(self):
        print(f"Население: {self.game.parameters['P1']}")
        print(f"Энергоресурсы: {self.game.parameters['E3']}")
        print(f"Промышленный капитал: {self.game.parameters['G3']}")
        print(f"Сельхоз капитал: {self.game.parameters['F3']}")

        
    

    def plot_results(self):

        fig, ax = plt.subplots(figsize=(10, 5))
        plt.subplots_adjust(left=0.4)

        ax_radio = plt.axes([0, 0.4, 0.3, 0.5])
        radio = RadioButtons(ax_radio, ('Население', 'Продовольствие на д.н./г.', 'Уровень смертности', 'Товары на д.н./г.',
                                        'Услуги на д.н./г.', 'Уровень рождаемости', 'Капитал для пр-ва энергии', 'Капитал энергосбережения',
                                        'Всего энергоресурсов', 'Капитал для пр-ва товаров', 'Капитал с/х', 'Внешний долг', 'Коэф. потребления ресурсов',
                                        'Сотояние окр. среды', 'Эффективность энергетики', 'Эффективность сел.хоз.', 'Эффективность промышл.', 'Темпы роста населения'))

        def update_plot(label):
            ax.clear()
            if label == 'Население':
                ax.plot(self.history["P1"], label="Население")
            elif label == 'Продовольствие на д.н./г.':
                ax.plot(self.history["P4"], label="Продовольствие на д.н./г.")
            elif label == 'Уровень смертности':
                ax.plot(self.history["P5"], label="Уровень смертности")
            elif label == 'Товары на д.н./г.':
                ax.plot(self.history["P6"], label="Товары на д.н./г.")
            elif label == 'Услуги на д.н./г.':
                ax.plot(self.history["P7"], label="Услуги на д.н./г.")
            elif label == 'Уровень рождаемости':
                ax.plot(self.history["P8"], label="Уровень рождаемости")
            elif label == 'Темпы роста населения':
                ax.plot(((self.history["P8"] - self.history["P5"]) / 1000), label="Темпы роста населения")
            elif label == 'Капитал для пр-ва энергии':
                ax.plot(self.history["E1"], label="Выбытие капитала")
                ax.plot(self.history["E2"], label="Новый капитал")
                ax.plot(self.history["E3"], label="Основной капитал")
            elif label == 'Капитал энергосбережения':
                ax.plot(self.history["E4"], label="Выбытие капитала")
                ax.plot(self.history["E5"], label="Новый капитал")
                ax.plot(self.history["E6"], label="Основной капитал")
            elif label == 'Всего энергоресурсов':
                ax.plot(self.history["E7"], label="Всего энергоресурсов")
            elif label == 'Коэф. потребления ресурсов':
                ax.plot(self.history["E10"], label="Коэф. потребления ресурсов")
            elif label == 'Эффективность энергетики':
                ax.plot(round(self.history["E16"]), label="Эффективность энергетики")
            elif label == 'Капитал для пр-ва товаров':
                ax.plot(self.history["G1"], label="Выбытие капитала")
                ax.plot(self.history["G2"], label="Новый капитал")
                ax.plot(self.history["G3"], label="Основной капитал")
            elif label == 'Эффективность промышл.':
                ax.plot(round(self.history["G15"]/(self.history["G3"] + self.history["G6"])), label="Эффективность промышл.")
            elif label == 'Сотояние окр. среды':
                ax.plot(self.history["F7"], label="Сотояние окр. среды")
            elif label == 'Эффективность сел.хоз.':
                ax.plot(round(self.history["F9"]/self.history["F3"]), label="Эффективность сел.хоз.")
            elif label == 'Капитал с/х':
                ax.plot(self.history["F1"], label="Выбытие капитала")
                ax.plot(self.history["F2"], label="Новый капитал")
                ax.plot(self.history["F3"], label="Основной капитал с/х")
            elif label == 'Внешний долг':
                ax.plot(self.history["TF1"], label="Внешний долг")
            ax.set_xlabel("Периоды")
            ax.set_ylabel("Значения")
            ax.set_title("Динамика показателей экономики")
            ax.legend()
            num_points = len(self.history["P1"])
            ax.set_xticks(range(num_points))
            ax.set_xticklabels(range(1, num_points + 1))
            fig.canvas.draw_idle()

        radio.on_clicked(update_plot)

        update_plot('Показатели')
        plt.show()



sim = Strategema()

if __name__ == "__main__":
    if sim.admin_login():
        print("Запуск программы с полными правами.")
        sim.menu()
    else:
        print("Доступ ограничен. Завершение работы.")
        exit()


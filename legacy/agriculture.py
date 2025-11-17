
class Agriculture:
    def __init__(self, parameters, decision_mgr):
        self.parameters = parameters
        self.decision_mgr = decision_mgr
    def distribute_agriculture_investments(self):
        if not self.decision_mgr.check_decision('capital', 3):
            print("Сначала необходимо распределить капиталовложения в промышленность!")
            return
        print("\n=== РАСПРЕДЕЛЕНИЕ КАПИТАЛОВЛОЖЕНИЙ В СЕЛЬСКОЕ ХОЗЯЙСТВО ===")
    
        # Расчет доступных средств
        remaining_funds = self.parameters["P12"] - (
            self.parameters["G18"] + 
            self.parameters["G19"] + 
            self.parameters["E26"] + 
            self.parameters["E27"]
        )
        
        # Минимальная сумма с учетом требований
        min_agriculture_investment = max(
            0,
            self.parameters["E27"] - self.parameters["G18"]
        )
        
        print(f"\nДоступно капиталовложений: {remaining_funds}")
        print(f"Минимальная сумма для сельского хозяйства: {min_agriculture_investment}")
        print(f"(должно покрыть E27: {self.parameters['E27']} вместе с G18: {self.parameters['G18']})")

        try:
            # Ввод
            while True:
                agriculture_investment = float(
                    input(f"Введите для производства продовольствия "
                        f"({min_agriculture_investment}-{remaining_funds}): ")
                )
                
                # Проверка минимального значения
                if agriculture_investment < min_agriculture_investment:
                    required = self.parameters["E27"] - self.parameters["G18"]
                    print(f"Ошибка: должно быть не менее {required} "
                        f"(E27 - G18 = {self.parameters['E27']} - {self.parameters['G18']})")
                    continue
                    
                # Проверка максимального значения
                if agriculture_investment > remaining_funds:
                    print(f"Ошибка: превышено доступное количество ({remaining_funds})")
                    continue
                    
                break

            # Расчет для экологии
            ecology_investment = remaining_funds - agriculture_investment
            
            # Сохранение параметров
            self.parameters.update({
                "F14": agriculture_investment,
                "F15": ecology_investment
            })
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('capital', 4)
            
            # Вывод
            print("\n" + "="*60)
            print("КАПИТАЛОВЛОЖЕНИЯ В СЕЛЬСКОЕ ХОЗЯЙСТВО РАСПРЕДЕЛЕНЫ".center(60))
            print("="*60)
            print(f"{'Производство продовольствия:':<30} {agriculture_investment:>10.2f}")
            print(f"{'Защита окружающей среды:':<30} {ecology_investment:>10.2f}")
            print("="*60)
            print(f"{'Всего распределено:':<30} {remaining_funds:>10.2f}")
            print("="*60)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False
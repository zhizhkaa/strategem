
class Energy:
    def __init__(self, parameters, decision_mgr):
        self.parameters = parameters
        self.decision_mgr = decision_mgr

    def distribute_energy_resources(self):
            print("\n=== РАСПРЕДЕЛЕНИЕ ЭНЕРГОРЕСУРСОВ ===")
            total = self.parameters["E7"]
            required_for_population = self.parameters["P11"] / 5
            
            try:
                # Ввод
                print(f"\nДоступно энергоресурсов: {total}")
                print(f"Требуется для населения: {required_for_population:.1f} (1/5 от P11)")
                while True:
                    # Население
                    population = float(input(f"Введите для населения ({required_for_population:.1f}): "))
                    if not abs(population - required_for_population) < 0.1:
                        print("Ошибка: не соответствует требованию!")
                        continue
                    break
                while True:
                # Экспорт
                    remaining = total - population
                    export = float(input(f"Введите на экспорт (до {remaining}): "))
                    if export < 0 or export > remaining:
                        print("Ошибка: недопустимое значение!")
                        continue
                    break
                remaining -= export
                while True:
                    # Резерв
                    reserve = float(input(f"Введите в резерв (до {remaining}): "))
                    if reserve < 0 or reserve > remaining:
                        print("Ошибка: недопустимое значение!")
                        continue
                    break
                
                # Производство (остаток)
                production = remaining - reserve
                
                # Сохранение результатов
                self.parameters.update({
                    "E20": round(population, -1),
                    "E21": export,
                    "E22": reserve, 
                    "E23": production
                })
                
                # Обновление статусов решений
                self.decision_mgr.set_decision('finance', 3)
                self.decision_mgr.set_decision('energy', 1)
                
                # Вывод
                print("\nРезультаты распределения:")
                print(f"- Население: {self.parameters['E20']}")
                print(f"- Экспорт: {self.parameters['E21']}")
                print(f"- Резерв: {self.parameters['E22']}")
                print(f"- Производство: {self.parameters['E23']}")
                print(f"Итого распределено: {sum([population, export, reserve, production])} из {total}")
                
                return self.parameters
                
            except ValueError:
                print("Ошибка: вводите только числа!")
                return False
            
    def distribute_energy_production(self):
        if not self.decision_mgr.check_decision("energy", 1):
            print("Сначала распределите энергоресурсы!")
            return
        print("\n=== РАСПРЕДЕЛЕНИЕ ЭНЕРГИИ НА ПРОИЗВОДСТВО ===")
        AVAILABLE_ENERGY = self.parameters["E23"]
        
        print(f"\nДоступно энергии для производства: {AVAILABLE_ENERGY}")

        try:
            # Ввод
            while True:
                food_production_energy = float(
                    input(f"Введите энергию для продовольствия (0-{AVAILABLE_ENERGY}): ")
                )
                
                # Проверка всех условий
                if food_production_energy < 0 or food_production_energy > AVAILABLE_ENERGY:
                    print("Ошибка: недопустимое значение!")
                    continue
                break 

            # Расчет для товаров
            goods_production_energy = AVAILABLE_ENERGY - food_production_energy
        
            # Сохранение параметров
            self.parameters.update({
                "E24": food_production_energy,
                "E25": goods_production_energy
            })
            
            # Вывод
            print("\n" + "="*50)
            print("ЭНЕРГИЯ НА ПРОИЗВОДСТВО РАСПРЕДЕЛЕНА".center(50))
            print("="*50)
            print(f"{'Для продовольствия:':<25} {food_production_energy:>10.2f}")
            print(f"{'Для товаров:':<25} {goods_production_energy:>10.2f}")
            print("="*50)
            print(f"{'Всего распределено:':<25} {AVAILABLE_ENERGY:>10.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False
        
    def invest_in_energy(self):
        if not self.decision_mgr.check_decision('capital', 1):
            print("Сначала распределите товары для капиталовложений!")
            print(self.decision_mgr.states['capital'])
            return
        print("\n=== РАСПРЕДЕЛЕНИЕ КАПИТАЛОВЛОЖЕНИЙ В ЭНЕРГЕТИКУ ===")
    
        TOTAL_INVESTMENTS = self.parameters["P12"]
        
        print(f"\nДоступно капиталовложений: {TOTAL_INVESTMENTS}")

        try:
            # Инвестиции в генерацию
            while True:
                generation_investment = float(
                    input(f"Введите для генерации энергии (0-{TOTAL_INVESTMENTS}): ")
                )
                
                if generation_investment < 0 or generation_investment > TOTAL_INVESTMENTS:
                    print("Ошибка: недопустимое значение!")
                    continue
                break

            # Инвестиции в энергосбережение
            remaining_investments = TOTAL_INVESTMENTS - generation_investment
            while True:
                efficiency_investment = float(
                    input(f"Введите для энергосбережения (0-{remaining_investments}): ")
                )
                
                if efficiency_investment < 0 or efficiency_investment > remaining_investments:
                    print("Ошибка: недопустимое значение!")
                    continue
                break

            # Сохранение параметров
            self.parameters.update({
                "E26": generation_investment,
                "E27": efficiency_investment
            })
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('capital', 2)
            
            # Вывод
            print("\n" + "="*50)
            print("КАПИТАЛОВЛОЖЕНИЯ РАСПРЕДЕЛЕНЫ".center(50))
            print("="*50)
            print(f"{'Генерация энергии:':<25} {generation_investment:>10.2f}")
            print(f"{'Энергосбережение:':<25} {efficiency_investment:>10.2f}")
            print("="*50)
            print(f"{'Всего распределено:':<25} {TOTAL_INVESTMENTS:>10.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False
    
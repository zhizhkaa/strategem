class Population:
    def __init__(self, parameters, decision_mgr):
        self.parameters = parameters
        self.decision_mgr = decision_mgr
    def distribute_food(self):
        print("\n=== РАСПРЕДЕЛЕНИЕ ПРОДОВОЛЬСТВИЯ ===")
    
        # Расчетные параметры
        MAX_POPULATION_FOOD = self.parameters["P1"] * 25  # P1 * 5 * 5
        TOTAL_FOOD = self.parameters["P2"]
        
        print(f"\nДоступно продовольствия: {TOTAL_FOOD}")
        print(f"Максимум для населения: {MAX_POPULATION_FOOD} (P1 * 25)")

        try:
            # Блок ввода
            while True:
                population_food = float(input(f"Введите количество для населения (0-{min(TOTAL_FOOD, MAX_POPULATION_FOOD)}): "))
                
                # Проверка условий
                if population_food < 0 or population_food > MAX_POPULATION_FOOD or population_food > TOTAL_FOOD:
                    print("Ошибка: недопустимое значение!")
                    continue
                break

            # Расчет экспорта
            export_food = TOTAL_FOOD - population_food
            
            # Сохранение параметров
            self.parameters.update({
                "P9": population_food,
                "P10": export_food
            })
            
            print(self.parameters["P9"])

            # Обновление статуса решений
            self.decision_mgr.set_decision('finance', 1)
            
            # вывод результатов
            print("\n" + "="*50)
            print("ПРОДОВОЛЬСТВИЕ УСПЕШНО РАСПРЕДЕЛЕНО".center(50))
            print("="*50)
            print(f"{'Для населения:':<25} {population_food:>10.2f}")
            print(f"{'На экспорт:':<25} {export_food:>10.2f}")
            print("="*50)
            print(f"{'Всего распределено:':<25} {TOTAL_FOOD:>10.2f}")
            print("="*50)
            
            return True
        
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False

    def distribute_goods(self):
        print("\n=== РАСПРЕДЕЛЕНИЕ ТОВАРОВ ===")
    
        # Расчетные параметры
        MAX_POPULATION_GOODS = self.parameters["P6"] * 75  # P6 * 15 * 5
        print(self.parameters["P6"])
        TOTAL_GOODS = self.parameters["P3"]
        
        print(f"\nДоступно товаров: {TOTAL_GOODS}")
        print(f"Максимум для населения: {MAX_POPULATION_GOODS} (P6 * 75)")

        try:
            # Товары для населения
            while True:
                population_goods = float(
                    input(f"Введите для населения (0-{min(TOTAL_GOODS, MAX_POPULATION_GOODS)}): ")
                )
                
                if population_goods < 0 or population_goods > MAX_POPULATION_GOODS or population_goods > TOTAL_GOODS:
                    print("Ошибка: недопустимое значение!")
                    continue
                break

            # Товары для капиталовложений
            remaining_goods = TOTAL_GOODS - population_goods
            while True:
                capital_goods = float(
                    input(f"Введите для капиталовложений (0-{remaining_goods}): ")
                )
                
                if capital_goods < 0 or capital_goods > remaining_goods:
                    print("Ошибка: недопустимое значение!")
                    continue
                break

            # Расчет экспорта
            export_goods = TOTAL_GOODS - population_goods - capital_goods
            
            # Сохранение параметров
            self.parameters.update({
                "P11": population_goods,
                "P12": capital_goods,
                "P13": export_goods
            })
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('capital', 1)
            self.decision_mgr.set_decision('finance', 2)
            print(self.decision_mgr.states['capital'])
            
            # Вывод
            print("\n" + "="*50)
            print("ТОВАРЫ УСПЕШНО РАСПРЕДЕЛЕНЫ".center(50))
            print("="*50)
            print(f"{'Для населения:':<25} {population_goods:>10.2f}")
            print(f"{'На капиталовложения:':<25} {capital_goods:>10.2f}") 
            print(f"{'На экспорт:':<25} {export_goods:>10.2f}")
            print("="*50)
            print(f"{'Всего распределено:':<25} {TOTAL_GOODS:>10.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False
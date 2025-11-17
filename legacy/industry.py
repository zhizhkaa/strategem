
class Industry:
    def __init__(self, parameters, decision_mgr):
        self.parameters = parameters
        self.decision_mgr = decision_mgr
    def distribute_investments(self):
        if not self.decision_mgr.check_decision('capital', 2):
            print("Сначала распределите товары для капиталовложений!")
            return
        print("\n=== РАСПРЕДЕЛЕНИЕ КАПИТАЛОВЛОЖЕНИЙ В ПРОМЫШЛЕННОСТЬ ===")
    
        # Расчет доступных средств
        remaining_funds = self.parameters["P12"] - self.parameters["E26"] - self.parameters["E27"]
        production_investment = self.parameters["E27"]  # Минимальная сумма для производства товаров
        
        print(f"\nДоступно капиталовложений: {remaining_funds}")
        print(f"Минимум для производства товаров: {production_investment} (должно покрывать E27 в сумме с F14)")

        try:
            # Производство товаров
            while True:
                goods_investment = float(
                    input(f"Введите для производства товаров (0 - {remaining_funds}): ")
                )
                
                if goods_investment < 0 or goods_investment > remaining_funds:
                    print(f"Ошибка: недопустимое значение!")
                    continue
                break

            # Для сферы услуг
            remaining_after_goods = remaining_funds - goods_investment
            while True:
                services_investment = float(
                    input(f"Введите для сферы услуг (0-{remaining_after_goods}): ")
                )
                
                if services_investment < 0 or services_investment > remaining_after_goods:
                    print("Ошибка: значение не может быть отрицательным")
                    continue
                break

            # Сохранение параметров
            self.parameters.update({
                "G18": goods_investment,
                "G19": services_investment
            })
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('capital', 3)
            
            # Вывод
            print("\n" + "="*50)
            print("КАПИТАЛОВЛОЖЕНИЯ РАСПРЕДЕЛЕНЫ".center(50))
            print("="*50)
            print(f"{'Производство товаров:':<25} {goods_investment:>10.2f}")
            print(f"{'Сфера услуг:':<25} {services_investment:>10.2f}")
            print("="*50)
            print(f"{'Всего распределено:':<25} {remaining_funds:>10.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\n Ошибка: вводите только числовые значения")
            return False

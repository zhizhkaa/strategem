import math

class Finance:
    def __init__(self, parameters, decision_mgr):
        self.parameters = parameters
        self.decision_mgr = decision_mgr
    def eval_currency_revenue(self):
        if not self.decision_mgr.check_decision('finance', 2):
            print("Сначала необходимо распределить средства на экспорт!")
            return
        print("\n=== УЧЕТ ВАЛЮТНЫХ ПОСТУПЛЕНИЙ ===")
    
        # Ожидаемые значения по экспорту
        expected_values = {
            "energy": self.parameters["E21"],
            "goods": self.parameters["P13"],
            "food": self.parameters["P10"]
        }
        
        print("\nОжидаемые суммы по экспорту:")
        print(f"- Энергия: {expected_values['energy']}")
        print(f"- Товары: {expected_values['goods']}")
        print(f"- Продовольствие: {expected_values['food']}")

        try:
            # Ввод иностранной помощи
            foreign_aid = float(input("Введите сумму иностранной помощи: "))
            if foreign_aid < 0:
                print("Ошибка: сумма помощи не может быть отрицательной")
                return False

            # Ввод и проверка экспортных значений
            receipts = {}
            for category in ["energy", "goods", "food"]:
                while True:
                    value = float(input(
                        f"Введите поступления от экспорта {category} "
                        f"(должно быть {expected_values[category]}): "
                    ))
                    if not math.isclose(value, expected_values[category], rel_tol=0.001):
                        print(f"Ошибка: должно быть равно {expected_values[category]}")
                        continue
                        
                    receipts[category] = value
                    break

            # Сохранение параметров
            self.parameters.update({
                "TF9": foreign_aid,
                "TF10": receipts["energy"],
                "TF11": receipts["goods"],
                "TF12": receipts["food"]
            })
            # Обновление статуса решений
            self.decision_mgr.set_decision('import', 1)
            
            # Вывод
            print("\n" + "="*60)
            print("ВАЛЮТНЫЕ ПОСТУПЛЕНИЯ УСПЕШНО ЗАФИКСИРОВАНЫ".center(60))
            print("="*60)
            print(f"{'Иностранная помощь:':<30} {foreign_aid:>15.2f}")
            print(f"{'Экспорт энергии:':<30} {receipts['energy']:>15.2f}")
            print(f"{'Экспорт товаров:':<30} {receipts['goods']:>15.2f}")
            print(f"{'Экспорт продовольствия:':<30} {receipts['food']:>15.2f}")
            print("="*60)
            print(f"{'Общая сумма поступлений:':<30} "
                f"{sum([foreign_aid, receipts['energy'], receipts['goods'], receipts['food']]):>15.2f}")
            print("="*60)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False

    def take_new_loan(self):
        print("\n=== ОФОРМЛЕНИЕ НОВОГО КРЕДИТА ===")
    
        try:
            # Ввод
            while True:
                loan_amount = float(input("Введите сумму кредита (≥ 0): "))
                
                if loan_amount < 0:
                    print("Ошибка: сумма кредита не может быть отрицательной")
                    return False
                    
                break

            # Сохранение параметра
            self.parameters["TF13"] = loan_amount
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('import', 2)
            
            # Вывод
            print("\n" + "="*50)
            print("НОВЫЙ КРЕДИТ УСПЕШНО ОФОРМЛЕН".center(50))
            print("="*50)
            print(f"{'Сумма кредита:':<25} {loan_amount:>15.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\n Ошибка: вводите только числовые значения")
            return False

    def pay_debt(self):
        print("\n=== ВЫПЛАТА ПО ВНЕШНЕМУ ДОЛГУ ===")
    
        current_debt = self.parameters["TF1"]
        print(f"\nТекущий размер долга: {current_debt:.2f}")

        try:
            # Ввод
            while True:
                payment_amount = float(input(
                    f"Введите сумму выплаты (0-{current_debt}): "
                ))
                
                if payment_amount < 0:
                    print("Ошибка: сумма не может быть отрицательной")
                    continue
                    
                if payment_amount > current_debt:
                    print(f"Ошибка: превышает размер долга ({current_debt})")
                    continue
                    
                break

            # Сохранение параметра
            self.parameters["TF14"] = payment_amount
            
            # Обновление статуса решений
            self.decision_mgr.set_decision('import', 3)
            
            # Расчет остатка долга
            remaining_debt = current_debt - payment_amount
            
            # Вывод
            print("\n" + "="*50)
            print("ВЫПЛАТА ПО ДОЛГУ ПРОВЕДЕНА".center(50))
            print("="*50)
            print(f"{'Текущий долг:':<25} {current_debt:>15.2f}")
            print(f"{'Сумма выплаты:':<25} {payment_amount:>15.2f}")
            print(f"{'Остаток долга:':<25} {remaining_debt:>15.2f}")
            print("="*50)
            
            return True
            
        except ValueError:
            print("\nОшибка: вводите только числовые значения")
            return False

    
    def distribute_import_currency(self):
        if not self.decision_mgr.check_decision('import', 3):
            print("Сначала необходимо оценить поступления валюты!")
            return
        print("\n=== РАСПРЕДЕЛЕНИЕ ВАЛЮТЫ НА ИМПОРТ ===")
        
        # Расчет доступной валюты
        total_available = (
            self.parameters["TF9"] +  # Иностранная помощь
            self.parameters["TF10"] + # Экспорт энергии
            self.parameters["TF11"] + # Экспорт товаров
            self.parameters["TF12"] + # Экспорт продовольствия
            self.parameters["TF13"] - # Новые кредиты
            self.parameters["TF14"]   # Выплаты по долгу
        )
        
        print(f"\nДоступно валюты для импорта: {total_available:.2f}")

        try:
            # Проверка общей суммы
            while True:
                total_import = float(input(
                    f"Введите общую сумму на импорт (должна быть {total_available:.2f}): "
                ))
                
                if not math.isclose(total_import, total_available, rel_tol=0.001):
                    print(f"Ошибка: сумма должна быть равна {total_available:.2f}")
                    continue
                break

            # Распределение по категориям
            categories = [
                ("энергию", "TF16"),
                ("товары", "TF17"),
                ("продовольствие", "TF18")
            ]
            
            remaining = total_import
            for i, (category_name, param_name) in enumerate(categories):
                if i < len(categories) - 1:  # Не последняя категория
                    while True:
                        amount = float(input(
                            f"Введите сумму для импорта {category_name} (0-{remaining:.2f}): "
                        ))
                        
                        if amount < 0 or amount > remaining:
                            print(f"Ошибка: должно быть между 0 и {remaining:.2f}")
                            continue
                            
                        self.parameters[param_name] = amount
                        remaining -= amount
                        break
                else:  # Последняя категория (продовольствие)
                    self.parameters[param_name] = remaining
                    print(f"\nСумма для импорта {category_name} автоматически рассчитана: {remaining:.2f}")

            # Проверка итогового распределения
            distributed_total = sum(self.parameters[p] for _, p in categories)
            if not math.isclose(distributed_total, total_import, rel_tol=0.001):
                raise ValueError("Общая сумма распределения не совпадает с доступной валютой")

            # Вывод
            print("\n" + "="*60)
            print("ВАЛЮТА НА ИМПОРТ РАСПРЕДЕЛЕНА".center(60))
            print("="*60)
            print(f"{'Импорт энергии:':<30} {self.parameters['TF16']:>15.2f}")
            print(f"{'Импорт товаров:':<30} {self.parameters['TF17']:>15.2f}")
            print(f"{'Импорт продовольствия:':<30} {self.parameters['TF18']:>15.2f}")
            print("="*60)
            print(f"{'Всего распределено:':<30} {total_import:>15.2f}")
            print("="*60)
            
            return True
            
        except ValueError as e:
            print(f"\nОшибка: {str(e)}")
            return False
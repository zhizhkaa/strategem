class DecisionManager:
    def __init__(self):
        self.reset_decisions()
    
    def reset_decisions(self):
        """Сброс всех решений"""
        self.states = {
            'capital': 0,    # Уровень принятия решений по капиталовложениям
            'energy': 0,     # Уровень принятия решений по энергетике
            'finance': 0,    # Уровень принятия финансовых решений
            'import': 0      # Уровень принятия решений по импорту
        }
    
    def check_decision(self, category, required_level):
        """Проверка, выполнено ли требуемое решение"""
        return self.states.get(category, 0) >= required_level
    
    def set_decision(self, category, level):
        """Установка уровня принятого решения"""
        if category in self.states:
            self.states[category] = level
            return True
        return False
    
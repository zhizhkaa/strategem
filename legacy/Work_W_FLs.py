from pathlib import Path
from datetime import datetime
import os
import json
import shutil


class UniversityGame:
    def __init__(self):
        base_dir = Path(__file__).parent
        self.data_dir = base_dir / "game_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "university_data.json"
        self.current_faculty = None
        self.current_group = None
        self.current_team = None
        self.periods = None
        self.period = 1
        self.load_data()

    def load_data(self):
        """Загрузка данных из JSON файла"""
        self.faculties = {}
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.faculties = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Ошибка загрузки данных: {e}")
                self.faculties = {}

    def save_data(self):
        """Сохранение данных в JSON файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.faculties, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")

    def create_faculty(self):
        """Создание нового факультета"""
        while True:
            name = input("Введите название факультета: ").strip()
            if not name:
                print("Название не может быть пустым!")
                continue
            
            if name in self.faculties:
                print("Факультет с таким названием уже существует!")
                continue

            # Создаем структуру факультета в JSON
            self.faculties[name] = {}
            
            # Создаем папку для факультета
            faculty_folder = self.data_dir / name
            if not faculty_folder.exists():
                faculty_folder.mkdir(parents=True, exist_ok=True)
                
            self.save_data()
            print(f"Факультет '{name}' успешно создан и папка создана!")
            break

    def create_group(self):
        """Создание новой группы"""
        if not self.current_faculty:
            print("Сначала выберите факультет!")
            return
        
        if self.current_faculty not in self.faculties:
            self.faculties[self.current_faculty] = {}

        while True:
            name = input("Введите название группы: ").strip()
            if not name:
                print("Название не может быть пустым!")
                continue

            if name in self.faculties[self.current_faculty]:
                print("Группа с таким названием уже существует!")
                continue

            # Создаем структуру группы в JSON
            self.faculties[self.current_faculty][name] = []
            self.save_data()

            group_folder = self.data_dir / self.current_faculty / name
            if not group_folder.exists():
                group_folder.mkdir(parents=True, exist_ok=True)
            print(f"Группа '{name}' успешно создана и папка создана!")
            break

    def create_team(self):
        """Создание новой команды"""
        if not self.current_faculty:
            print("Сначала выберите факультет!")
            return
        
        try:
            if self.current_group is None:
                print("Сначала выберите группу!")
                return
        except AttributeError:
            print("Сначала выберите группу!")
            return
        
        teams = self.faculties[self.current_faculty][self.current_group]

        while True:
            name = input("Введите название команды: ").strip()
            if not name:
                print("Название не может быть пустым!")
                continue
                
            if name in teams:
                print("Команда с таким названием уже существует в этой группе!")
                continue
            
            teams.append(name)
            self.save_data()
            
            faculty_folder = self.data_dir / self.current_faculty
            group_folder = faculty_folder / self.current_group
            team_file = group_folder / f"{name}.json"
            
            team_data = {
                "savedate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "fac": self.current_faculty,
                "group": self.current_group,
                "team": name,
                "period": None,
                "periods": None,
                "history": {}
            }
            
            with open(team_file, 'w', encoding='utf-8') as f:
                json.dump(team_data, f, ensure_ascii=False, indent=2)
            
            print(f"Команда '{name}' успешно создана!")
            break

    def delete_faculty(self):
        """Удаляет выбранный факультет из JSON"""
        if not self.faculties:
            print("Нет доступных факультетов для удаления.")
            return
        print("\nДоступные факультеты для удаления:")
        faculties = list(self.faculties.keys())
        for i, faculty in enumerate(faculties, 1):
            print(f"{i}. {faculty}")
        choice = input("Введите номер факультета для удаления: ").strip()
        if not choice.isdigit():
            print("Некорректный ввод.")
            return
        index = int(choice) - 1
        if 0 <= index < len(faculties):
            faculty_name = faculties[index]
            confirm = input(f"Вы уверены, что хотите удалить факультет '{faculty_name}'? (да/нет): ").lower()
            if confirm == 'да':
                # Удаление папки факультета
                faculty_folder = self.data_dir / faculty_name
                if faculty_folder.exists():
                    shutil.rmtree(faculty_folder)
                
                # Удаление из JSON данных
                del self.faculties[faculty_name]
                self.save_data()
                
                print(f"Факультет '{faculty_name}' удален.")
                self.current_faculty = None
            else:
                print("Удаление отменено.")
        else:
            print("Некорректный номер.")

    def delete_group(self):
        """Удаляет выбранную группу из JSON"""
        if not self.current_faculty:
            print("Сначала выберите факультет.")
            return
        groups = list(self.faculties[self.current_faculty].keys())
        if not groups:
            print("Нет групп для удаления.")
            return
        print("\nДоступные группы для удаления:")
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group}")
        choice = input("Введите номер группы для удаления: ").strip()
        if not choice.isdigit():
            print("Некорректный ввод.")
            return
        index = int(choice) - 1
        if 0 <= index < len(groups):
            group_name = groups[index]
            confirm = input(f"Вы уверены, что хотите удалить группу '{group_name}'? (да/нет): ").lower()
            if confirm == 'да':
                # Удаление папки группы
                group_folder = self.data_dir / self.current_faculty / group_name
                if group_folder.exists():
                    shutil.rmtree(group_folder)
                
                # Удаление из JSON данных
                del self.faculties[self.current_faculty][group_name]
                
                # Если после удаления групп факультет пуст, удаляем его
                if not self.faculties[self.current_faculty]:
                    del self.faculties[self.current_faculty]
                    self.current_faculty = None
                
                self.save_data()
                print(f"Группа '{group_name}' удалена.")
                self.current_group = None
            else:
                print("Удаление отменено.")
        else:
            print("Некорректный номер.")

    def delete_team(self):
        """Удаляет выбранную команду из JSON"""
        if not self.current_faculty or not self.current_group:
            print("Сначала выберите факультет и группу.")
            return
        teams = self.faculties[self.current_faculty][self.current_group]
        if not teams:
            print("Нет команд для удаления.")
            return
        print("\nДоступные команды для удаления:")
        for i, team in enumerate(teams, 1):
            print(f"{i}. {team}")
        choice = input("Введите номер команды для удаления: ").strip()
        if not choice.isdigit():
            print("Некорректный ввод.")
            return
        index = int(choice) - 1
        if 0 <= index < len(teams):
            team_name = teams[index]
            confirm = input(f"Вы уверены, что хотите удалить команду '{team_name}'? (да/нет): ").lower()
            if confirm == 'да':
                # Удаление JSON файл команды
                team_file = self.data_dir / self.current_faculty / self.current_group / f"{team_name}.json"
                if team_file.exists():
                    team_file.unlink()
                
                # Удаление из JSON списка
                teams.remove(team_name)
                self.save_data()
                print(f"Команда '{team_name}' удалена.")
            else:
                print("Удаление отменено.")
        else:
            print("Некорректный номер.")

    
    def save_team_data(self, faculty_name, group_name, team_name, period, periods, history_parameters):
        """Сохранение данных команды в JSON файл в новом формате"""
        faculty_folder = self.data_dir / faculty_name
        group_folder = faculty_folder / group_name
        team_file = group_folder / f"{team_name}.json"
        
        # Создание данных в новом формате
        team_data = {
            "savedate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "fac": faculty_name,
            "group": group_name,
            "team": team_name,
            "period": period,
            "periods": periods,
            "history": history_parameters
        }
        
        # Сохранение в JSON
        try:
            with open(team_file, 'w', encoding='utf-8') as f:
                json.dump(team_data, f, ensure_ascii=False, indent=2)
            print(f"Данные сохранены в: {team_file}")
        except Exception as e:
            print(f"Ошибка сохранения данных команды: {e}")

    def select_faculty(self):
        """Выбор факультета"""
        if not self.faculties:
            print("Нет доступных факультетов!")
            return False
            
        print("\nДоступные факультеты:")
        faculties = list(self.faculties.keys())
        for i, faculty in enumerate(faculties, 1):
            print(f"{i}. {faculty}")
            
        while True:
            choice = input("Выберите факультет (номер): ").strip()
            if not choice.isdigit():
                print("Введите номер факультета!")
                continue
                
            index = int(choice) - 1
            if 0 <= index < len(faculties):
                self.current_faculty = faculties[index]
                self.current_group = None
                self.current_team = None
                print(f"Выбран факультет: {self.current_faculty}")
                return True
            print("Неверный номер факультета!")

    def select_group(self):
        """Выбор группы внутри текущего факультета"""
        if not self.current_faculty:
            print("Сначала выберите факультет!")
            return False
        
        if self.current_faculty not in self.faculties:
            print("Факультет не найден в данных!")
            return False
            
        groups = list(self.faculties[self.current_faculty].keys())
        if not groups:
            print("В этом факультете нет групп.")
            return False
            
        print(f"\nГруппы факультета {self.current_faculty}:")
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group}")
            
        while True:
            choice = input("Выберите группу (номер): ").strip()
            if not choice.isdigit():
                print("Введите номер группы!")
                continue
            index = int(choice) - 1
            if 0 <= index < len(groups):
                self.current_group = groups[index]
                print(f"Выбрана группа: {self.current_group}")
                return True
            print("Неверный номер группы!")

    def select_team(self):
        """Выбор команды"""
        if not self.current_faculty:
            print("Сначала выберите факультет!")
            return False
        
        if not self.current_group:
            print("Сначала выберите группу!")
            return False
            
        teams = self.faculties[self.current_faculty][self.current_group]
        if not teams:
            print("В этой группе нет команд!")
            return False
            
        print(f"\nКоманды группы {self.current_group}:")
        for i, team in enumerate(teams, 1):
            print(f"{i}. {team}")
            
        while True:
            choice = input("Выберите команду (номер): ").strip()
            if not choice.isdigit():
                print("Введите номер команды!")
                continue
                
            index = int(choice) - 1
            if 0 <= index < len(teams):
                self.current_team = teams[index]
                print(f"Выбрана команда: {self.current_team}")
                return True
            print("Неверный номер команды!")

    def delete_func(self):
        """Менеджер удаления"""
        while True:
            print("\n" + "="*40)
            print("МЕНЕДЖЕР УДАЛЕНИЯ".center(40))
            print("="*40)
            print("1. Удалить факультет")
            print("2. Удалить группу")
            print("3. Удалить команду")
            print("4. Вернуться назад")
            print("="*40)
            choice = input("Выберите действие: ").strip()
            if choice == "1":
                self.delete_faculty()
            elif choice == "2":
                self.delete_group()
            elif choice == "3":
                self.delete_team()
            elif choice == "4":
                break
            else:
                print("Неверный ввод, попробуйте снова")

    def faculty_menu(self):
        """Меню управления факультетами"""
        while True:
            print("\n" + "="*40)
            print("МЕНЕДЖЕР ФАКУЛЬТЕТОВ, ГРУПП И КОМАНД".center(40))
            print("="*40)
            print("1. Создать факультет")
            print("2. Выбрать факультет")
            print("3. Создать группу")
            print("4. Выбрать группу")
            print("5. Создать команду")
            print("6. Выбрать команду")
            print("7. Удаление")
            print("8. Вернуться назад")
            print("="*40)
            
            if self.current_faculty:
                print(f"Текущий факультет: {self.current_faculty}")
                if self.current_group:
                    if self.current_group not in self.faculties[self.current_faculty]:
                        self.current_group = None
                        print("Выберите группу.")
                    else:
                        print(f"Текущая группа: {self.current_group}")
                        if self.current_team:
                            if self.current_team not in self.faculties[self.current_faculty][self.current_group]:
                                self.current_team = None
                                print("Выберите команду.")
                            else:
                                print(f"Текущая команда: {self.current_team}")
            
            choice = input("Выберите действие: ").strip()
            
            if choice == "1":
                self.create_faculty()
            elif choice == "2":
                self.select_faculty()
            elif choice == "3":
                self.create_group()
            elif choice == "4":
                self.select_group()
            elif choice == "5":
                self.create_team()
            elif choice == "6":
                self.select_team()
            elif choice == "7":
                self.delete_func()
            elif choice == "8":
                break
            else:
                print("Неверный ввод, попробуйте снова")
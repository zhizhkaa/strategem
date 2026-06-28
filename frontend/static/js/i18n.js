(function () {
    const STORAGE_KEY = "strategem_lang";
    const DEFAULT_LANG = "ru";

    const en = {
        "Главная": "Home",
        "Администратор": "Administrator",
        "API Docs": "API Docs",
        "Выйти": "Log out",
        "Панель администратора": "Admin panel",
        "Управление играми и командами": "Manage games and teams",
        "Настройки": "Settings",
        "Факультет": "Faculty",
        "Группа": "Group",
        "Команда": "Team",
        "Создать игру": "Create game",
        "Текущие": "Current",
        "Архив": "Archive",
        "Обновить": "Refresh",
        "Игры": "Games",
        "Архив игр": "Game archive",
        "Команды без активных игр": "Teams without active games",
        "Факультеты, группы и команды": "Faculties, groups, and teams",
        "Документы для игроков": "Player documents",
        "Загрузить файл": "Upload file",
        "Скачать Excel": "Download Excel",
        "Архивировать": "Archive",
        "Вернуть из архива": "Restore from archive",
        "Удалить игру": "Delete game",
        "Настройка сохранена": "Setting saved",
        "Конфигурационные файлы": "Configuration files",
        "Глобальные параметры": "Global settings",
        "Использовать пароли": "Use passwords",
        "Авторасчёт параметров": "Auto-calculate parameters",
        "Параллельные решения": "Parallel decisions",
        "Редактировать": "Edit",
        "Редактор конфигурации": "Configuration editor",
        "Справка": "Help",
        "Проверить": "Validate",
        "Сбросить": "Reset",
        "Сохранить": "Save",
        "Отмена": "Cancel",
        "Справка по конфигурации": "Configuration help",
        "Проверка": "Validation",
        "Ошибок нет": "No errors",
        "Найдены ошибки": "Errors found",
        "Сводный лист": "Summary sheet",
        "Сводный лист решений": "Decision summary",
        "Население": "Population",
        "Энергетика": "Energy",
        "Промышленность": "Industry",
        "С/х и среда": "Agriculture and environment",
        "Торговля и финансы": "Trade and finance",
        "Внести значения →": "Submit values →",
        "Отправить решения": "Submit decisions",
        "Сохранение...": "Saving...",
        "Проверка...": "Checking...",
        "Переменная / Название": "Variable / Name",
        "Информация к сведению": "Information",
        "Текущая ситуация": "Current situation",
        "Проверка корректности:": "Correctness check:",
        "Всего": "Total",
        "Графики": "Charts",
        "Сменить команду": "Change team",
        "Начать новую игру": "Start a new game",
        "Игра завершена!": "Game finished!",
        "Загрузка...": "Loading...",
        "Загрузка игры...": "Loading game...",
        "Доступ запрещён": "Access denied",
        "Войти": "Log in",
    };

    function currentLang() {
        const params = new URLSearchParams(window.location.search);
        const fromUrl = params.get("lang");
        if (fromUrl) {
            localStorage.setItem(STORAGE_KEY, fromUrl);
            return fromUrl;
        }
        return localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
    }

    function translateText(value, lang) {
        if (lang === DEFAULT_LANG) return value;
        const normalized = value.replace(/\s+/g, " ").trim();
        return en[normalized] || value;
    }

    function translateElement(element, lang) {
        if (element.closest("script, style, textarea, code, pre")) return;

        for (const attr of ["title", "placeholder", "aria-label"]) {
            const value = element.getAttribute(attr);
            if (value) {
                element.setAttribute(attr, translateText(value, lang));
            }
        }

        for (const node of element.childNodes) {
            if (node.nodeType !== Node.TEXT_NODE) continue;
            const text = node.nodeValue || "";
            if (!text.trim()) continue;
            const translated = translateText(text, lang).trim();
            if (translated && translated !== text.trim()) {
                node.nodeValue = text.replace(text.trim(), translated);
            }
        }
    }

    function applyTranslations(root = document) {
        const lang = currentLang();
        document.documentElement.lang = lang;
        if (lang === DEFAULT_LANG) return;
        const elements = root.querySelectorAll ? root.querySelectorAll("*") : [];
        for (const element of elements) {
            translateElement(element, lang);
        }
    }

    function setLanguage(lang) {
        localStorage.setItem(STORAGE_KEY, lang);
        window.location.reload();
    }

    window.StrategemI18n = {
        currentLang,
        setLanguage,
        applyTranslations,
        dictionaries: { en },
    };

    document.addEventListener("DOMContentLoaded", () => {
        applyTranslations();
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === "characterData" && mutation.target.parentElement) {
                    translateElement(mutation.target.parentElement, currentLang());
                }
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        applyTranslations(node);
                    }
                }
            }
        });
        observer.observe(document.body, { childList: true, characterData: true, subtree: true });
    });
})();

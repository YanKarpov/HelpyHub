import re
from typing import List, Optional

class ProfanityFilter:
    ALLOWED_ENDINGS = [
        'а', 'ы', 'е', 'ой', 'ую', 'ою', 'и', 'у', 'ам', 'ах', 'ями', 'ях', 'ом', 'енция', 'онька', 'ище', 'астый'
    ]

    def __init__(self, badwords: Optional[List[str]] = None):
        if badwords is None:
            badwords = self._load_default_badwords()
        self.patterns = self._compile_patterns(badwords)

    @staticmethod
    def _load_default_badwords(filepath: str = "assets/data/badwords.txt") -> List[str]:
        try:
            with open(filepath, encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Файл со словами по умолчанию не найден: {filepath}")
            return []

    @classmethod
    def from_file(cls, filepath: str) -> "ProfanityFilter":
        try:
            with open(filepath, encoding="utf-8") as f:
                words = [line.strip() for line in f if line.strip()]
            return cls(badwords=words)
        except FileNotFoundError:
            print(f"Файл '{filepath}' не найден.")
            return cls()

    def _obfuscate(self, word: str) -> str:
        char_map = {
            'а': '[аa@4а́а̀]', 'б': '[бb6]', 'в': '[вvbw]', 'г': '[гg]',
            'д': '[дd]', 'е': '[еeё3е́ѐ]', 'ё': '[ёe3]', 'ж': '[жzh]',
            'з': '[з3z]', 'и': '[иi1|!ії]', 'й': '[йиi]', 'к': '[кkqκ]',
            'л': '[лl]', 'м': '[мm]', 'н': '[нh]', 'о': '[оo0]',
            'п': '[пpπ]', 'р': '[рpr]', 'с': '[сsc$]', 'т': '[тt]',
            'у': '[уyu]', 'ф': '[фfph]', 'х': '[хxh%]', 'ц': '[цc]',
            'ч': '[чch4]', 'ш': '[шsh]', 'щ': '[щsch]', 'ь': "[ьb']",
            'ы': '[ыbi]', 'ъ': '[ъb]', 'э': '[эe]', 'ю': '[юiu]',
            'я': '[яya]'
        }
        # Каждую букву заменить на паттерн + разрешить спецсимволы между буквами
        return ''.join(char_map.get(c, re.escape(c)) + r'[\W_]*' for c in word.lower())

    def _compile_patterns(self, words: List[str]) -> List[re.Pattern]:
        vowels = 'аеиоуыэюяё'
        patterns = []
        for w in words:
            if not w:
                continue

            # Отделяем корень и возможное окончание
            base = w
            endings = []

            # Если слово оканчивается на гласную — отделим корень и сделаем список окончаний
            if w[-1] in vowels:
                base = w[:-1]
                endings = [w[-1]] + self.ALLOWED_ENDINGS
            else:
                endings = self.ALLOWED_ENDINGS + ['']  # допускаем и без окончания

            base_pattern = self._obfuscate(base)

            # Сформируем паттерн для всех окончаний с обфускацией
            endings_patterns = [self._obfuscate(e) for e in endings]

            # Допустим ровно одно окончание из списка (или пустое)
            endings_regex = '(?:' + '|'.join(endings_patterns) + ')'

            full_pattern = rf'(?<!\w){base_pattern}{endings_regex}(?!\w)'

            patterns.append(re.compile(full_pattern, re.IGNORECASE))
        return patterns

    def contains_profanity(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        return any(p.search(text) for p in self.patterns)

    def check_and_raise(self, text: str):
        if self.contains_profanity(text):
            raise ValueError("Сообщение содержит запрещённые слова и не может быть отправлено.")

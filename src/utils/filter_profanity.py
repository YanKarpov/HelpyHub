import re
from typing import List, Optional

class ProfanityFilter:
    def __init__(self, badwords: Optional[List[str]] = None):
        if badwords is None:
            badwords = self._load_default_badwords()
        self.patterns = self._compile_patterns(badwords)

    @staticmethod
    def _load_default_badwords(filepath: str = "badwords.txt") -> List[str]:
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

        return ''.join(char_map.get(c, c) + r'[\W_]*' for c in word.lower())

    def _compile_patterns(self, words: List[str]) -> List[re.Pattern]:
        vowels = 'аеиоуыэюяё'
        patterns = []
        for w in words:
            base = w
            suffix = ''

            if len(w) > 4 and w[-1] in vowels:
                base = w[:-1]
                suffix = w[-1]

            base_pattern = self._obfuscate(base)

            if suffix:
                suffix_pattern = self._obfuscate(suffix) + r'[\W_]*'
                suffix_pattern = f'(?:{suffix_pattern})*'
            else:
                suffix_pattern = ''

            full_pattern = base_pattern + suffix_pattern
            patterns.append(re.compile(full_pattern, re.IGNORECASE))
        return patterns

    def contains_profanity(self, text: str) -> bool:
        return bool(text.strip()) and any(p.search(text) for p in self.patterns)

    def check_and_raise(self, text: str):
        if self.contains_profanity(text):
            raise ValueError("Сообщение содержит запрещённые слова и не может быть отправлено.")

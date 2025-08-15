import pytest
from src.utils.profanity_filter import ProfanityFilter

@pytest.fixture
def filter():
    return ProfanityFilter.from_file("assets/data/badwords.txt")

# === Мат должен детектиться ===
@pytest.mark.parametrize("text", [
    # Базовые формы
    "жопа", "Жопа", "ЖОПА", "жопЫ", "жопЕ", "жопой", "жопе",

    # Латинские буквы вместо кириллических
    "жoпa",  # o,a латиницей
    "ж0пa",  # 0 вместо о
    "жoп@",  # @ вместо а
    "ж0п@",

    # Перемешанные регистры
    "ЖоПа",
    "жОпА",

    # Пробелы и знаки между буквами
    "ж о п а",
    "ж_о-п*а",
    "ж!о@п#а$%",
    "ж  о   п   а",
    "ж/о\\п|а",
    "ж.о.п.а",
    "ж(о)п[а]",
    "ж*о_п@а",

    # В предложении
    "Это просто жопа какая-то",
    "Ты что, ж0па?",
    "Жоп@ мира",

    # Разные формы одного корня
    "жопонька",
    "жопище",
    "жопенция",
    "жопастый",

    # Сочетание кириллицы и латиницы
    "ЖoПa",
    "Ж0Пa",
])
def test_detects_variants(filter, text):
    with pytest.raises(ValueError):
        filter.check_and_raise(text)

# === Мат НЕ должен детектиться ===
@pytest.mark.parametrize("text", [
    # Похожие слова без мата
    "жаба", "лопата", "жупел",
    "пижон", "тёплый", "копать",
    "жопарь" ,  # если не в списке
    "джопа",    # если не в списке

    # Внутри длинных слов, если фильтр не должен ловить
    "жопация",
    "дожопаться",

    # Частичные совпадения
    "жпа", "жоп", "жопенок",  # если не добавлено

    # Полностью без мата
    "привет как дела",
    "сегодня хорошая погода",

    # Пустые и пробельные строки
    "",
    "   ",
])
def test_does_not_detect_clean(filter, text):
    filter.check_and_raise(text)

# === Проверка устойчивости к разным символам ===
@pytest.mark.parametrize("text", [
    "ж*о_п@а",
    "Ж-О-П-А",
    "Ж@О#П$А%",
    "ж..о..п..а",
    "ж~о~п~а",
])
def test_detects_with_punctuation(filter, text):
    with pytest.raises(ValueError):
        filter.check_and_raise(text)

# === Пакетная проверка предложений ===
@pytest.mark.parametrize("text,should_fail", [
    ("Сегодня будет жарко", False),
    ("Это просто ж0па!", True),
    ("Жопа мира и всё", True),
    ("На хуй ты так сделал", True),
    ("Пошёл в жопу", True),
    ("Прекрасный день", False),
])
def test_sentence_cases(filter, text, should_fail):
    if should_fail:
        with pytest.raises(ValueError):
            filter.check_and_raise(text)
    else:
        filter.check_and_raise(text)

from dataclasses import dataclass

@dataclass(frozen=True)
class CategoryInfo:
    image: str
    text: str

CATEGORIES = {
    "Документы": CategoryInfo(
        image="assets/images/documents.jpg",
        text="Тебе поможет учебный отдел, он находится на 4 этаже рядом с кабинетом 4.2"
    ),
    "Учебный процесс": CategoryInfo(
        image="assets/images/study.jpg",
        text="Ты можешь обратиться на свою кафедру. Она находится на 4 этаже напротив столовой"
    ),
    "Служба заботы": CategoryInfo(
        image="assets/images/support.jpg",
        text="Обратись в кабинет службы заботы на 3 этаже рядом с кабинетом 3.8"
    ),
    "Другое": CategoryInfo(
        image="assets/images/other.webp",
        text="Разные полезные сведения."
    ),
}

CATEGORIES_LIST = list(CATEGORIES.keys())

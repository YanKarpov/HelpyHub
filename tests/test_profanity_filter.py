import pytest
from filter_profanity import ProfanityFilter

BAD_WORDS = ["жопа", "мандарин"]

@pytest.fixture
def filter():
    return ProfanityFilter(badwords=BAD_WORDS)

@pytest.mark.parametrize("text", [
    "жопа",              
    "ЖОпА",              
    "ж о п а",              
    "ж*о*п*а",            
    "ж_о_п_а",               
    "ж!о@п#а$",            
    "ж^о&п(а)",              
    "Это ж о п а!",         
    "жоп@",                 
    "ж*о_п@а",       
])
def test_profanity_zhopa_detected(filter, text):
    with pytest.raises(ValueError):
        filter.check_and_raise(text)

@pytest.mark.parametrize("text", [
    "жаба",                 
    "жопация",             
    "жоп",               
    "лопа",        
    "пижон",                
    "жопарь",              
    "джопа",                 
    "жопочка",              
    "чужой",                
])
def test_profanity_zhopa_not_detected(filter, text):
    filter.check_and_raise(text)

@pytest.mark.parametrize("text", [
    "ЖОПА!",               
    "Ж-О-П-А",              
    "Ж@О#П$А%",            
    "ж.о.п.а",              
    "ж  о   п  а",          
])
def test_profanity_zhopa_with_punctuation(filter, text):
    with pytest.raises(ValueError):
        filter.check_and_raise(text)

@pytest.mark.parametrize("text", [
    "Ни одной жопы здесь нет", 
    "Это просто текст",          
    "Сегодня вкусный был мандарин",      
])
def test_profanity_clean_texts(filter, text):
    filter.check_and_raise(text)

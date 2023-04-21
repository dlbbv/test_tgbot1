import requests

from config import API_WEATHER_TOKEN # Импорт токена для api запроса погоды


url='https://api.openweathermap.org/data/2.5/weather?q={}&appid={}&units=metric'


def get_weather(city):
    try:
        r = requests.get(url.format(city, API_WEATHER_TOKEN))
        data = r.json() # Запись данных из запроса
        
        # Получение нужных данных из переменной data
        temp = round(data['main']['temp']) # Температура, округляем до целого числа
        feels_like = round(data['main']['feels_like']) #средняя температура, округляем до целого числа
        humidity = data['main']['humidity'] #влажность
        pressure = data['main']['pressure'] #давление
        wind = data['wind']['speed'] #скорость ветра

        answer = f"""
        В городе {city} сейчас температура {temp} градусов, ощущается как {feels_like} градусов.
Влажность: {humidity}%.
Давление: {pressure} мм.рт.ст.
Ветер: {wind} м/с.
"""
        return answer

    except Exception:
        return ('Вы неверно ввели название города либо такого не существует!\nПример названия:\nНижний Новгород')
import requests


url_getVal = 'https://openexchangerates.org/api/currencies.json' # Api для получения списка доступных валют на openexchangerates


# Проверка на правильность введенных кодов валют
def checkValue(val):
    try:
        response = requests.get(url_getVal)
        response.raise_for_status()  # Вызываем исключение, если статус ответа не равен 200
        data = response.json()
    except requests.exceptions.HTTPError as error:
        return error
    else:
        response = requests.get(url_getVal)
        response.raise_for_status()
        data = response.json()

    return val not in data
import sys
from datetime import datetime, timedelta

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'So-Seckrekt'
API_KEY = 'a2eec5522c1c2c34cdf69f49e448083b'
user_agent = {'User-agent': 'Mozilla/5.0'}
DB_NAME = 'weather'

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}.db'

db = SQLAlchemy(app)


class WeatherInCity(db.Model):
    __tablename__ = DB_NAME

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)


def get_local_time(timezone: str) -> datetime:
    return datetime.utcnow() + timedelta(seconds=int(timezone))


def get_part_of_the_day(time_stamp: datetime) -> str:
    hour = time_stamp.hour
    parts_of_the_day = ((5, 12, 'morning'), (12, 17, 'afternoon'),
                        (17, 21, 'evening'), (21, 4, 'night'),
                        )
    for day_part in parts_of_the_day:
        if any((day_part[0] <= hour, hour < day_part[1])):
            return day_part[2]


def add_to_database(city_name, database=WeatherInCity):
    if not city_name:
        pass
    city = database(name=city_name)
    already_in_database = database.query.filter(database.name == city_name).first()
    if not already_in_database:
        db.session.add(city)
        db.session.commit()
    elif already_in_database:
        flash("The city has already been added to the list!")
        weather_data = None
        return weather_data and get_flashed_messages()[0]


def get_weather_from_api(city_name):
    def kelvin_to_celcius(kelvin_value: float) -> int:
        return int(round(kelvin_value - 273.15))

    web_site = f'https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}'
    r = requests.get(web_site, headers=user_agent)
    if r.status_code == 200:
        json_data = r.json()
        dict_with_weather_info = {
            'name': json_data['name'].upper(),
            'temp': kelvin_to_celcius(float(json_data['main']['temp'])),
            'state': json_data['weather'][0]['main'],
            'day_part': get_part_of_the_day(get_local_time(json_data['timezone'])),
        }
        return dict_with_weather_info

    elif r.status_code == 404:
        flash("The city doesn't exist!")
        dict_with_weather_info = None
        return dict_with_weather_info and get_flashed_messages()[0]

    return None


def get_forecast():
    cities_in_db = WeatherInCity.query.all()
    weather_data = []
    for city in cities_in_db:
        data = get_weather_from_api(city.name)
        if data:
            weather_data.append(data)
    return weather_data


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        weather_data = get_forecast()
        database = WeatherInCity.query.filter_by(id=WeatherInCity.id)
        return render_template('index.html', weather=weather_data, cities=database)
    elif request.method == 'POST':
        city_name = request.form.get('city_name')
        add_to_database(city_name)
        return redirect(url_for('index'))


@app.route('/delete/<city_id>', methods=['GET', 'POST'])
def delete(city_id):
    city = WeatherInCity.query.filter_by(id=city_id).first()
    db.session.delete(city)
    db.session.commit()
    return redirect('/')


# don't change the following way to run flask:
if __name__ == '__main__':
    db.create_all()  # save the table in the database
    app.run(host="0.0.0.0", port=5000)
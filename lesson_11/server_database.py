from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from common.variables import *
import datetime


# Класс - серверная база данных:
class ServerStorage:
    database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)

    Base = declarative_base()

    # Класс - отображение таблицы всех пользователей
    class AllUsers(Base):
        __tablename__ = 'users_table'
        id = Column(Integer(), primary_key=True)
        name = Column(String(50), unique=True)
        last_login = Column(DateTime())

        def __init__(self, name):
            self.name = name

    # Класс - отображение таблицы активных пользователей:
    class ActiveUsers(Base):
        __tablename__ = 'active_users_table'
        id = Column(Integer(), primary_key=True)
        user = Column(ForeignKey('users_table.id'), unique=True)
        ip_address = Column(String())
        port = Column(Integer())
        login_time = Column(DateTime())

        def __init__(self, user, ip_address, port, login_time):
            self.user = user
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    # Класс - отображение таблицы истории входов
    class LoginHistory(Base):
        __tablename__ = 'user_login_history'
        id = Column(Integer(), primary_key=True)
        name = Column(ForeignKey('users_table.id'))
        date_time = Column(DateTime())
        ip = Column(String())
        port = Column(String())

        def __init__(self, ip, date_time, name, port):
            self.ip = ip
            self.date_time = date_time
            self.name = name
            self.port = port

    # Создаём таблицы
    Base.metadata.create_all(database_engine)

    # Создаём сессию
    Session = sessionmaker(bind=database_engine)
    session = Session()

    # Если в таблице активных пользователей есть записи, то их необходимо удалить
    # Когда устанавливаем соединение, очищаем таблицу активных пользователей
    session.query(ActiveUsers).delete()
    session.commit()

    # Функция выполняющяяся при входе пользователя, записывает в базу факт входа
    def user_login(self, username, ip_address, port):
        print(username, ip_address, port)
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        rez = self.session.query(self.AllUsers).filter_by(name=username)
        print(type(rez))
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        # Если нет, то создаздаём нового пользователя
        else:
            # Создаем экземпляр класса self.AllUsers, через который передаем данные в таблицу
            user = self.AllUsers(username)
            self.session.add(user)
            # Комит здесь нужен, чтобы присвоился ID
            self.session.commit()

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаем экземпляр класса self.ActiveUsers, через который передаем данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # и сохранить в историю входов
        # Создаем экземпляр класса self.LoginHistory, через который передаем данные в таблицу
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    # Функция фиксирующая отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
        )
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
            ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращающая историю входов по пользователю или всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.login_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())

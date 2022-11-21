"""
Опорная схема базы данных:
На стороне сервера БД содержит следующие таблицы:
 - клиент:
    логин;
    информация.
- история_клиента:
    время входа;
    ip-адрес.
- список_контактов (составляется на основании выборки всех записей с id_владельца):
    id_владельца;
    id_клиента.

"""
from pprint import pprint
import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime


class ServerStorage:
    class AllUsers:
        def __init__(self, username, ip_address, port):
            self.username = username
            self.last_login = datetime.datetime.now()
            self.ip_address = ip_address
            self.port = port
            self.id = None

    class ClientHistory:
        def __init__(self, user_id, ip_address, port, login_time):
            self.id = None
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    class ClientContacts:
        def __init__(self, user_id, contact_name, contact_time):
            self.user_id = user_id
            self.contact_name = contact_name
            self.contact_time = contact_time

    def __init__(self):
        self.database_engine = create_engine('sqlite:///server_database_console.db', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()
        # Создание таблицы пользователей

        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String, unique=True),
                            Column('ip_address', String),
                            Column('port', String),
                            Column('last_login', DateTime)
                            )
        # Создание таблицы истории активности пользователей
        login_history = Table('login_history', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('user_id', ForeignKey('Users.id')),
                              Column('ip_address', String),
                              Column('port', String),
                              Column('login_time', DateTime),
                              )
        # Создание таблицы истории контактов пользователей
        users_contacts = Table('users_contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('user_id', ForeignKey('Users.id')),
                               Column('contact_name', String),
                               Column('contact_time', DateTime)
                               )
        # Создаем  таблицы
        self.metadata.create_all(self.database_engine)
        mapper(self.AllUsers, users_table)
        mapper(self.ClientHistory, login_history)
        mapper(self.ClientContacts, users_contacts)
        # Создаем сессию
        session = sessionmaker(bind=self.database_engine)
        self.session = session()

    def user_login(self, username, ip_address, port):
        res = self.session.query(self.AllUsers).filter_by(username=username)
        if res.count():
            user = res.first()
            user.last_login = datetime.datetime.now()
        else:
            user = self.AllUsers(username, ip_address,  port)
            self.session.add(user)
            self.session.commit()
        date_time = datetime.datetime.now()
        history = self.ClientHistory(user.id, ip_address, port, date_time)
        self.session.add(history)
        self.session.commit()

    def contact(self, username, contact_name, contact_time):
        res = self.session.query(self.AllUsers).filter_by(username=username)
        user = res.first()

        contacts = self.ClientContacts(user.id, contact_name, contact_time)
        self.session.add(contacts)
        self.session.commit()

    def user_list(self):
        query = self.session.query(
            self.AllUsers.username,
            self.AllUsers.ip_address,
            self.AllUsers.port,
            self.AllUsers.last_login
        )
        #  print(query)
        return query.all()

    def history(self, username=None):
        query = self.session.query(
            self.AllUsers.username,
            self.ClientHistory.login_time,
            self.ClientHistory.ip_address,
            self.ClientHistory.port
        ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.username == username)
        return query.all()

    def contacts_list(self, username):

        query = self.session.query(
            self.AllUsers.username,
            self.ClientContacts.contact_name,
            self.ClientContacts.contact_time,

        ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.username == username)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    print("Версия SQLAlchemy:", sqlalchemy.__version__)
    test_db.user_login('client_1', '127.0.0.1', 7777)
    test_db.user_login('client_2', '127.0.0.1', 8888)
    test_db.user_login('client_3', '127.0.0.1', 7878)
    test_db.user_login('client_4', '127.0.0.1', 7888)
    test_db.user_login('client_5', '127.0.0.1', 7888)
    print('============== test AllUsers ==============')
    pprint(test_db.user_list())
    #
    test_db.contact('client_2', 'client_1', datetime.datetime.now())
    test_db.contact('client_2', 'client_3', datetime.datetime.now())
    test_db.contact('client_3', 'client_1', datetime.datetime.now())
    test_db.contact('client_3', 'client_2', datetime.datetime.now())

    print('============== test ClientsContacts ==============')
    test_db.contacts_list('client_2')
    test_db.contacts_list(None)
    pprint(test_db.contacts_list('client_2'))

    print('============== test ClientsHistory ==============')
    pprint(test_db.history())
    pprint(test_db.history('client_3'))

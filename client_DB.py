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
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import mapper, sessionmaker
import datetime
from server import database


class ClientStorage:
    name = 'Test client'
    server_database = database

    class AllUsersClient:
        def __init__(self, username, ip_address, port, sender_count, recepient_count):
            self.id = None
            self.username = username
            self.ip_address = ip_address
            self.port = port
            self.sender_count = sender_count
            self.recepient_count = recepient_count

    class MessageHistory:
        def __init__(self, user_id, message_to, message_from, message_time):
            self.id = None
            self.user_id = user_id
            self.message_to = message_to
            self.message_from = message_from
            self.message_time = message_time

    class UsersContactsList:
        def __init__(self, username, contact_name):
            self.username = username
            self.contact_name = contact_name

    def __init__(self):
        self.database_engine = create_engine(f'sqlite:///client_{self.name}.db', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()
        users_table = Table('UsersClient', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String, unique=True),
                            Column('ip_address', String),
                            Column('port', String),
                            Column('sender_count', Integer),
                            Column('recepient_count', Integer)
                            )
        message_history = Table('message_history', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('username', String),
                                Column('message_to', String),
                                Column('message_from', String),
                                Column('message_time', DateTime),
                                )
        users_contacts = Table('users_contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('username', String),
                               Column('contact_name', String),
                               )
        # Создаем таблицы
        self.metadata.create_all(self.database_engine)
        mapper(self.AllUsersClient, users_table)
        mapper(self.MessageHistory, message_history)
        mapper(self.UsersContactsList, users_contacts)
        # Создаем сессию
        session = sessionmaker(bind=self.database_engine)
        self.session = session()

    def user_list_client(self, username=None):
        query = self.session.query(
            self.AllUsersClient.id,
            self.AllUsersClient.username,
            self.AllUsersClient.ip_address,
            self.AllUsersClient.port,


        )
        if username:
            query = query.filter(self.AllUsers.username == username)
        return query.all()

    def load_users_from_client(self):
        users = self.user_list_client()
        # res = self.session.query(self.AllUsers).filter_by(username=username)
        # if res.count():
        for item in users:
            print(item.username)
            sender_count = 0
            recepient_count = 0
            user = self.AllUsersClient(item.username, item.ip_address, item.port, sender_count, recepient_count)
            self.session.add(user)
            self.session.commit()
        self.session.commit()


    def load_users_from_server(self):
        users = sorted(self.server_database.user_list())
        for item in users:
            sender_count = 0
            recepient_count = 0

            user = self.AllUsersClient(item.username, item.ip_address, item.port, sender_count,
                                       recepient_count)
            self.session.add(user)
            self.session.commit()
        self.session.commit()
        pprint(users)


# Загрузка контактов из базы данных сервера. Если клиент снова подключился и имеет список конта
def add_contact(self, username, add_contact_name):
    contacts = self.UsersContactsList(username, add_contact_name)
    self.session.add(contacts)
    self.session.commit()


if __name__ == '__main__':
    test_db = ClientStorage()
    test_db.load_users_from_client()
    if not test_db.load_users_from_client():
        test_db.load_users_from_server()
    # print("Версия SQLAlchemy:", sqlalchemy.__version__)
    # test_db.user_login('client_1', '127.0.0.1', 7777)
    # test_db.user_login('client_2', '127.0.0.1', 8888)
    # test_db.user_login('client_3', '127.0.0.1', 7878)
    # test_db.user_login('client_4', '127.0.0.1', 7888)
    # test_db.user_login('client_5', '127.0.0.1', 7888)
    # print('============== test AllUsers ==============')
    # pprint(test_db.user_list())
    #
    # test_db.add_contact('client_2', 'client_1')
    # test_db.add_contact('client_2', 'client_3')
    # test_db.add_contact('client_3', 'client_1')
    # test_db.add_contact('client_3', 'client_2')

    # print('============== test ClientsContacts ==============')
    # test_db.contacts_list('client_2')
    # test_db.contacts_list(None)
    # pprint(test_db.contacts_list('client_2'))
    #
    # print('============== test ClientsHistory ==============')
    # pprint(test_db.history())
    # pprint(test_db.history('client_3'))

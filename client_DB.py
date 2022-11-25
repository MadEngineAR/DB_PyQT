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
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import mapper, sessionmaker
import datetime
from server import database

global client_name


class ClientStorage:
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
        def __init__(self, from_user, to_user, message, date):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = date

    class UsersContactsList:
        def __init__(self, username, contact_name):
            self.username = username
            self.contact_name = contact_name

    def __init__(self, name):
        self.database_engine = create_engine(f'sqlite:///client_{name}.db', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        global client_name
        client_name = name
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
                                Column('from_user', String),
                                Column('to_user', String),
                                Column('message', Text),
                                Column('date', DateTime)
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

    def user_list_client(self, username):
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
        return users

    """
    Метод необходим в случае если база данных клиента слетела, либо ее не было, как в моем случае
    и если клиент уже зарегистрирован, программа клиент ничего не знает о доступных пользователях.
    """

    def load_users_from_server(self):
        users = sorted(self.server_database.user_list())
        for item in users:
            sender_count = 0
            recepient_count = 0

            user = self.AllUsersClient(item.username, item.ip_address, item.port, item.sender_count,
                                       item.recepient_count)
            self.session.add(user)
            self.session.commit()
        self.session.commit()
        pprint(users)

    def get_contact(self):
        query = self.session.query(
            self.UsersContactsList.username,
            self.UsersContactsList.contact_name,

        )

        return query.all()

    """
        Метод необходим в случае если база данных клиента слетела, либо ее не было, как в моем случае,
        а клиент уже зарегистрирован, программа клиент ничего не знает о контактах.
    """

    def load_contact_from_server(self):
        res = self.server_database.contacts_list(client_name)
        user_contacts = []
        for item in res:
            if item.contact_name not in user_contacts:
                contact = self.UsersContactsList(item.username, item.contact_name)
                user_contacts.append(item.contact_name)
                self.session.add(contact)
                self.session.commit()
        return res

    def add_contact(self, username, contact_name):
        res = self.session.query(self.UsersContactsList).filter_by(contact_name=contact_name)
        # print(res)
        if not res.count():
            contacts = self.UsersContactsList(username, contact_name)
            self.session.add(contacts)
            self.session.commit()

    def del_contact(self, username, del_contact_name):
        self.session.query(self.UsersContactsList).filter_by(contact_name=del_contact_name).delete()
        self.session.commit()

    """
    Метод необходим в случае если база данных клиента слетела, либо ее не было, как в моем случае,
    а клиент уже зарегистрирован, программа клиент ничего не знает о cвоих сообщениях.
    """

    def load_history_server_DB(self):
        res = self.server_database.contacts_list(client_name)
        for item in res:
            print(item.username)
            print(item.contact_name)
            print(item.message)
            print(item.contact_time)
            contact = self.MessageHistory(item.username, item.contact_name, item.message, item.contact_time)
            self.session.add(contact)
            self.session.commit()
        return res

    def save_message(self, from_user, to_user, message):
        date = datetime.datetime.now()
        message_row = self.MessageHistory(from_user, to_user, message, date)
        self.session.add(message_row)
        self.session.commit()

    def get_history(self, from_user=None, to_user=None):
        query = self.session.query(self.MessageHistory).filter_by(from_user=from_user)
        query_to = self.session.query(self.MessageHistory).filter_by(to_user=to_user)
        print(query.count())
        print(query_to.count())
        history = []
        if query.count():
            if from_user:
                history = [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                           for history_row in query.all()]
            if to_user:
                history_to = [
                    (history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                    for history_row in query_to.all()]
                history.extend(history_to)
            return history
        else:
            self.load_history_server_DB()


if __name__ == '__main__':

    test_db = ClientStorage('Test')
    # test_db.load_users_from_client()
    # test_list = test_db.load_users_from_client()
    #
    # if not test_db.load_users_from_client():
    #     test_db.load_users_from_server()
    #     test_db.load_contact_from_server()
    #
    # print(test_db.get_contact('Russia'))
    # test_db.add_contact('Russia', 'client_3')
    # print(test_db.get_contact('Russia'))
    # test_db.del_contact('Russia', 'client_3')
    # print(test_db.get_contact('Russia'))

    # test_db.save_message('Russia', 'client_2',
    #                      f'Тестовое сообщение от Russia!')
    # test_db.save_message('client_2', 'Russia',
    #                      f'Другое сообщение от Russia')
    # pprint(test_db.get_history())
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

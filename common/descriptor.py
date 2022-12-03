"""Новый протокол дескрипторов"""


class NonNegative:

    def __get__(self, instance, owner):
        return instance.__dict__[self.my_attr]

    def __set__(self, instance, value):
        if type(value) is not int:
            raise ValueError("Значение порта может быть только целым числом")
        if value < 0:
            raise ValueError("Не может быть отрицательным")
        instance.__dict__[self.my_attr] = value

    def __set_name__(self, owner, my_attr):
        # owner - владелец атрибута - <class '__main__.Worker'>
        # my_attr - имя атрибута владельца -listen_port
        self.my_attr = my_attr

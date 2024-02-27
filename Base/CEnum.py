class _CEnumMeta(type):
    def __iter__(self):
        '''
        Make child classes itself iterable not only child instances since that is what enum.Enum does
        '''
        return iter([self.__dict__[variable] for variable in self.__dict__ if not variable.startswith('__')])

    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        x.__iter__ = _CEnumMeta.__iter__
        x.__member__ = [x.__dict__[variable] for variable in x.__dict__ if not variable.startswith('__')]
        return x


class CEnum(metaclass = _CEnumMeta):
    '''
    We need a meta class since otherwise child classes cannot be handled like instances but that is what we want to become as similar as possible to enum.Enum

    A child of CEnum behaves like Enum but more like enums in C what means there is no need for value but there is also no unified Enum type

    Example:
        class Bar(CEnum):
            A = 1
            B = 2
            C = "hello"
            D = 42

        for x in Bar:
            print(x)
        > 1
        > 2
        > hello
        > 42

        print(Bar.A)
        print(Bar.B)
        print(Bar.C)
        print(Bar.D)
        print(type(Bar.D))
        > 1
        > 2
        > hello
        > 42
        > <class 'int'>

        print([member for member in Bar])
        > [1, 2, 'hello', 42]

        print(Bar.__member__)
        > [1, 2, 'hello', 42]
    '''
    pass


names = ['Иван', 'Мария', 'Петр', 'Илья']
names_1 = []
names_summ = []
first_letter_list = []


def keys_teshaurus(names):
    names.sort()
    for i in names:
        first_letter = (names[names.index(i)])[0]
        if names.index(i) == len(names) - 1:
            first_letter_list.append(first_letter)
            names_1.append(names[names.index(i)])
            if (names[names.index(i)])[0] == (names[names.index(i) - 1])[0]:
                first_letter_list.pop()
                names_1.pop()
            break
        else:
            if (names[names.index(i)])[0] == (names[names.index(i) + 1])[0]:
                first_letter_repeat = names[names.index(i)][0]
                first_letter_list.append(first_letter_repeat)
                names_summ = list(filter(lambda el: el.startswith(first_letter_repeat), names))
                names_1.append(names_summ)
            elif (names[names.index(i)])[0] == (names[names.index(i) - 1])[0]:
                True
            else:
                first_letter_list.append(first_letter)
                names_1.append(names[names.index(i)])
    teshaurus = dict(zip(first_letter_list, names_1))
    print(teshaurus)
    return teshaurus


keys_teshaurus(names)

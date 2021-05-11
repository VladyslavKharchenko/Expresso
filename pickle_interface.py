import pickle
from collections import defaultdict
import os.path


class PickleInterface:
    def __init__(self, file):
        self.file = file

        if not os.path.exists(file):
            self._create_default()

        contents = self._load()
        if contents['bot_data'] == {}:
            contents['bot_data'] = defaultdict(dict)
            contents['bot_data']['admins'] = {}
        self._dump(contents)

    def _create_default(self):
        default_contents = {
            'bot_data': defaultdict(dict, {}),
            'chat_data': defaultdict(dict, {}),
            'conversations': {},
            'user_data': defaultdict(dict, {})
        }
        self._dump(default_contents)

    def _load(self):
        with (open(self.file, 'rb')) as openfile:
            while True:
                try:
                    return pickle.load(openfile)
                except EOFError:
                    break

    def _dump(self, obj):
        with (open(self.file, 'wb')) as openfile:
            while True:
                try:
                    return pickle.dump(obj, openfile)
                except EOFError:
                    break

    # def pickle_handler(self, function):
    #     def wrapper(*args, **kwargs):
    #         contents = self._load()
    #         function(*args, **kwargs)
    #         self._dump(contents)
    #         return contents
    #     return wrapper

    def get_contents(self):
        contents = self._load()
        return contents

    def add_admin(self, user_id, user_name, sudo=False):
        contents = self._load()
        bot_data = contents['bot_data']
        admins = bot_data['admins']  # was contents['bot_data']
        if user_id in admins:
            raise Exception(f'User {user_id} is already an admin!')
        else:
            admins[user_id] = {}
            admins[user_id]['name'] = user_name
            admins[user_id]['is_available'] = False
            admins[user_id]['sudo'] = sudo

        self._dump(contents)
        return contents

    def remove_admin(self, user_id):
        contents = self._load()
        del contents['bot_data']['admins'][user_id]
        self._dump(contents)
        return contents

    def make_admin_available(self, user_id):
        contents = self._load()
        bot_data = contents['bot_data']
        admins = bot_data['admins']
        if user_id in admins:
            admins[user_id]['is_available'] = True
        else:
            raise Exception(f'User {user_id} is not an admin!')
        # use contents and user_id here
        self._dump(contents)
        return contents

    def make_admin_busy(self, user_id):
        contents = self._load()
        bot_data = contents['bot_data']
        admins = bot_data['admins']
        if user_id in admins:
            admins[user_id]['is_available'] = False
        else:
            raise Exception(f'User {user_id} is not an admin!')
        # use contents and user_id here
        self._dump(contents)
        return contents

    def get_admin_name_by_id(self, user_id):
        contents = self._load()
        name = contents['bot_data']['admins'][user_id]['name']
        self._dump(contents)
        return name


if __name__ == '__main__':
    pickle_interface = PickleInterface(file='data/persistent')
    # contents = pickle_interface.add_admin(231297270, 'Vladyslav', sudo=True)
    # contents = pickle_interface.make_admin_available(231297270)
    # contents = pickle_interface.get_admin_name_by_id(231297270)
    contents = pickle_interface.get_contents()
    print(contents)


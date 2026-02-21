import os

from auth import UserManager as AuthUserManager

class UserStore:
    USER_FILE = "users_data.json"

    @classmethod
    def load_users(cls):
        users = AuthUserManager.get_all_users()
        return [{"username": username, "role": role} for username, role in users]

    @classmethod
    def save_users(cls, users):
        return users

    @classmethod
    def add_user(cls, username, password, role):
        return AuthUserManager.create_user(username, password, role)

    @classmethod
    def _get_user_role(cls, username):
        users = cls.load_users()
        for user in users:
            if user.get("username") == username:
                return user.get("role")
        return None

    @classmethod
    def _count_admins(cls):
        users = cls.load_users()
        return sum(1 for user in users if user.get("role") == "admin")

    @classmethod
    def delete_user(cls, username):
        role = cls._get_user_role(username)
        if role is None:
            return False
        if role == "admin":
            current_username = os.environ.get("EYESHIELD_CURRENT_USER")
            if current_username and current_username != username:
                return False
            if cls._count_admins() <= 1:
                return False
        return AuthUserManager.delete_user(username)

    @classmethod
    def get_all_users(cls):
        return cls.load_users()

# For backward compatibility with existing code
load_users = UserStore.load_users
save_users = UserStore.save_users
add_user = UserStore.add_user
delete_user = UserStore.delete_user
get_all_users = UserStore.get_all_users


import json
import os

class UserStore:
    USER_FILE = "users_data.json"
    DEFAULT_ADMIN = {"username": "admin", "password": "admin", "role": "admin"}

    @classmethod
    def load_users(cls):
        if not os.path.exists(cls.USER_FILE):
            cls.save_users([cls.DEFAULT_ADMIN])
            return [cls.DEFAULT_ADMIN]
        with open(cls.USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        if not users:
            cls.save_users([cls.DEFAULT_ADMIN])
            return [cls.DEFAULT_ADMIN]
        return users

    @classmethod
    def save_users(cls, users):
        with open(cls.USER_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)

    @classmethod
    def add_user(cls, username, password, role):
        users = cls.load_users()
        if any(u["username"] == username for u in users):
            return False
        users.append({"username": username, "password": password, "role": role})
        cls.save_users(users)
        return True

    @classmethod
    def delete_user(cls, username):
        users = cls.load_users()
        user_to_delete = next((u for u in users if u["username"] == username), None)
        if not user_to_delete:
            return False
        # Block admin-to-admin deletion always (unless self)
        if user_to_delete["role"] == "admin":
            # Try to get current user from environment variable (set by app), fallback to block all except self
            import os
            current_username = os.environ.get("EYESHIELD_CURRENT_USER")
            if current_username is None or username != current_username:
                return False
        new_users = [u for u in users if u["username"] != username]
        if len(new_users) == len(users):
            return False
        cls.save_users(new_users)
        return True

    @classmethod
    def get_all_users(cls):
        return cls.load_users()

# For backward compatibility with existing code
load_users = UserStore.load_users
save_users = UserStore.save_users
add_user = UserStore.add_user
delete_user = UserStore.delete_user
get_all_users = UserStore.get_all_users


import user_store

class UserAuth:
    @staticmethod
    def verify_user(username: str, password: str) -> str | None:
        users = user_store.get_all_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                return user["role"]
        return None

# For backward compatibility
verify_user = UserAuth.verify_user

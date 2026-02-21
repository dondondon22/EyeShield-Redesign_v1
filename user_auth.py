from auth import UserManager

class UserAuth:
    @staticmethod
    def verify_user(username: str, password: str) -> str | None:
        return UserManager.verify_user(username, password)

# For backward compatibility
verify_user = UserAuth.verify_user

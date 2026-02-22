"""Authentication service for user management."""

import secrets
import string
from datetime import datetime
from typing import Optional, Tuple

from portfolio_app.models.user import User
from portfolio_app.repositories.user_repository import UserRepository


class AuthService:
    """Service handling registration, login, and password management."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def register(self, username: str, password: str) -> Tuple[User, bool]:
        """Register a new user.

        The first user to register is automatically granted admin status.

        Args:
            username: Desired username
            password: Plain-text password (will be hashed)

        Returns:
            Tuple of (created User, is_first_user)

        Raises:
            ValueError: If username is already taken
        """
        if self.user_repo.get_by_username(username):
            raise ValueError('This username is already taken.')

        is_first = self.user_repo.count() == 0
        user = User(
            username=username,
            is_admin=is_first,
        )
        user.set_password(password)
        self.user_repo.add(user)
        self.user_repo.commit()
        return user, is_first

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Verify credentials and update last_login on success.

        Args:
            username: Username to authenticate
            password: Plain-text password to verify

        Returns:
            The authenticated User, or None if credentials are invalid
        """
        user = self.user_repo.get_by_username(username)
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            self.user_repo.commit()
            return user
        return None

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Change user password after verifying the current one.

        Args:
            user: The user changing their password
            current_password: Must match the stored hash
            new_password: New plain-text password

        Raises:
            ValueError: If current_password is wrong
        """
        if not user.check_password(current_password):
            raise ValueError('Current password is incorrect.')
        user.set_password(new_password)
        self.user_repo.commit()

    def reset_password(self, user_id: int) -> str:
        """Admin action: generate and set a random temporary password.

        Args:
            user_id: ID of the user whose password will be reset

        Returns:
            The generated temporary password (show once to admin)

        Raises:
            ValueError: If user not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('User not found.')

        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        user.set_password(temp_password)
        self.user_repo.commit()
        return temp_password

    def toggle_admin(self, user_id: int, current_user: User) -> User:
        """Toggle admin status for a user (admin only).

        Args:
            user_id: Target user ID
            current_user: The admin performing the action

        Raises:
            ValueError: If user not found or trying to change own status
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('User not found.')
        if user.id == current_user.id:
            raise ValueError('You cannot change your own admin status.')
        user.is_admin = not user.is_admin
        self.user_repo.commit()
        return user

    def delete_user(self, user_id: int, current_user: User) -> None:
        """Delete a user account (admin only).

        Args:
            user_id: Target user ID
            current_user: The admin performing the deletion

        Raises:
            ValueError: If user not found or trying to delete own account
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('User not found.')
        if user.id == current_user.id:
            raise ValueError('You cannot delete your own account.')
        self.user_repo.delete(user)
        self.user_repo.commit()

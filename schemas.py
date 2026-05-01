from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


# SQLModel model classes
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    username: str = Field(index=True, unique=True)
    password: str


class Post(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("duration >= 1 AND duration <= 10",
                        name="duration_range"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    text: str
    duration: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    def expires_at(self) -> datetime:
        return self.created_at + timedelta(hours=self.duration)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at()


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

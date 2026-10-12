from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[int] = mapped_column(Integer)


class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[int] = mapped_column(Integer)


class Horse(Base):
    __tablename__ = 'horses'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(200), unique=True)
    sex: Mapped[str] = mapped_column(String(20))
    responsible: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
    __mapper_args__ = {'version_id_col': version}


class Training(Base):
    __tablename__ = 'training_sessions'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    horse_id: Mapped[str] = mapped_column(ForeignKey('horses.id'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    type: Mapped[str] = mapped_column(String(80))
    responsible: Mapped[str] = mapped_column(String(200))
    distance: Mapped[int] = mapped_column(Integer)
    segment_length: Mapped[int] = mapped_column(Integer)
    timing_mode: Mapped[str] = mapped_column(String(20), default='split', server_default='split')
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text)
    track_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    intensity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
    splits: Mapped[list['Split']] = relationship(cascade='all, delete-orphan', order_by='Split.number')
    __mapper_args__ = {'version_id_col': version}


class Split(Base):
    __tablename__ = 'training_splits'
    __table_args__ = (UniqueConstraint('training_id', 'number'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[str] = mapped_column(ForeignKey('training_sessions.id'), index=True)
    number: Mapped[int] = mapped_column(Integer)
    distance: Mapped[int] = mapped_column(Integer)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Audit(Base):
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Operation(Base):
    __tablename__ = 'operations'
    __table_args__ = (UniqueConstraint('user_id', 'key'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    key: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)


class WriteGuard(Base):
    __tablename__ = 'write_guards'
    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)

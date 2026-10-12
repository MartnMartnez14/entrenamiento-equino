import fcntl
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent


def sqlite_path(url):
    parsed = make_url(url)
    if parsed.get_backend_name() != 'sqlite' or not parsed.database or parsed.database == ':memory:':
        raise ValueError('Estos comandos requieren SQLite en archivo. Para otro motor utiliza sus herramientas de respaldo.')
    return Path(parsed.database).resolve()


@contextmanager
def server_lock(database, exclusive=True):
    database.parent.mkdir(parents=True, exist_ok=True)
    lock = open(str(database) + '.lock', 'a')
    try:
        fcntl.flock(lock, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError('El servidor está activo. Deténlo antes de restaurar o ejecutar otro servidor.')
    try:
        yield
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def verify(path):
    with sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('La copia no supera la verificación de integridad.')
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {'users', 'horses', 'training_sessions', 'training_splits', 'audit_log', 'login_sessions', 'login_attempts', 'operations', 'write_guards', 'alembic_version'}
        if not required <= tables:
            raise ValueError('No es una base Entrenamiento Equino migrada.')
        counts = {name: connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in sorted(required - {'alembic_version'})}
    return counts


def safe_destination(path):
    path = Path(path).resolve()
    # Backups must remain outside the only public directories and demo files.
    if any(path.is_relative_to(ROOT / d) for d in ['js', 'vendor', 'docs']) or path.parent == ROOT:
        raise ValueError('Guarda las copias en instance/backups o fuera del proyecto.')
    if path.exists():
        raise ValueError('El destino ya existe. No se sobrescribirá.')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def backup(source, destination):
    source, destination = Path(source).resolve(), safe_destination(destination)
    verify(source)
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    counts = verify(destination)
    metadata = {'verifiedAt': datetime.now(timezone.utc).isoformat(), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'bytes': destination.stat().st_size, 'counts': counts}
    meta_path = Path(str(destination) + '.json')
    fd = os.open(meta_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(metadata, f, indent=2)
    return metadata


def restore(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target:
        raise ValueError('Origen y destino deben ser diferentes.')
    verify(source)
    with server_lock(target):
        if target.exists():
            prior = target.parent / 'backups' / ('before-restore-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.sqlite')
            backup(target, prior)
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
            src.backup(dst)
            # A restoration never resurrects valid login cookies.
            dst.execute('DELETE FROM login_sessions')
            dst.commit()
        os.chmod(target, 0o600)
        return verify(target)

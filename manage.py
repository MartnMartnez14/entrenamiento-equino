import argparse
import getpass
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash
from alembic.config import Config
from alembic import command
from backend.app import create_app
from backend.models import User, Horse, Training, Split, Audit
from backend.domain import segments, validate_backup
from backend.backup import sqlite_path, backup, restore, server_lock


def main():
    parser = argparse.ArgumentParser(description='Administración local de Entrenamiento Equino')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('migrate')
    sub.add_parser('create-admin')
    sub.add_parser('seed-demo')
    b = sub.add_parser('backup'); b.add_argument('destination')
    r = sub.add_parser('restore'); r.add_argument('source'); r.add_argument('--confirm', action='store_true')
    s = sub.add_parser('serve'); s.add_argument('--port', type=int, default=8001)
    args = parser.parse_args()
    app = create_app()
    engine = app.extensions['engine']
    if args.command == 'migrate':
        config = Config('alembic.ini'); config.set_main_option('sqlalchemy.url', app.config['DATABASE_URL'].replace('%', '%%'))
        command.upgrade(config, 'head')
    elif args.command == 'serve':
        with server_lock(sqlite_path(app.config['DATABASE_URL']), exclusive=False):
            app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
    elif args.command == 'backup':
        print(backup(sqlite_path(app.config['DATABASE_URL']), args.destination))
    elif args.command == 'restore':
        if not args.confirm:
            raise ValueError('Restauración requiere --confirm, servidor detenido y una copia revisada.')
        engine.dispose()
        print(restore(args.source, sqlite_path(app.config['DATABASE_URL'])))
    elif args.command == 'create-admin':
        username = input('Usuario del administrador: ').strip().casefold()
        password = getpass.getpass('Contraseña (12–128 caracteres): ')
        if not username or len(username) > 120 or not 12 <= len(password) <= 128 or password != getpass.getpass('Repite la contraseña: '):
            raise ValueError('Usuario o contraseña inválidos, o las contraseñas no coinciden.')
        with Session(engine) as db:
            if db.scalar(select(User.id).where(User.username == username)):
                raise ValueError('El usuario ya existe.')
            user = User(id=str(uuid4()), username=username, password_hash=generate_password_hash(password), role='admin', active=True, must_change=False)
            db.add(user); db.flush()
            db.add(Audit(user_id=user.id, action='bootstrap-admin', entity_id=user.id, before=None, after={'username': username, 'role': 'admin'}))
            db.commit()
        print('Administrador creado. No se guardó la contraseña en archivos.')
    elif args.command == 'seed-demo':
        with Session(engine) as db:
            if db.scalar(select(Horse.id).limit(1)) or db.scalar(select(Training.id).limit(1)):
                raise ValueError('La base deportiva debe estar vacía.')
            admin = db.scalar(select(User).where(User.role == 'admin', User.active.is_(True)))
            if not admin:
                raise ValueError('Crea primero el administrador.')
            data = json.loads((Path(__file__).parent / 'data/demo-v1.json').read_text())
            # Shift the fixture as a whole to the current Montevideo date.
            anchor = datetime.now(ZoneInfo('America/Montevideo')).date()
            latest = max(datetime.fromisoformat(row['date']).date() for row in data['sessions'])
            offset = anchor - latest
            for row in data['sessions']:
                row['date'] = (datetime.fromisoformat(row['date']).date() + offset).isoformat()
            validate_backup(data)
            for row in data['horses']:
                db.add(Horse(id=row['id'], name=row['name'], name_key=row['name'].casefold(), sex=row['sex'], responsible=row['responsible'], status=row['status'], notes=row['notes']))
            db.flush()
            for row in data['sessions']:
                training = Training(id=row['id'], horse_id=row['horseId'], author_id=admin.id, date=row['date'], type=row['type'], responsible=row['responsible'], distance=row['distance'], segment_length=row['segmentLength'], total=row['total'], status=row['status'], notes=row['notes'], track_condition=row['trackCondition'], intensity=row['intensity'])
                lengths = segments(row['distance'], row['segmentLength']) if row['distance'] else []
                training.splits = [Split(number=n, distance=m, time_ms=row['splits'][n]) for n,m in enumerate(lengths)]
                db.add(training)
            db.add(Audit(user_id=admin.id, action='seed-demo', entity_id='dataset', before=None, after={'fictitious': True}))
            db.commit()
        print('Demostración cargada explícitamente.')


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        raise SystemExit(str(e))

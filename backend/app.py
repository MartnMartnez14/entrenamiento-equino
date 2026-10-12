import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, session, g, send_from_directory
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from sqlalchemy import create_engine, event, select, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.security import generate_password_hash, check_password_hash

from .models import Base, User, LoginSession, LoginAttempt, Horse, Training, Split, Audit, Operation, WriteGuard, now
from .domain import validate_horse, validate_training, validate_backup, segments, identifier

ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def public_user(user):
    return dict(id=user.id, username=user.username, role=user.role, active=user.active, mustChange=user.must_change)


def horse_json(h):
    return dict(id=h.id, name=h.name, sex=h.sex, responsible=h.responsible, status=h.status, notes=h.notes, version=h.version, updatedAt=h.updated_at)


def training_json(s):
    return dict(id=s.id, horseId=s.horse_id, authorId=s.author_id, timingMode=s.timing_mode, date=s.date, type=s.type, responsible=s.responsible, distance=s.distance, segmentLength=s.segment_length, total=s.total, status=s.status, notes=s.notes, trackCondition=s.track_condition, intensity=s.intensity, splits=[p.time_ms for p in s.splits], version=s.version, createdAt=s.created_at, updatedAt=s.updated_at)


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    instance = ROOT / 'instance'
    instance.mkdir(exist_ok=True)
    production = os.getenv('ENTRENAMIENTO_EQUINO_ENV') == 'production'
    secret = os.getenv('SECRET_KEY')
    if not secret and not production:
        path = instance / 'secret.key'
        if not path.exists():
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(secrets.token_hex(32))
        secret = path.read_text().strip()
    app.config.update(SECRET_KEY=secret, DATABASE_URL=os.getenv('DATABASE_URL', 'sqlite:///' + str(instance / 'entrenamiento-equino.sqlite')), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=production, PERMANENT_SESSION_LIFETIME=28800, WTF_CSRF_TIME_LIMIT=28800, MAX_CONTENT_LENGTH=10 * 1024 * 1024, DEMONSTRATION=True, PRODUCTION=production)
    if config:
        app.config.update(config)
    if production and (not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32):
        raise RuntimeError('Producción requiere SECRET_KEY de al menos 32 caracteres.')
    engine = create_engine(app.config['DATABASE_URL'], connect_args={'timeout': 10} if app.config['DATABASE_URL'].startswith('sqlite') else {})
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    app.extensions['engine'] = engine
    CSRFProtect(app)

    @app.before_request
    def access():
        if app.config['PRODUCTION'] and not request.is_secure:
            return jsonify(error='HTTPS obligatorio.'), 400
        g.db = Session(engine)
        g.user = None
        token = session.get('token')
        if token:
            login = g.db.get(LoginSession, digest(token))
            if login and login.expires_at > int(time.time()):
                user = g.db.get(User, login.user_id)
                if user and user.active:
                    g.user = user
        if request.path.startswith('/api/') and request.path not in ['/api/auth', '/api/login']:
            if not g.user:
                return jsonify(error='Inicia sesión para continuar.'), 401
            if g.user.must_change and request.path not in ['/api/password', '/api/logout']:
                return jsonify(error='Cambia la contraseña temporal antes de continuar.', mustChange=True), 403

    @app.teardown_request
    def close(_):
        if hasattr(g, 'db'):
            g.db.close()

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store' if request.path.startswith('/api/') or request.path == '/' else 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if app.config['PRODUCTION']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(_):
        return jsonify(error='Sesión o token de seguridad vencido. Recarga antes de reintentar.'), 400

    @app.errorhandler(ValueError)
    def invalid(err):
        return jsonify(error=str(err)), 400

    @app.errorhandler(IntegrityError)
    def duplicate(_):
        g.db.rollback()
        return jsonify(error='El identificador o nombre ya existe. Actualiza los datos y revisa el registro.'), 409

    @app.errorhandler(StaleDataError)
    def stale(_):
        g.db.rollback()
        return jsonify(error='Otro usuario cambió el registro. Revisa la versión actual antes de guardar.'), 409

    @app.errorhandler(OperationalError)
    def busy(_):
        if hasattr(g, 'db'):
            g.db.rollback()
        app.logger.exception('Database operation failed')
        return jsonify(error='El servidor no pudo guardar. Conserva el formulario y reintenta.'), 503

    @app.get('/')
    def index():
        return send_from_directory(ROOT, 'index.html')

    @app.get('/demo')
    @app.get('/demo.html')
    def local_demo():
        return send_from_directory(ROOT, 'demo.html')

    @app.get('/assets/<path:name>')
    @app.get('/js/<path:name>')
    @app.get('/vendor/<path:name>')
    @app.get('/style.css', defaults={'name': 'style.css'})
    def assets(name):
        if request.path.startswith('/js/'):
            name = 'js/' + name
        elif request.path.startswith('/vendor/'):
            name = 'vendor/' + name
        # Explicit allowlist: databases, backups and source files are never served.
        allowed = {'style.css', 'vendor/chart.umd.js', 'js/app.js', 'js/demo-app.js', 'js/domain.js', 'js/storage.js', 'js/api.js', 'js/comparisons.js', 'js/shared.js', 'js/register-form.js', 'js/charts.js'}
        if name not in allowed:
            return '', 404
        return send_from_directory(ROOT, name)

    @app.get('/api/auth')
    def auth():
        return jsonify(user=public_user(g.user) if g.user else None, csrfToken=generate_csrf(), demonstration=app.config['DEMONSTRATION'])

    def new_login(user):
        session.clear()
        token = secrets.token_urlsafe(32)
        session['token'] = token
        session.permanent = True
        g.db.add(LoginSession(token_hash=digest(token), user_id=user.id, expires_at=int(time.time()) + 28800))

    @app.post('/api/login')
    def login():
        data = request.get_json() or {}
        username = str(data.get('username', '')).strip().casefold()[:120]
        password = data.get('password', '')
        if not isinstance(password, str) or len(password) > 128:
            return jsonify(error='Credenciales inválidas.'), 401
        current = int(time.time())
        keys = [digest('account:' + username), digest('ip:' + (request.remote_addr or 'unknown'))]
        attempts = []
        for key in keys:
            attempt = g.db.get(LoginAttempt, key)
            if not attempt:
                attempt = LoginAttempt(key=key, failures=0, window_start=current)
                g.db.add(attempt)
            elif current - attempt.window_start >= 900:
                attempt.failures, attempt.window_start = 0, current
            attempts.append(attempt)
        if any(a.failures >= 5 for a in attempts):
            return jsonify(error='Demasiados intentos. Reintenta en 15 minutos.'), 429
        user = g.db.scalar(select(User).where(User.username == username))
        valid = check_password_hash(user.password_hash if user else app.config['DUMMY_HASH'], password)
        if not user or not user.active or not valid:
            g.db.flush()
            for key in keys:
                g.db.execute(update(LoginAttempt).where(LoginAttempt.key == key).values(failures=LoginAttempt.failures + 1))
            g.db.commit()
            return jsonify(error='Usuario o contraseña incorrectos.'), 401
        attempts[0].failures = 0
        new_login(user)
        g.db.commit()
        return jsonify(user=public_user(user), csrfToken=generate_csrf())

    @app.post('/api/logout')
    def logout():
        g.db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(session.get('token', ''))))
        g.db.commit()
        session.clear()
        return jsonify(ok=True)

    def password_valid(value):
        if not isinstance(value, str) or not 12 <= len(value) <= 128:
            raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')
        return value

    @app.post('/api/password')
    def password():
        data = request.get_json() or {}
        current = data.get('currentPassword', '')
        if not isinstance(current, str) or len(current) > 128 or not check_password_hash(g.user.password_hash, current):
            return jsonify(error='Contraseña actual incorrecta.'), 400
        new = password_valid(data.get('password'))
        if check_password_hash(g.user.password_hash, new):
            raise ValueError('Elige una contraseña diferente.')
        g.user.password_hash = generate_password_hash(new)
        g.user.must_change = False
        g.db.execute(delete(LoginSession).where(LoginSession.user_id == g.user.id))
        g.db.add(Audit(user_id=g.user.id, action='password-change', entity_id=g.user.id, before=None, after=None))
        new_login(g.user)
        g.db.commit()
        return jsonify(user=public_user(g.user), csrfToken=generate_csrf())

    def require_admin():
        if g.user.role != 'admin':
            return jsonify(error='Esta operación requiere un administrador.'), 403

    @app.get('/api/state')
    def state():
        return jsonify(version=2, horses=[horse_json(h) for h in g.db.scalars(select(Horse).order_by(Horse.name))], sessions=[training_json(s) for s in g.db.scalars(select(Training).order_by(Training.date))])

    def audit(action, entity_id, before, after):
        g.db.add(Audit(user_id=g.user.id, action=action, entity_id=entity_id, before=before, after=after))

    def operation():
        key = identifier(request.headers.get('Idempotency-Key'))
        fingerprint = digest(request.method + request.path + json.dumps(request.get_json(), sort_keys=True, ensure_ascii=False))
        existing = g.db.scalar(select(Operation).where(Operation.user_id == g.user.id, Operation.key == key))
        if existing:
            if existing.fingerprint != fingerprint:
                raise ValueError('Esta clave de operación ya se usó con otros datos.')
            return key, fingerprint, existing.response
        return key, fingerprint, None

    def finish(key, fingerprint, response):
        g.db.add(Operation(user_id=g.user.id, key=key, fingerprint=fingerprint, response=response))
        try:
            g.db.commit()
        except IntegrityError:
            g.db.rollback()
            existing = g.db.scalar(select(Operation).where(Operation.user_id == g.user.id, Operation.key == key))
            if existing and existing.fingerprint == fingerprint:
                return jsonify(existing.response)
            raise
        return jsonify(response)

    @app.route('/api/horses', methods=['POST'])
    @app.route('/api/horses/<record_id>', methods=['PUT'])
    def save_horse(record_id=None):
        if (error := require_admin()) is not None:
            return error
        key, fingerprint, replay = operation()
        if replay is not None:
            return jsonify(replay)
        data = request.get_json() or {}
        clean = validate_horse(data)
        h = g.db.get(Horse, record_id) if record_id else None
        if record_id and not h:
            return jsonify(error='Caballo inexistente.'), 404
        if record_id and clean['id'] != record_id:
            raise ValueError('Identificador incoherente.')
        if h and data.get('version') != h.version:
            return jsonify(error='La ficha cambió. Revisa la versión actual.', current=horse_json(h)), 409
        before = horse_json(h) if h else None
        if not h:
            h = Horse(id=clean['id'])
            g.db.add(h)
        for attr in ['name', 'sex', 'responsible', 'status', 'notes']:
            setattr(h, attr, clean[attr])
        h.name_key, h.updated_at = clean['name'].casefold(), now()
        g.db.flush()
        after = horse_json(h)
        audit('horse-update' if before else 'horse-create', h.id, before, after)
        return finish(key, fingerprint, after)

    def populate(s, clean):
        for attr, key in [('horse_id', 'horseId'), ('date', 'date'), ('type', 'type'), ('responsible', 'responsible'), ('distance', 'distance'), ('segment_length', 'segmentLength'), ('total', 'total'), ('timing_mode', 'timingMode'), ('status', 'status'), ('notes', 'notes'), ('track_condition', 'trackCondition'), ('intensity', 'intensity')]:
            setattr(s, attr, clean[key])
        lengths = segments(s.distance, s.segment_length) if s.distance and s.timing_mode != 'final' else []
        # Delete old splits before inserting rows with the same split number.
        s.splits.clear()
        g.db.flush()
        s.splits = [Split(number=i, distance=length, time_ms=clean['splits'][i]) for i, length in enumerate(lengths)]
        s.updated_at = now()

    @app.route('/api/sessions', methods=['POST'])
    @app.route('/api/sessions/<record_id>', methods=['PUT'])
    def save_training(record_id=None):
        key, fingerprint, replay = operation()
        if replay is not None:
            return jsonify(replay)
        data = request.get_json() or {}
        clean = validate_training(data)
        if not g.db.get(Horse, clean['horseId']):
            raise ValueError('Caballo inexistente.')
        s = g.db.get(Training, record_id) if record_id else None
        if record_id and not s:
            return jsonify(error='Sesión inexistente.'), 404
        if record_id and clean['id'] != record_id:
            raise ValueError('Identificador incoherente.')
        if s and g.user.role != 'admin' and s.author_id != g.user.id:
            return jsonify(error='Solo puedes corregir tus propios registros.'), 403
        if s and data.get('version') != s.version:
            return jsonify(error='Otro usuario cambió la sesión. Revisa la versión actual.', current=training_json(s)), 409
        before = training_json(s) if s else None
        if not s:
            s = Training(id=clean['id'], author_id=g.user.id)
            g.db.add(s)
        populate(s, clean)
        g.db.flush()
        after = training_json(s)
        audit('training-update' if before else 'training-create', s.id, before, after)
        return finish(key, fingerprint, after)

    @app.get('/api/users')
    def users():
        if (error := require_admin()) is not None:
            return error
        return jsonify([public_user(u) for u in g.db.scalars(select(User).order_by(User.username))])

    @app.route('/api/users', methods=['POST'])
    @app.route('/api/users/<user_id>', methods=['PUT'])
    def save_user(user_id=None):
        if (error := require_admin()) is not None:
            return error
        g.db.execute(update(WriteGuard).where(WriteGuard.name == 'admin').values(version=WriteGuard.version + 1))
        data = request.get_json() or {}
        user = g.db.get(User, user_id) if user_id else None
        if user_id and not user:
            return jsonify(error='Usuario inexistente.'), 404
        before = public_user(user) if user else None
        username = data.get('username')
        role, active = data.get('role'), data.get('active', True)
        if not isinstance(username, str) or not 1 <= len(username.strip()) <= 120 or role not in ['admin', 'worker'] or type(active) is not bool:
            raise ValueError('Cuenta inválida.')
        if user and user.role == 'admin' and user.active and (role != 'admin' or not active):
            others = list(g.db.scalars(select(User).where(User.role == 'admin', User.active.is_(True), User.id != user.id)))
            if not others:
                raise ValueError('Debe quedar al menos un administrador activo.')
        if not user:
            user = User(id=str(uuid4()), password_hash=generate_password_hash(password_valid(data.get('password'))), must_change=True)
            g.db.add(user)
        user.username, user.role, user.active = username.strip().casefold(), role, active
        if not active or (before and before['role'] != role):
            g.db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        g.db.flush()
        audit('user-update' if before else 'user-create', user.id, before, public_user(user))
        g.db.commit()
        return jsonify(public_user(user))

    @app.post('/api/users/<user_id>/reset-password')
    def reset_password(user_id):
        if (error := require_admin()) is not None:
            return error
        user = g.db.get(User, user_id)
        if not user:
            return jsonify(error='Usuario inexistente.'), 404
        user.password_hash = generate_password_hash(password_valid((request.get_json() or {}).get('password')))
        user.must_change = True
        g.db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        audit('password-reset', user.id, None, None)
        g.db.commit()
        return jsonify(ok=True)

    @app.get('/api/audit')
    def audit_log():
        if (error := require_admin()) is not None:
            return error
        return jsonify([dict(id=a.id, userId=a.user_id, action=a.action, entityId=a.entity_id, before=a.before, after=a.after, createdAt=a.created_at) for a in g.db.scalars(select(Audit).order_by(Audit.id.desc()).limit(200))])

    @app.get('/api/export')
    def export():
        if (error := require_admin()) is not None:
            return error
        return state()

    @app.post('/api/import/preview')
    @app.post('/api/import')
    def import_data():
        if (error := require_admin()) is not None:
            return error
        data = validate_backup(request.get_json())
        if not request.path.endswith('preview'):
            g.db.execute(update(WriteGuard).where(WriteGuard.name == 'import').values(version=WriteGuard.version + 1))
        if g.db.scalar(select(Horse.id).limit(1)) or g.db.scalar(select(Training.id).limit(1)):
            return jsonify(error='Solo se permite importar en una base deportiva vacía.'), 409
        if request.path.endswith('preview'):
            return jsonify(horses=len(data['horses']), sessions=len(data['sessions']))
        # Unique constraints and one transaction also protect concurrent imports.
        for h in data['horses']:
            g.db.add(Horse(id=h['id'], name=h['name'], name_key=h['name'].casefold(), sex=h['sex'], responsible=h['responsible'], status=h['status'], notes=h['notes']))
        g.db.flush()
        for clean in data['sessions']:
            s = Training(id=clean['id'], author_id=g.user.id)
            g.db.add(s)
            populate(s, clean)
        g.db.flush()
        audit('import', 'dataset', None, dict(horses=len(data['horses']), sessions=len(data['sessions'])))
        g.db.commit()
        return jsonify(ok=True)

    app.config['DUMMY_HASH'] = generate_password_hash(secrets.token_urlsafe(24))
    return app

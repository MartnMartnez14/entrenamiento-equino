import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from backend.app import create_app, digest
from backend.models import User, LoginSession, Audit, Training
from backend.domain import segments, timing, parse_time, validate_backup
from backend.backup import backup, restore, server_lock, verify

PASSWORD = 'Solo-pruebas-12345'


@pytest.fixture
def app(tmp_path, monkeypatch):
    url = 'sqlite:///' + str(tmp_path / 'test.sqlite')
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('alembic.ini')
    command.upgrade(config, 'head')
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-' * 10, 'DATABASE_URL': url})
    with Session(app.extensions['engine']) as db:
        for name, role in [('admin', 'admin'), ('worker', 'worker'), ('other', 'worker')]:
            db.add(User(id=name, username=name, password_hash=generate_password_hash(PASSWORD), role=role, active=True, must_change=False))
        db.commit()
    yield app
    app.extensions['engine'].dispose()


def csrf(client):
    return client.get('/api/auth').json['csrfToken']


def post(client, path, data, method='POST', key=None):
    headers = {'X-CSRFToken': csrf(client)}
    if key:
        headers['Idempotency-Key'] = key
    return client.open(path, method=method, json=data, headers=headers)


def login(app, username='admin'):
    client = app.test_client()
    response = post(client, '/api/login', {'username': username, 'password': PASSWORD})
    assert response.status_code == 200, response.json
    return client


def horse(client, id='h'):
    data = dict(id=id, name='Ejemplo ' + id, sex='Macho', responsible='Responsable', status='active', notes='')
    response = post(client, '/api/horses', data, key=str(uuid4()))
    assert response.status_code == 200, response.json
    return response.json


def training(horse_id='h', id=None, distance=1500, **changes):
    splits = [round(m / 500 * 38000) for m in segments(distance)]
    data = dict(id=id or str(uuid4()), horseId=horse_id, date='2026-10-11', type='Galope suave', responsible='Responsable del trabajo', distance=distance, segmentLength=500, splits=splits, total=sum(splits), status='completed', notes='', trackCondition=None, intensity=None)
    data.update(changes)
    return data


def save(client, data, method='POST', key=None):
    path = '/api/sessions' + ('/' + data['id'] if method == 'PUT' else '')
    return post(client, path, data, method, key or str(uuid4()))


def test_private_routes_csrf_and_logout(app):
    c = app.test_client()
    for path in ['/api/state', '/api/users', '/api/export', '/api/audit']:
        assert c.get(path).status_code == 401
    assert c.post('/api/login', json={'username': 'admin', 'password': PASSWORD}).status_code == 400
    c = login(app)
    assert c.get('/api/state').status_code == 200
    assert c.get('/instance/entrenamiento-equino.sqlite').status_code == 404
    assert c.get('/assets/backend/app.py').status_code == 404
    assert c.get('/js/charts.js').status_code == 200
    assert c.get('/js/comparisons.js').status_code == 200
    assert post(c, '/api/logout', {}).status_code == 200
    assert c.get('/api/state').status_code == 401


def test_rate_limit_persistent(app):
    c = app.test_client()
    for _ in range(5):
        assert post(c, '/api/login', {'username': 'admin', 'password': 'wrong'}).status_code == 401
    assert post(app.test_client(), '/api/login', {'username': 'admin', 'password': PASSWORD}).status_code == 429


def test_expiry_and_disable(app):
    admin, worker = login(app), login(app, 'worker')
    with Session(app.extensions['engine']) as db:
        db.execute(update(LoginSession).where(LoginSession.user_id == 'worker').values(expires_at=int(time.time()) - 1)); db.commit()
    assert worker.get('/api/state').status_code == 401
    worker = login(app, 'worker')
    assert post(admin, '/api/users/worker', dict(username='worker', role='worker', active=False), 'PUT').status_code == 200
    assert worker.get('/api/state').status_code == 401


def test_permissions_owner_audit_and_version(app):
    a, w, other = login(app), login(app, 'worker'), login(app, 'other')
    h = horse(a)
    assert post(w, '/api/horses', dict(h, id='x'), key=str(uuid4())).status_code == 403
    assert w.get('/api/users').status_code == 403
    assert w.get('/api/export').status_code == 403
    created = save(w, training(authorId='admin')).json
    assert created['authorId'] == 'worker'
    assert save(other, dict(created, notes='No permitido'), 'PUT').status_code == 403
    corrected = save(w, dict(created, notes='Corrección'), 'PUT')
    assert corrected.status_code == 200
    assert save(a, dict(created, notes='Versión vieja'), 'PUT').status_code == 409
    current = corrected.json
    assert save(a, dict(current, notes='Corrección admin'), 'PUT').status_code == 200
    logs = a.get('/api/audit').json
    change = next(x for x in logs if x['action'] == 'training-update')
    assert change['before']['notes'] == 'Corrección'
    assert change['after']['notes'] == 'Corrección admin'
    assert change['userId'] == 'admin'
    h['status'] = 'inactive'
    assert post(a, '/api/horses/h', h, 'PUT', str(uuid4())).status_code == 200
    assert len(w.get('/api/state').json['sessions']) == 1


def test_idempotency_and_different_payload(app):
    c = login(app); horse(c)
    data, key = training(), str(uuid4())
    a, b = save(c, data, key=key), save(c, data, key=key)
    assert a.status_code == b.status_code == 200 and a.json == b.json
    assert len(c.get('/api/state').json['sessions']) == 1
    assert save(c, dict(data, notes='Cambio'), key=key).status_code == 400


@pytest.mark.parametrize('distance', [500, 1000, 1200, 1500, 2000])
def test_distances_and_centiseconds(app, distance):
    c = login(app); horse(c)
    data = training(distance=distance)
    data['splits'][0] = 38251; data['total'] = sum(data['splits'])
    r = save(c, data)
    assert r.status_code == 200, r.json
    assert r.json['splits'][0] == 38251
    with Session(app.extensions['engine']) as db:
        s = db.get(Training, data['id'])
        assert sum(p.distance for p in s.splits) == distance
        if distance == 1200:
            assert [p.distance for p in s.splits] == [500, 500, 200]


@pytest.mark.parametrize('changes', [dict(distance=-1), dict(splits=[-1, 2, 3]), dict(total=5), dict(date='2026-02-31'), dict(horseId='missing'), dict(segmentLength=0), dict(splits=[True, 2, 3]), dict(status='unknown')])
def test_invalid_training(app, changes):
    c = login(app); horse(c)
    data = training(); data.update(changes)
    assert save(c, data).status_code == 400
    assert not c.get('/api/state').json['sessions']


def test_draft_untimed_rest_cancelled(app):
    c = login(app); horse(c)
    for status in ['draft', 'untimed', 'rest', 'cancelled']:
        splits = [38000, None, None] if status == 'draft' else [None] * 3
        data = training(status=status, splits=splits, total=None)
        if status in ['rest', 'cancelled']:
            data.update(distance=0, splits=[])
        assert save(c, data).status_code == 200
    assert len(c.get('/api/state').json['sessions']) == 4


def test_domain_accumulated():
    assert timing(['38', '37', '36']) == ([38000, 37000, 36000], 111000)
    assert timing(['38', '75', '111'], 'cumulative') == ([38000, 37000, 36000], 111000)
    assert parse_time('1:15.25') == 75250
    with pytest.raises(ValueError): timing(['38', '37'], 'cumulative')
    with pytest.raises(ValueError): timing(['', '75'], 'cumulative', 'draft')
    assert timing(['38', '', ''], status='draft')[1] is None


def test_reset_password_and_forced_change(app):
    a, w = login(app), login(app, 'worker')
    temp = 'Temporal-prueba-12345'
    assert post(a, '/api/users/worker/reset-password', {'password': temp}).status_code == 200
    assert w.get('/api/state').status_code == 401
    w = app.test_client()
    assert post(w, '/api/login', {'username': 'worker', 'password': temp}).json['user']['mustChange']
    assert w.get('/api/state').status_code == 403
    assert post(w, '/api/password', {'currentPassword': temp, 'password': 'Nueva-prueba-12345'}).status_code == 200
    assert w.get('/api/state').status_code == 200


def test_create_user_and_last_admin(app):
    c = login(app)
    assert post(c, '/api/users/admin', {'username': 'admin', 'role': 'worker', 'active': True}, 'PUT').status_code == 400
    r = post(c, '/api/users', {'username': 'new', 'role': 'worker', 'active': True, 'password': PASSWORD})
    assert r.status_code == 200 and r.json['mustChange']
    assert post(c, '/api/users', {'username': 'new', 'role': 'worker', 'active': True, 'password': PASSWORD}).status_code == 409


def test_two_clients_restart_export(app):
    a, w = login(app), login(app, 'worker'); horse(a)
    r = save(w, training())
    assert r.status_code == 200
    assert a.get('/api/state').json['sessions'][0]['id'] == r.json['id']
    restarted = create_app({'TESTING': True, 'SECRET_KEY': 'test-' * 10, 'DATABASE_URL': app.config['DATABASE_URL']})
    a2 = login(restarted)
    assert a2.get('/api/state').json['sessions'][0]['id'] == r.json['id']
    validate_backup(a2.get('/api/export').json)
    restarted.extensions['engine'].dispose()


def test_import_empty_only_atomic(app):
    c = login(app)
    data = dict(version=1, horses=[dict(id='h', name='Ejemplo', sex='Macho', responsible='Original', status='active', notes='')], sessions=[training()])
    assert post(c, '/api/import/preview', data).json == {'horses': 1, 'sessions': 1}
    invalid = json.loads(json.dumps(data)); invalid['sessions'][0]['horseId'] = 'missing'
    assert post(c, '/api/import', invalid).status_code == 400
    assert not c.get('/api/state').json['horses']
    assert post(c, '/api/import', data).status_code == 200
    assert c.get('/api/state').json['sessions'][0]['authorId'] == 'admin'
    assert c.get('/api/state').json['horses'][0]['responsible'] == 'Original'
    assert post(c, '/api/import', data).status_code == 409


def test_real_backup_restore_login_and_lock(app, tmp_path):
    c = login(app); horse(c); save(c, training())
    source = Path(app.config['DATABASE_URL'].removeprefix('sqlite:///'))
    dest = tmp_path / 'backups' / 'copy.sqlite'
    metadata = backup(source, dest)
    assert metadata['counts']['training_sessions'] == 1
    assert len(metadata['sha256']) == 64
    target = tmp_path / 'restored.sqlite'
    restore(dest, target)
    assert verify(target)['training_sessions'] == 1
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT COUNT(*) FROM login_sessions').fetchone()[0] == 0
    restored = create_app({'TESTING': True, 'SECRET_KEY': 'test-' * 10, 'DATABASE_URL': 'sqlite:///' + str(target)})
    assert login(restored).get('/api/state').json['sessions'][0]['total'] == 114000
    restored.extensions['engine'].dispose()
    restore(dest, target)
    assert list((tmp_path / 'backups').glob('before-restore-*.sqlite'))
    with server_lock(target, exclusive=False):
        with pytest.raises(ValueError): restore(dest, target)


def test_concurrent_writes_no_duplicate(app):
    admin = login(app); horse(admin)
    workers = [login(app, 'worker'), login(app, 'worker')]
    data = training(); key = str(uuid4()); barrier = threading.Barrier(2)
    tokens = [csrf(c) for c in workers]
    def run(i):
        barrier.wait()
        return workers[i].post('/api/sessions', json=data, headers={'X-CSRFToken': tokens[i], 'Idempotency-Key': key}).status_code
    with ThreadPoolExecutor(2) as pool:
        statuses = list(pool.map(run, range(2)))
    assert 200 in statuses
    assert all(s in [200, 409, 503] for s in statuses)
    assert len(admin.get('/api/state').json['sessions']) == 1
    assert save(workers[0], data, key=key).status_code == 200


def test_production_https_secure_cookie_and_secret(app, monkeypatch):
    monkeypatch.setenv('ENTRENAMIENTO_EQUINO_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError): create_app()
    secure = create_app({'TESTING': True, 'SECRET_KEY': 'test-' * 10, 'DATABASE_URL': app.config['DATABASE_URL']})
    client = secure.test_client()
    assert client.get('/api/auth').status_code == 400
    response = client.get('/api/auth', base_url='https://localhost')
    assert response.status_code == 200
    cookie = response.headers.get('Set-Cookie', '')
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    secure.extensions['engine'].dispose()


def test_extended_demo_fixture():
    import json
    from pathlib import Path
    from backend.domain import validate_backup
    data = validate_backup(json.loads((Path(__file__).parents[1] / 'data/demo-v1.json').read_text()))
    assert len(data['horses']) == 3
    assert len(data['sessions']) == 243
    assert {s['status'] for s in data['sessions']} == {'completed', 'draft', 'rest', 'cancelled', 'untimed'}
    for horse in data['horses']:
        for distance in [500, 1000, 1200, 1500, 2000]:
            assert len([s for s in data['sessions'] if s['horseId'] == horse['id'] and s['distance'] == distance and s['status'] == 'completed']) >= 2


def test_final_time_api_and_backup(app, tmp_path):
    client = login(app); horse(client)
    data = training(timingMode='final', splits=[], total=111000)
    response = post(client, '/api/sessions', data, key=str(uuid4()))
    assert response.status_code == 200, response.json
    record = response.json
    assert record['timingMode'] == 'final' and record['splits'] == [] and record['total'] == 111000
    record['total'] = 112250
    updated = post(client, '/api/sessions/' + record['id'], record, method='PUT', key=str(uuid4()))
    assert updated.status_code == 200, updated.json
    exported = client.get('/api/export').json
    assert exported['version'] == 2
    assert validate_backup(exported)['sessions'][0]['total'] == 112250
    path = tmp_path / 'final-backup.sqlite'
    backup(app.config['DATABASE_URL'].removeprefix('sqlite:///'), path)
    target = tmp_path / 'restored.sqlite'
    restore(path, target)
    recovered = create_app({'TESTING': True, 'SECRET_KEY': 'test-' * 10, 'DATABASE_URL': 'sqlite:///' + str(target)})
    assert login(recovered).get('/api/state').json['sessions'][0]['total'] == 112250
    recovered.extensions['engine'].dispose()


@pytest.mark.parametrize('changes', [{'total':0}, {'total':None}, {'total':-1}, {'splits':[38000]}, {'total':True}, {'timingMode':'other'}])
def test_invalid_final_time(app, changes):
    client=login(app);horse(client)
    data=training(timingMode='final',splits=[],total=111000);data.update(changes)
    assert post(client,'/api/sessions',data,key=str(uuid4())).status_code == 400


def test_final_draft_and_import(app):
    client=login(app);h=horse(client)
    data=training(timingMode='final',status='draft',splits=[],total=None)
    assert post(client,'/api/sessions',data,key=str(uuid4())).status_code == 200
    for version in [1,2]:
        value=validate_backup(dict(version=version,horses=[h],sessions=[training()]))
        assert value['sessions'][0]['timingMode']=='split'
    data.update(status='completed',total=111000)
    assert validate_backup(dict(version=2,horses=[h],sessions=[data]))['sessions'][0]['splits']==[]


def test_migration_preserves_existing_times(tmp_path, monkeypatch):
    path=tmp_path/'legacy.sqlite';monkeypatch.setenv('DATABASE_URL','sqlite:///'+str(path));config=Config('alembic.ini')
    command.upgrade(config,'265a276adee0')
    db=sqlite3.connect(path)
    db.execute("INSERT INTO users VALUES ('u','legacy','hash','admin',1,0,'2026-10-11')")
    db.execute("INSERT INTO horses VALUES ('h','Horse','horse','Macho','R','active','',1,'2026-10-11')")
    db.execute("INSERT INTO training_sessions (id,horse_id,author_id,date,type,responsible,distance,segment_length,total,status,notes,version,created_at,updated_at) VALUES ('s','h','u','2026-10-11','Galope suave','R',1500,500,111000,'completed','',1,'2026-10-11','2026-10-11')")
    for i,value in enumerate([38000,37000,36000]):db.execute('INSERT INTO training_splits(training_id,number,distance,time_ms) VALUES (?,?,?,?)',('s',i,500,value))
    db.commit();db.close();command.upgrade(config,'head');db=sqlite3.connect(path)
    assert db.execute('SELECT timing_mode,total FROM training_sessions').fetchone()==('split',111000)
    assert [r[0] for r in db.execute('SELECT time_ms FROM training_splits ORDER BY number')]==[38000,37000,36000]
    db.close()


def test_import_v2_final_time(app):
    client=login(app)
    data=dict(version=2,horses=[dict(id='h',name='H',sex='Macho',status='active',responsible='R',notes='')],sessions=[training(timingMode='final',splits=[],total=111000)])
    assert post(client,'/api/import/preview',data).json=={'horses':1,'sessions':1}
    assert post(client,'/api/import',data).status_code==200
    actual=client.get('/api/state').json['sessions'][0]
    assert actual['timingMode']=='final' and actual['total']==111000 and actual['splits']==[]

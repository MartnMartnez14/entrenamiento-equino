import math
import re
from datetime import date
from decimal import Decimal

TYPES = ['Caminata', 'Trote', 'Galope suave', 'Galope moderado', 'Trabajo fuerte', 'Trabajo de velocidad', 'Recuperación activa', 'Otro']
STATES = ['completed', 'draft', 'untimed', 'rest', 'cancelled']


def text(data, key, maximum=200, required=False):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f'Valor inválido: {key}.')
    return value.strip()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('Identificador inválido.')
    return value


def segments(distance, length=500):
    if type(distance) is not int or type(length) is not int or distance <= 0 or length <= 0 or distance > 2147483647 or length > 2147483647:
        raise ValueError('Las distancias deben ser metros enteros positivos.')
    if math.ceil(distance / length) > 1000:
        raise ValueError('Usa hasta 1000 tramos.')
    return [min(length, distance - i * length) for i in range(math.ceil(distance / length))]


def parse_time(value):
    value = str(value).strip().replace(',', '.')
    if not re.fullmatch(r'\d+(?::\d{1,2})?(?:\.\d{1,3})?', value):
        raise ValueError('Tiempo inválido.')
    parts = value.split(':')
    if len(parts) == 2 and Decimal(parts[1]) >= 60:
        raise ValueError('Segundos inválidos.')
    result = int((Decimal(parts[-1]) + (Decimal(parts[0]) * 60 if len(parts) == 2 else 0)) * 1000)
    if not 0 < result <= 2147483647:
        raise ValueError('Tiempo fuera de rango.')
    return result


def timing(values, mode='split', status='completed'):
    result, previous, gap = [], 0, False
    for value in values:
        if not str(value).strip():
            if status != 'draft':
                raise ValueError('Completa los tiempos.')
            result.append(None)
            gap = True
            continue
        current = parse_time(value)
        if mode == 'cumulative':
            if gap or current <= previous:
                raise ValueError('Los acumulados deben ser crecientes y consecutivos.')
            result.append(current - previous)
            previous = current
        else:
            result.append(current)
    return result, None if None in result else sum(result)


def validate_horse(data):
    if not isinstance(data, dict):
        raise ValueError('Ficha inválida.')
    result = dict(id=identifier(data.get('id')), name=text(data, 'name', required=True), sex=text(data, 'sex'), responsible=text(data, 'responsible'), status=text(data, 'status'), notes=text(data, 'notes', 5000))
    if result['sex'] not in ['Macho', 'Hembra', 'No indicado'] or result['status'] not in ['active', 'rest', 'inactive']:
        raise ValueError('Estado o sexo inválido.')
    return result


def validate_training(data):
    if not isinstance(data, dict):
        raise ValueError('Sesión inválida.')
    result = {key: text(data, key, 5000 if key == 'notes' else 200, key in ['responsible', 'date']) for key in ['date', 'type', 'status', 'responsible', 'notes']}
    if date.fromisoformat(result['date']).isoformat() != result['date'] or result['type'] not in TYPES or result['status'] not in STATES:
        raise ValueError('Fecha, trabajo o estado inválido.')
    result.update(id=identifier(data.get('id')), horseId=identifier(data.get('horseId')), distance=data.get('distance'), segmentLength=data.get('segmentLength'))
    for key in ['trackCondition', 'intensity']:
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 100):
            raise ValueError('Contexto inválido.')
        result[key] = value.strip() or None if isinstance(value, str) else None
    result['timingMode'] = data.get('timingMode', 'split')
    if result['timingMode'] not in ['split', 'cumulative', 'final']:
        raise ValueError('Modalidad inválida.')
    status = result['status']
    if status not in ['completed', 'draft']:
        result['timingMode'] = 'split'
    splits = data.get('splits')
    if not isinstance(splits, list):
        raise ValueError('Parciales inválidos.')
    if status in ['rest', 'cancelled']:
        if data.get('distance') != 0 or splits or data.get('total') is not None:
            raise ValueError('Descansos y cancelaciones no tienen distancia ni tiempos.')
        if type(result['segmentLength']) is not int or result['segmentLength'] <= 0:
            raise ValueError('Longitud inválida.')
        result.update(splits=[], total=None)
        return result
    if result['timingMode'] == 'final' and status in ['completed', 'draft']:
        segments(result['distance'], result['distance'])
        if type(result['segmentLength']) is not int or result['segmentLength'] <= 0:
            raise ValueError('Longitud inválida.')
        total = data.get('total')
        if splits or (total is None and status != 'draft') or (total is not None and (type(total) is not int or not 0 < total <= 2147483647)):
            raise ValueError('Tiempo final inválido.')
        result.update(splits=[], total=total)
        return result
    lengths = segments(result['distance'], result['segmentLength'])
    if len(splits) != len(lengths) or any(v is not None and (type(v) is not int or not 0 < v <= 2147483647) for v in splits):
        raise ValueError('Parciales inválidos.')
    total = None if None in splits else sum(splits)
    if (status == 'completed' and total is None) or (status == 'untimed' and any(v is not None for v in splits)) or total != data.get('total') or (total is not None and total > 2147483647):
        raise ValueError('Total incoherente.')
    result.update(splits=splits, total=total)
    return result


def validate_backup(data):
    if not isinstance(data, dict) or data.get('version') not in [1, 2] or not isinstance(data.get('horses'), list) or not isinstance(data.get('sessions'), list):
        raise ValueError('Copia incompatible.')
    horses = [validate_horse(h) for h in data['horses']]
    sessions = [validate_training(s) for s in data['sessions']]
    ids = {h['id'] for h in horses}
    if len(ids) != len(horses) or len({h['name'].casefold() for h in horses}) != len(horses) or len({s['id'] for s in sessions}) != len(sessions) or any(s['horseId'] not in ids for s in sessions):
        raise ValueError('Duplicados o referencias inválidas.')
    return {'version': 2, 'horses': horses, 'sessions': sessions}

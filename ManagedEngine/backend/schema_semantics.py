"""SQLite schema signatures adapted from the reviewed T01 validator."""
import re

_SQL_TOKEN = re.compile(r'''\s+|--[^\r\n]*|/\*.*?\*/|'(?:''|[^'])*'|"(?:""|[^"])*"|`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9$]*|\d+(?:\.\d+)?|<=|>=|<>|!=|==|\|\||.''', re.S)


def _sql_tokens(sql):
    return [token for token in _SQL_TOKEN.findall(sql or '')
            if not token.isspace() and not token.startswith(('--', '/*'))]


def _normalized_expression(tokens):
    while len(tokens) >= 2 and tokens[0] == '(' and tokens[-1] == ')':
        depth = 0
        for index, token in enumerate(tokens):
            depth += (token == '(') - (token == ')')
            if depth == 0 and index != len(tokens) - 1:
                return _normalized_expression_tokens(tokens)
        tokens = tokens[1:-1]
    return _normalized_expression_tokens(tokens)


def _normalized_expression_tokens(tokens):
    result = []
    for token in tokens:
        if token.startswith("'"):
            result.append(token)
        elif token.startswith(('"', '`', '[')):
            result.append(token[1:-1].replace('""', '"').replace('``', '`').casefold())
        else:
            result.append(token.casefold())
    return result


def _checks(sql):
    tokens = _sql_tokens(sql)
    result = []
    for index, token in enumerate(tokens[:-1]):
        if token.casefold() != 'check' or tokens[index + 1] != '(':
            continue
        depth = 1
        end = index + 2
        while end < len(tokens) and depth:
            depth += (tokens[end] == '(') - (tokens[end] == ')')
            end += 1
        if depth:
            raise ValueError('required schema invariant malformed')
        result.append(_normalized_expression(tokens[index + 2:end - 1]))
    return sorted(result)


def _affinity(declaration):
    value = declaration.upper()
    if 'INT' in value:
        return 'INTEGER'
    if any(part in value for part in ('CHAR', 'CLOB', 'TEXT')):
        return 'TEXT'
    if not value or 'BLOB' in value:
        return 'BLOB'
    if any(part in value for part in ('REAL', 'FLOA', 'DOUB')):
        return 'REAL'
    return 'NUMERIC'


def table_semantics(db, name):
    quoted = '"' + name.replace('"', '""') + '"'
    columns = db.execute(f'PRAGMA table_xinfo({quoted})').fetchall()
    affinities = {row[1].casefold(): _affinity(row[2]) for row in columns}
    defaults = {row[1].casefold(): _normalized_expression(_sql_tokens(row[4])) for row in columns if row[4] is not None}
    primary = sorted(row[1].casefold() for row in columns if row[5])
    not_null = sorted(row[1].casefold() for row in columns if row[3])
    indexes = db.execute(f'PRAGMA index_list({quoted})').fetchall()
    # DESC column keys and WITHOUT ROWID tables have a PK index rather than a rowid alias.
    rowid_alias = (primary[0] if len(primary) == 1 and
                   any(row[5] and row[2].upper() == 'INTEGER' for row in columns) and
                   not any(index[3] == 'pk' for index in indexes) else None)
    unique = []
    for index in indexes:
        index_name = index[1]
        index_quoted = '"' + index_name.replace('"', '""') + '"'
        index_keys = [row for row in db.execute(f'PRAGMA index_xinfo({index_quoted})') if row[5]]
        if not index_keys or any(row[2] is None for row in index_keys):
            raise ValueError('unsupported additional schema expression index: ' + name)
        if not index[2]:
            if index[4]:
                raise ValueError('unsupported additional schema partial index: ' + name)
            continue
        keys = [(row[2].casefold(), (row[4] or '').casefold()) for row in index_keys]
        predicate = None
        if index[4]:
            row = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (index_name,)).fetchone()
            tokens = _sql_tokens(row[0] if row else '')
            depth = 0
            where = None
            for position, token in enumerate(tokens):
                depth += (token == '(') - (token == ')')
                if depth == 0 and token.casefold() == 'where':
                    where = position
                    break
            if where is None:
                raise ValueError('required schema invariant malformed')
            predicate = _normalized_expression(tokens[where + 1:])
        unique.append([sorted([list(key) for key in keys]), predicate])
    groups = {}
    for row in db.execute(f'PRAGMA foreign_key_list({quoted})'):
        group = groups.setdefault(row[0], {'table': row[2].casefold(), 'update': row[5].casefold(), 'delete': row[6].casefold(), 'match': row[7].casefold(), 'columns': []})
        group['columns'].append([row[3].casefold(), row[4].casefold() if row[4] is not None else None])
    foreign = []
    for group in groups.values():
        group['columns'].sort(key=lambda pair: (pair[0], pair[1] or ''))
        foreign.append(group)
    sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
    return {'primary_key': primary, 'rowid_alias': rowid_alias, 'affinities': affinities, 'hidden': {row[1].casefold(): row[6] for row in columns}, 'defaults': defaults, 'not_null': not_null, 'unique': unique, 'foreign_keys': foreign, 'checks': _checks(sql)}

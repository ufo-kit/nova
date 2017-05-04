from nova import db, models


class InvalidTokenFormat(ValueError):

    pass


def check_token(token):
    uid, signature = token.split('.')
    try:
        user = from_token(token)
    except InvalidTokenFormat as e:
        abort(400)

    if user is None:
        abort(401, "Unknown user")

    if not user.is_token_valid(token):
        abort(401)

    return user


def from_token(token):
    if not '.' in token:
        raise InvalidTokenFormat("No '.' in the token")

    parts = token.split('.')

    if len(parts) != 2:
        raise InvalidTokenFormat("Token cannot be separated")

    try:
        uid = int(parts[0])
    except ValueError as e:
        raise InvalidTokenFormat(str(e))

    return db.session.query(models.User).filter(models.User.id == uid).first()

import ed25519ll


def sign(msg, priv_key):

    return ed25519ll.crypto_sign(msg, priv_key).replace(msg, b'')


def verify_sig(msg, pub_key, sig):

    sig += msg
    try:
        verified = ed25519ll.crypto_sign_open(sig, pub_key)
    except ValueError:
        return False

    return verified == msg

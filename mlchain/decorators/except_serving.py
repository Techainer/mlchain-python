def except_serving(f):
    f._MLCHAIN_EXCEPT_SERVING = True
    return f
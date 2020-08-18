def except_serving(func):
    func._MLCHAIN_EXCEPT_SERVING = True
    return func

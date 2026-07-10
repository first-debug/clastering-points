def max_confidence(objs: list[dict]) -> dict:
    return max(objs, key=lambda o: float(o['confidence']))


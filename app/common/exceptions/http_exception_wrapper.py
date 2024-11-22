from fastapi import HTTPException


def http_exception(status_code: int, msg: str, _input) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "msg": msg,
            "input": _input
        }
    )

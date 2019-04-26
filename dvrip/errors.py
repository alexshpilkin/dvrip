__all__ = ('DVRIPError', 'DVRIPDecodeError')


class DVRIPError(Exception):
	pass


class DVRIPDecodeError(ValueError, DVRIPError):
	pass

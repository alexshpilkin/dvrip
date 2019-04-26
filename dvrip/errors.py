__all__ = ('DVRIPError', 'DVRIPDecodeError', 'DVRIPRequestError')


class DVRIPError(Exception):
	pass


class DVRIPDecodeError(ValueError, DVRIPError):
	pass


class DVRIPRequestError(OSError, DVRIPError):
	__slots__ = ('request', 'reply')

	def __init__(self, request, reply):
		super().__init__(reply.status.message)
		self.request = request
		self.reply   = reply
		assert not self.status

	@property
	def status(self):
		return self.reply.status

	@property
	def code(self):
		return self.status.code

	@classmethod
	def signal(cls, request, reply):
		if not reply.status:
			raise cls(request, reply)

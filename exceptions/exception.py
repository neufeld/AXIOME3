"""
Custom exceptions are defined here
"""
# Custom exception
class AXIOME3Error(RuntimeError):
	def __init__(self, message, response=None):
		super().__init__(message)
		if(response is not None):
			self.response = response